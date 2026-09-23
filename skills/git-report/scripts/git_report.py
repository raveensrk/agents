#!/usr/bin/env python3
"""Collect a person's git commits across their repos for a time window; prints JSON."""
import concurrent.futures, datetime, json, os, re, subprocess, sys

if sys.version_info < (3, 11):
    sys.exit("ERROR: python 3.11+ required (for tomllib); found " + sys.version.split()[0])
import tomllib

CONFIG = os.path.expanduser("~/.local/git_report.toml")
CACHE = os.path.expanduser("~/.cache/git_report")
PRUNE = {"node_modules", ".venv", "venv", "__pycache__"}


def parse_time(s):
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s.strip(), fmt).astimezone()
        except ValueError:
            pass
    sys.exit(f"ERROR: bad time {s!r}; use 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD'")


def git(repo, *args, timeout=60, batch_ssh=False):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="C")
    if batch_ssh:  # never let ssh prompt; keep any user-configured ssh command
        env.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes -o ConnectTimeout=15")
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                          errors="replace", env=env, timeout=timeout,
                          stdin=subprocess.DEVNULL)


def is_url(s):
    return "://" in s or re.match(r"^[\w.-]+@[\w.-]+:", s) is not None


def load_config():
    if not os.path.isfile(CONFIG):
        sys.exit(f"ERROR: config not found: {CONFIG}")
    try:
        with open(CONFIG, "rb") as f:
            cfg = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        sys.exit(f"ERROR: invalid TOML in {CONFIG}: {e}")
    for key in ("dirs", "repos", "emails"):
        val = cfg.get(key, [])
        if not isinstance(val, list) or not all(isinstance(v, str) for v in val):
            sys.exit(f"ERROR: '{key}' in {CONFIG} must be a list of strings")
        cfg[key] = [v.strip() for v in val if v.strip()]
    if not cfg["emails"]:
        sys.exit(f"ERROR: 'emails' in {CONFIG} is empty")
    if not cfg["dirs"] and not cfg["repos"]:
        sys.exit(f"ERROR: 'dirs' and 'repos' in {CONFIG} are both empty")
    hours = cfg.get("default_hours", 24)
    if isinstance(hours, bool) or not isinstance(hours, (int, float)) or hours <= 0:
        sys.exit(f"ERROR: 'default_hours' in {CONFIG} must be a number above 0")
    cfg["default_hours"] = hours
    return cfg


def discover(root):
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
        if ".git" in dirnames or ".git" in filenames:
            yield dirpath
        dirnames[:] = [d for d in dirnames if d != ".git" and d not in PRUNE]


