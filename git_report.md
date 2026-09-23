# Git report one-shot prompt

Paste the block below to an agent on your own machine. It fetches every repo
listed in your config and reports the commits you made in a time window.
With no window given, it reports the last 24 hours up to now.

Each teammate keeps their own config at `~/.local/git_report.toml`. The prompt
contains no personal paths or emails.

## Config

Create `~/.local/git_report.toml`:

```toml
# Directories scanned recursively; every git repo below each one is included.
dirs = [
  "~/repos",
]

# Single repos: a local path or a remote URL.
# Remote URLs are mirror-cloned into ~/.cache/git_report/ on first use.
repos = []

# Author emails that count as mine (case-insensitive).
emails = [
  "me@company.com",
]
```

## Rules the script enforces

- **Repos:** Every git repo under `dirs`, plus each entry in `repos`. Submodules and nested repos are included. Worktrees and duplicates are counted once.
- **Commits:** Local and remote commits on all branches. Merge commits are skipped.
- **Authors:** Only commits whose author email is in `emails`.
- **Time:** The author date must fall inside the window. A rebased or amended copy of the same commit is listed once.
- **Safety:** Read-only. The script only runs `git fetch` and, for remote URLs, `git clone --mirror` into `~/.cache/git_report/`. Fetch never prompts for a password. If a fetch fails, the report says so and uses the local data.
- **Requirements:** git 2.31+ and python 3.11+.

## Prompt

````text
Report the git work I did in a time window, using ONLY the script below.

============================================================
WINDOW
============================================================

1. If I gave no window, use the default: the last 24 hours ending now.
   Run the script with no --start or --end flags.
2. If I gave a window, convert it to local time in the form
   "YYYY-MM-DD HH:MM" (or "YYYY-MM-DD" for midnight). Work out relative
   phrases ("yesterday 11am to 4am today", "since Monday") from the
   current local date and time (run `date` to get it). Pass --start and
   --end. If I gave only a start, omit --end (it defaults to now).
3. If the window is ambiguous, ask me one question before running
   anything.

============================================================
HARD RULES
============================================================

- Run the script exactly as written. Do not edit it, and do not replace it
  with your own git commands.
- Read-only. Never pull, checkout, reset, stash, commit, push, or change git
  config in any repo.
- Report only what the script outputs. Never invent, merge, or drop
  commits, and never add authors that are not in the config.
- If the script prints a line starting with "ERROR:", stop. Show me that
  line and how to fix it. If the config is missing, tell me to create
  ~/.local/git_report.toml with this template:
    dirs = ["~/repos"]
    repos = []
    emails = ["me@company.com"]

============================================================
STEP 1 - RUN
============================================================

Run this from any directory. Replace the flags as described under WINDOW.
It can take a few minutes, because it fetches every repo first.

python3 - --start "YYYY-MM-DD HH:MM" --end "YYYY-MM-DD HH:MM" <<'PY'
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
    args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
    end = parse_time(args["--end"]) if args.get("--end") else datetime.datetime.now().astimezone()
    start = parse_time(args["--start"]) if args.get("--start") else end - datetime.timedelta(hours=24)
    if start >= end:
        sys.exit(f"ERROR: start {start} is not before end {end}")
    cfg = load_config()
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
PY

The output is JSON:
- window: the start and end that were used
- repos_scanned: the number of unique repos
- repos_with_commits: for each repo, its commits with time, hash, author,
  subject, body, stat, branches, and pushed (false = local-only)
- skipped: config entries that do not exist or failed to clone
- fetch_failed: repos whose fetch failed (their remote data may be stale)

============================================================
STEP 2 - REPORT
============================================================

Write the report as plain text in chat. Do not create a file.

1. Header line: the window (start to end, with the timezone), the total
   number of commits, and the number of repos with commits.
2. Group commits by repo (use the repo folder name), in time order.
3. One line per commit: time (HH:MM, with the date when the window spans
   several days), short hash, branch, pushed or local-only, a
   plain-language summary drawn from the subject and body (not the raw
   subject line), size (+/- lines when notable), and author email.
4. "Themes": 3 bullets that group the work by topic.
5. "Skipped" and "Fetch failed": list each entry with its reason. Leave a
   section out if it is empty.
6. If there are no commits, say so plainly and still show sections 5.
7. End with one next action.
````
