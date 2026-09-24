#!/usr/bin/env python3
"""Migrate line-schema todo items to the org schema (todo_schema.org).

Consolidates every repo's boards into repo-root org files:

    todo.md/TODO.md items   ->  <repo>/todo.org
    inbox.md items          ->  <repo>/todo.org      (shaped tasks, not capture)
    archive.md items        ->  <repo>/<board>.org_archive, paired with the board in its directory

Board = a .md file named todo, inbox or archive (case-insensitive) that holds
line-schema items. Any other .md file with items is documentation, a fixture
or prose and is never converted; the report names it.

    migrate_todo.py ~/repos ~/dot            dry run, writes nothing
    migrate_todo.py --apply ~/repos ~/dot    write, git rm boards, commit per repo

Safety, in order of how much it matters:

  1. --apply refuses a repo whose tree is dirty, so a revert undoes this and
     nothing else.
  2. Every converted item is reparsed with an org reader before the file is
     written. One bad line leaves that whole source board untouched.
  3. Fenced blocks and non-board files are never touched.
  4. A file reached twice through a symlink is converted once.
"""

import argparse
import datetime
import os
import re
import subprocess
import sys
import uuid

STATES = ["TODO", "IN_PROGRESS", "OPTIONAL", "LATER", "DONE", "OBSOLETE"]
TODO_LINE = "#+TODO: TODO IN_PROGRESS OPTIONAL LATER | DONE OBSOLETE"
SKIP = {".git", "node_modules", "target", "tests", "fixtures", "dist", "build", ".venv"}
FENCE = ("```", "~~~")
BOARD_NAMES = {"todo", "inbox", "archive"}

LINE = re.compile(r"^(\s*)- (" + "|".join(STATES) + r"): (?:\[T(\d+)\] )?(.*)$")
# One metadata token at the very end: +tag, @ctx, key:value.
META = re.compile(r"\s(\+\w+|@\w+|(?:" + "created|completed|due|recurring" + r"):\S+)$")
PRI = re.compile(r"\s\(([ABC])\)$")
MD_HEAD = re.compile(r"^(#{1,6}) (.*)$")
RECUR = re.compile(r"^(daily|weekly|monthly|yearly|[1-9]\d*[dwmy])$")

DATE = r"\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])"
TIME = r"([01]\d|2[0-3]):[0-5]\d"
TS = re.compile(rf"^({DATE})(?:T{TIME})?$")


class Bad(Exception):
    pass


def day_name(date_str):
    try:
        return datetime.date.fromisoformat(date_str).strftime("%a")
    except ValueError:
        raise Bad(f"impossible date {date_str}")


def repeater(value):
    """`recurring:` value to an org repeater string."""
    value = value.strip().lower().replace("_", "")
    if value.startswith("from-done"):
        tail = value[len("from-done"):].strip()
        if not RECUR.match(tail):
            raise Bad(f"bad recurring from-done {value!r}")
        return "." + tail
    if value in ("daily", "weekly", "monthly", "yearly"):
        return "+1" + value[0]
    if RECUR.match(value):
        return "+" + value
    raise Bad(f"bad recurring {value!r}")


def parse_date(token):
    if not TS.match(token):
        raise Bad(f"bad date {token!r}")
    date, rest = token[:10], token[10:]
    return date, rest  # rest = "THH:MM" or ""


def sym(tok):
    """Fold a tag to an org tag: lowercase. Raises on org-illegal characters."""
    tag = tok.lower()
    if not re.fullmatch(r"[a-z0-9_@#%]+", tag):
        raise Bad(f"tag {tok!r} not an org tag (charset or uppercase)")
    return tag


def state_like(word):
    """True if a container heading starting with `word` would be misread as a
    task state: exact state or the near-miss rules of todo_schema.org."""
    w = word.rstrip(":").lower()
    states = [s.lower() for s in STATES]
    if w in states:
        return True
    for s in states:
        if len(s) >= 6 and len(w) >= 6:
            if sum(a != b for a, b in zip(w, s)) <= 1 and abs(len(w) - len(s)) <= 1:
                return True
    return False