def mirror(url):
    name = re.sub(r"[^\w.-]+", "_", re.sub(r"^\w+://", "", url)).strip("_")
    path = os.path.join(CACHE, name if name.endswith(".git") else name + ".git")
    if not os.path.isdir(path):
        os.makedirs(CACHE, exist_ok=True)
        r = subprocess.run(["git", "clone", "--mirror", "--quiet", url, path],
                           capture_output=True, text=True, timeout=600,
                           stdin=subprocess.DEVNULL,
                           env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
        if r.returncode:
            return None, r.stderr.strip()
    return path, None


def fetch(repo):
    if not git(repo, "remote").stdout.strip():
        return "no remote"
    try:
        custom_ssh = git(repo, "config", "--get", "core.sshCommand").stdout.strip()
        r = git(repo, "fetch", "--all", "--prune", "--quiet", timeout=180,
                batch_ssh=not custom_ssh)
    except subprocess.TimeoutExpired:
        return "fetch timed out after 180s"
    if not r.returncode:
        return None
    lines = [x for x in r.stderr.splitlines() if x.strip()]
    return next((x for x in lines if x.startswith(("fatal:", "error:"))), " ".join(lines))[:300]


def commits(repo, bare, start, end, emails):
    fmt = "%x1e%H%x1f%h%x1f%at%x1f%ae%x1f%an%x1f%s%x1f%b"
    r = git(repo, "log", "--all", "--no-merges", f"--since=@{int(start.timestamp())}",
            f"--format={fmt}", timeout=300)
    out = {}
    for rec in r.stdout.split("\x1e")[1:]:
        h, short, at, ae, an, subj, body = rec.split("\x1f", 6)
        at = int(at)
        if ae.strip().lower() not in emails or not start.timestamp() <= at <= end.timestamp():
            continue
        refs = git(repo, "for-each-ref", "--contains", h,
                   "--format=%(refname)", "refs/heads", "refs/remotes").stdout.split()
        pushed = bare or any(x.startswith("refs/remotes/") for x in refs)
        branches = sorted({re.sub(r"^refs/(heads|remotes)/", "", x) for x in refs
                           if not x.endswith("/HEAD")})
        stat = git(repo, "show", "--shortstat", "--format=", h).stdout.strip()
        key = (ae.lower(), at, subj)  # rebased or amended copies of the same work
        if key in out:
            out[key]["branches"] = sorted(set(out[key]["branches"]) | set(branches))
            out[key]["pushed"] |= pushed
            continue
        out[key] = {
            "time": datetime.datetime.fromtimestamp(at).astimezone().strftime("%Y-%m-%d %H:%M"),
            "hash": short, "author": f"{an} <{ae}>", "subject": subj,
            "body": body.strip()[:1500], "stat": stat, "branches": branches[:5],
            "pushed": pushed,
        }
    return sorted(out.values(), key=lambda c: c["time"])


def main():
    argv = sys.argv[1:]
    if len(argv) % 2 or any(k not in ("--start", "--end") for k in argv[::2]):
        sys.exit("ERROR: usage: git_report.py [--start 'YYYY-MM-DD HH:MM'] [--end 'YYYY-MM-DD HH:MM']")
    args = dict(zip(argv[::2], argv[1::2]))
    cfg = load_config()
    end = parse_time(args["--end"]) if args.get("--end") else datetime.datetime.now().astimezone()
    start = (parse_time(args["--start"]) if args.get("--start")
             else end - datetime.timedelta(hours=cfg["default_hours"]))
    if start >= end:
        sys.exit(f"ERROR: start {start} is not before end {end}")
    emails = {e.lower() for e in cfg["emails"]}
    skipped, failed, found = [], [], []

    for d in cfg["dirs"]:
        p = os.path.expanduser(d)
        if os.path.isdir(p):
            found += [(x, False) for x in discover(p)]
        else:
            skipped.append(f"dirs: {d} (not a directory)")
    for entry in cfg["repos"]:
        if is_url(entry):
            path, err = mirror(entry)
            if path:
                found.append((path, True))
            else:
                skipped.append(f"repos: {entry} (clone failed: {err})")
        else:
            p = os.path.expanduser(entry)
            if git(p, "rev-parse", "--git-dir").returncode if os.path.isdir(p) else True:
                skipped.append(f"repos: {entry} (not a git repo)")
            else:
                found.append((p, False))

    repos = {}
    for path, bare in found:
        r = git(path, "rev-parse", "--path-format=absolute", "--git-common-dir")
        if r.returncode:
            skipped.append(f"{path} (not readable as a git repo)")
            continue
        repos.setdefault(os.path.realpath(r.stdout.strip()), (os.path.realpath(path), bare))

    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        results = dict(zip(repos, ex.map(lambda k: fetch(repos[k][0]), repos)))
    for k, err in results.items():
        if err and err != "no remote":
            failed.append({"repo": repos[k][0], "error": err})

    report = []
    for k, (path, bare) in sorted(repos.items(), key=lambda kv: kv[1][0]):
        c = commits(path, bare, start, end, emails)
        if c:
            report.append({"repo": path, "local_only_repo": results[k] == "no remote", "commits": c})

    json.dump({
        "window": {"start": start.isoformat(timespec="minutes"), "end": end.isoformat(timespec="minutes")},
        "repos_scanned": len(repos), "repos_with_commits": report,
        "skipped": skipped, "fetch_failed": failed,
    }, sys.stdout, indent=1, ensure_ascii=False)


main()