def heading_title(title):
    """A markdown heading may not become a task or a near-miss state."""
    words = title.split()
    if words and state_like(words[0]):
        return "Board — " + title
    return title


def convert(line):
    """One line-schema item -> list of org lines. Raises Bad."""
    m = LINE.match(line)
    if not m:
        return None
    state, tid, rest = m.group(2), m.group(3), m.group(4)

    pri = None
    hit = PRI.search(rest)
    if hit:
        pri, rest = hit.group(1), rest[: hit.start()]

    tags, kv = [], {}
    while True:
        hit = META.search(rest)
        if not hit:
            break
        tok = hit.group(1)
        rest = rest[: hit.start()]
        if tok.startswith("+") or tok.startswith("@"):
            tags.append(sym(tok[1:]))
        else:
            key, val = tok.split(":", 1)
            if key in kv:
                raise Bad(f"repeated key {key}")
            kv[key] = val

    title = rest.strip()
    if not title:
        raise Bad("empty title")

    prefix = f"[#{pri}] " if pri else ""
    head = f"{'*' * TASK_DEPTH} {state} {prefix}{title}"
    if tags:
        head += " :" + "".join(t + ":" for t in tags)

    out = [head]
    if "due" in kv:
        date, tpart = parse_date(kv["due"])
        stamp = date + " " + day_name(date)
        if tpart:
            stamp += " " + tpart[1:]
        if "recurring" in kv:
            stamp += " " + repeater(kv["recurring"])
        out.append(f"{' ' * TASK_DEPTH}DEADLINE: <{stamp}>")
    if "completed" in kv:
        date, tpart = parse_date(kv["completed"])
        if tpart:
            raise Bad("completed with a time")
        out.append(f"{' ' * TASK_DEPTH}CLOSED: [{date} {day_name(date)}]")
    props = [f":ID: {uuid.uuid4()}"]
    if "created" in kv:
        date, _ = parse_date(kv["created"])
        props.append(f":CREATED: {date}")
    out.append(f"{' ' * TASK_DEPTH}:PROPERTIES:")
    out.extend(f"{' ' * TASK_DEPTH}{p}" for p in props)
    out.append(f"{' ' * TASK_DEPTH}:END:")

    body = []
    if tid:
        body.append(f"former id: [T{tid}]")
    if body:
        out.extend(" " * TASK_DEPTH + b for b in body)
    return out


# Depth at which task headings are emitted, set per source file.
TASK_DEPTH = 2


def migrate(path, depth):
    """Convert one board file at a fixed task depth. Returns (count, org_lines, error, prose_dropped)."""
    try:
        text = open(path, encoding="utf-8").read()
    except (UnicodeDecodeError, OSError) as err:
        return 0, None, str(err), 0

    fenced = False
    # Frontmatter is only frontmatter at file start; a `---` later is prose.
    # in_front: 2 = opener pending, 1 = inside frontmatter.
    in_front = 2 if re.match(r"\A---\s*\n", text) else 0

    out, count, prose = [], 0, 0

    for line in text.splitlines(keepends=True):
        bare = line.strip()
        end = "\n" if line.endswith("\n") else ""

        if bare.startswith(FENCE):
            fenced = not fenced
            continue
        if fenced:
            continue

        if in_front:
            if in_front == 2:
                in_front = 1  # the opening --- line itself
            elif bare == "---":
                in_front = False
            else:
                prose += 1  # frontmatter lines, dropped
            continue

        h = MD_HEAD.match(line)
        if h:
            level, title = len(h.group(1)), h.group(2).strip()
            if title:
                out.append(f"{'*' * level} {heading_title(title)}" + end)
            continue

        m = LINE.match(line)
        if m:
            try:
                global TASK_DEPTH
                TASK_DEPTH = depth
                item = convert(line.rstrip("\n"))
            except Bad as err:
                return 0, None, f"{path}: {err}", prose
            out.extend(x + end for x in item)
            count += 1
            continue
        note = re.match(r"^(\s+)(.*)$", line)
        if note and note.group(2).strip():
            out.append(" " * depth + note.group(2).rstrip("\n") + end)
            continue

        if bare:
            # Prose is preserved verbatim as body under the current heading,
            # never dropped: a board may carry spec text between its items.
            out.append(" " * depth + bare + end)
            continue

    return count, out, None, prose


def scan(path):
    """The deepest markdown heading level outside fenced blocks. For task depth."""
    try:
        text = open(path, encoding="utf-8").read()
    except (UnicodeDecodeError, OSError):
        return 1
    deepest, fenced = 1, False
    for line in text.splitlines():
        bare = line.strip()
        if bare.startswith(FENCE):
            fenced = not fenced
            continue
        if fenced:
            continue
        h = MD_HEAD.match(line)
        if h:
            deepest = max(deepest, len(h.group(1)))
    return deepest


def board_name(path):
    base = os.path.splitext(os.path.basename(path))[0].lower()
    return base if base in BOARD_NAMES else None


def walk(root, seen):
    """Yield every markdown file under root, skipping SKIP dirs and repeat visits."""
    for dirpath, dirs, names in os.walk(root, followlinks=True):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(".")]
        for name in names:
            if not name.endswith(".md"):
                continue
            path = os.path.join(dirpath, name)
            real = os.path.realpath(path)
            if real in seen:
                continue
            seen.add(real)
            yield path, real


def repo_of(path):
    try:
        got = subprocess.run(
            ["git", "-C", os.path.dirname(path), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return got.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def dirty(root):
    got = subprocess.run(
        ["git", "-C", root, "status", "--porcelain"], capture_output=True, text=True
    )
    return bool(got.stdout.strip())


def org_header(title):
    return [f"#+TITLE: {title}", TODO_LINE, "#+STARTUP: logdone", ""]


def archive_header():
    return ["# -*- mode: org -*-", TODO_LINE, "Archived entries", ""]


HEADING = re.compile(r"^(\*+) (\S+)(.*)$")
STAMP = re.compile(r"[<\[](\d{4})-(\d{2})-(\d{2}) (Mon|Tue|Wed|Thu|Fri|Sat|Sun)[ \d:]*[>\]]")


def validate(text, name):
    """Reparse generated org per the reader rules of todo_schema.org. Raises Bad."""
    stack = []  # (depth, is_task) of enclosing headings
    for n, line in enumerate(text.splitlines(), 1):
        if not line.startswith("*"):
            continue
        m = HEADING.match(line)
        if not m:
            raise Bad(f"{name}:{n}: bad heading {line!r}")
        depth, state, rest = len(m.group(1)), m.group(2), m.group(3)
        is_task = state in STATES
        if is_task and not rest.strip():
            raise Bad(f"{name}:{n}: empty title")
        if not is_task and state_like(state):
            raise Bad(f"{name}:{n}: container starts with a state-like word")
        while stack and stack[-1][0] >= depth:
            stack.pop()
        if is_task:
            if any(t for _, t in stack):
                raise Bad(f"{name}:{n}: nested task")
            stack.append((depth, True))
        else:
            stack.append((depth, False))
        for y, mo, dy, day in STAMP.findall(line):
            real = datetime.date(int(y), int(mo), int(dy)).strftime("%a")
            if real != day:
                raise Bad(f"{name}:{n}: day name says {day}, date is {real}")
    return True


def collect(roots):
    """Build plan: repo -> target name -> (text, [source paths], counts). Plus skipped reports."""
    plan, skipped, loose = {}, [], []
    seen = set()

    # repo -> list of (kind, dir, count, org text, prose, real path, deepest)
    boards = {}

    for root in roots:
        for path, real in walk(os.path.expanduser(root), seen):
            kind = board_name(path)
            if not kind:
                continue
            deepest = scan(real)
            count, lines, err, prose = migrate(real, deepest + 1)
            if err:
                skipped.append(f"board {err}")
                continue
            if not count:
                continue
            home = repo_of(path)
            if not home:
                loose.append((path, count))
                continue
            boards.setdefault(home, []).append(
                (kind, os.path.dirname(real), count, "".join(lines), prose, real, deepest)
            )

    for home, items in boards.items():
        # All tasks in one repo sit at one depth, so no task can nest in a task
        # when boards merge. Headings keep their markdown depth; tasks of a
        # shallower board land under its top heading, which is a container.
        depth = max(i[6] for i in items) + 1
        reconverted = []
        for kind, dir_, count, _, prose, real, _ in items:
            count, lines, err, prose = migrate(real, depth)
            if err:
                skipped.append(f"board {err}")
            else:
                reconverted.append((kind, dir_, count, "".join(lines), prose, real))
        targets = {}
        for kind, dir_, count, org, prose, real in reconverted:
            prose_dropped[home] = prose_dropped.get(home, 0) + prose
            if kind == "todo":
                targets.setdefault("todo.org", ["", [], 0])
                targets["todo.org"][0] += org
                targets["todo.org"][1].append(real)
                targets["todo.org"][2] += count
            elif kind == "inbox":
                targets.setdefault("todo.org", ["", [], 0])
                targets["todo.org"][0] += org
                targets["todo.org"][1].append(real)
                targets["todo.org"][2] += count
            elif kind == "archive":
                paired = "inbox" if os.path.exists(os.path.join(dir_, "inbox.md")) else "todo"
                name = f"{paired}.org_archive"
                targets.setdefault(name, ["", [], 0])
                targets[name][0] += org
                targets[name][1].append(real)
                targets[name][2] += count
        for name, (org, sources, count) in targets.items():
            head = archive_header() if name.endswith("_archive") else org_header("TODO")
            text = "\n".join(head) + org
            try:
                validate(text, f"{os.path.basename(home)}/{name}")
            except Bad as err:
                skipped.append(f"generated {err}")
                continue
            plan.setdefault(home, {})[name] = (text, sources, count)

    return plan, skipped, loose


prose_dropped = {}


def main():
    ap = argparse.ArgumentParser(description="Migrate line-schema todos to the org schema.")
    ap.add_argument("roots", nargs="+", help="directories to scan")
    ap.add_argument("--apply", action="store_true", help="write files and commit, per repo")
    args = ap.parse_args()

    plan, skipped, loose = collect(args.roots)

    total = sum(c for repo in plan.values() for _, _, c in repo.values())
    files = sum(len(repo) for repo in plan.values())
    print(f"{total} items into {files} org files\n")

    for home, targets in sorted(plan.items()):
        state = " (dirty, would skip)" if dirty(home) else ""
        print(f"  {os.path.basename(home)}{state}")
        for name, (text, sources, count) in sorted(targets.items()):
            print(f"    {name:<22} {count:>6} items  <- {len(sources)} board(s)")
        dropped = prose_dropped.get(home, 0)
        if dropped:
            print(f"    {'':<22} {dropped:>6} frontmatter lines dropped")

    if loose:
        print(f"\n  {len(loose)} boards outside any git repo, not committed")
    for err in skipped:
        print(f"  {err}")

    if not args.apply:
        print("\nDry run. Nothing written. Re-run with --apply to migrate.")
        return 0

    for home, targets in sorted(plan.items()):
        if dirty(home):
            print(f"\nskipping {home}: working tree is dirty")
            continue
        for name, (text, sources, _) in targets.items():
            open(os.path.join(home, name), "w", encoding="utf-8").write(text)
        subprocess.run(["git", "-C", home, "add", "-A"] + sorted(targets), check=True)
        subprocess.run(
            ["git", "-C", home, "rm", "-q"] + sorted(
                {s for v in targets.values() for s in v[1]}
            ),
            check=True,
        )
        items = sum(c for _, _, c in targets.values())
        subprocess.run(
            ["git", "-C", home, "commit", "-q", "-m",
             "refactor: migrate todos to the org schema",
             "-m", f"{items} items into {len(targets)} org files, by migrate_todo.py."],
            check=True,
        )
        print(f"\ncommitted {home}: {items} items into {len(targets)} org files")

    return 0


if __name__ == "__main__":
    sys.exit(main())
