#!/usr/bin/env python3
"""Convert line-schema todo items to the lisp schema.

    - TODO: [T3] Pay rent +finance @home due:2026-08-05 (A)
    - @(todo T3 "Pay rent" (tag finance) (ctx home) (due 2026-08-05) (pri A))

Reads todo_schema.md, writes todo_schema_lisp.md. Dry run by default.

    migrate_todo.py ~/repos ~/dot            report only, writes nothing
    migrate_todo.py --apply ~/repos ~/dot    convert and commit, per repo

Safety, in order of how much it matters:

  1. --apply refuses a repo whose tree is dirty, so a revert undoes this and
     nothing else.
  2. Every converted line is reparsed before the file is written. One bad line
     leaves that whole file untouched.
  3. Fenced blocks, test fixtures and build output are never touched.
  4. A file reached twice through a symlink is converted once.
"""

import argparse
import os
import re
import subprocess
import sys

STATES = ["TODO", "IN_PROGRESS", "OPTIONAL", "LATER", "DONE", "OBSOLETE"]
KEYS = ["created", "completed", "due", "recurring"]
SKIP = {".git", "node_modules", "target", "tests", "fixtures", "dist", "build", ".venv"}
FENCE = ("```", "~~~")

# `- TODO: [T3] rest of the line`, any indent.
LINE = re.compile(r"^(\s*)- (" + "|".join(STATES) + r"): (?:\[T(\d+)\] )?(.*)$")

# One metadata token at the very end: +tag, @ctx, key:value.
META = re.compile(r"\s(\+\w+|@\w+|(?:" + "|".join(KEYS) + r"):\S+)$")

PRI = re.compile(r"\s\(([ABC])\)$")


class Bad(Exception):
    pass


def read(src):
    """Parse one `@(...)` form. Raises Bad with a column. Mirrors todo_schema_lisp.md."""
    at = src.find("@(")
    if at < 0:
        at = src.find("#(")
    if at < 0:
        raise Bad("no form")

    # at+2 skips the "@(" marker: the outer paren is already open, depth 1.
    i = at + 2
    out, cur, depth = [], "", 1
    stack = [out]

    while i < len(src):
        c = src[i]

        if c == '"':
            j, buf = i + 1, ""
            while True:
                if j >= len(src):
                    raise Bad(f"col {i + 1}: unterminated string")
                if src[j] == "\\":
                    if src[j + 1] not in '"\\':
                        raise Bad(f"col {j + 1}: bad escape")
                    buf += src[j + 1]
                    j += 2
                    continue
                if src[j] == '"':
                    break
                buf += src[j]
                j += 1
            stack[-1].append(("str", buf))
            i = j + 1
            continue

        if c == "(":
            sub = []
            stack[-1].append(("form", sub))
            stack.append(sub)
            depth += 1
            i += 1
            continue

        if c == ")":
            if cur:
                stack[-1].append(("sym", cur))
                cur = ""
            stack.pop()
            depth -= 1
            i += 1
            if depth == 0:
                return out, i
            continue

        if c in " \t":
            if cur:
                stack[-1].append(("sym", cur))
                cur = ""
            i += 1
            continue

        cur += c
        i += 1

    raise Bad(f"col {at + 1}: unbalanced form")


def check(src):
    """Reparse a converted line and validate it. Raises Bad."""
    body, _ = read(src)

    if not body or body[0][0] != "sym":
        raise Bad("missing state")

    seen = set()
    for kind, val in body[1:]:
        if kind != "form":
            continue
        if not val or val[0][0] != "sym":
            raise Bad("metadata needs a key")
        key = val[0][1]
        if key in seen:
            raise Bad(f"repeated key {key}")
        seen.add(key)
        if len(val) < 2:
            raise Bad(f"key {key} has no value")


def sym(tok):
    """Fold a tag or context to a schema symbol: lowercase, no underscores."""
    return tok.lower().replace("_", "-")


def convert(line):
    """One line-schema item to one lisp form. Returns None if the line is not an item."""
    m = LINE.match(line)
    if not m:
        return None

    indent, state, tid, rest = m.groups()

    pri = None
    hit = PRI.search(rest)
    if hit:
        pri, rest = hit.group(1), rest[: hit.start()]

    # Metadata sits at the end, so peel tokens off the tail until none is left.
    tags, ctxs, kv = [], [], {}
    while True:
        hit = META.search(rest)
        if not hit:
            break
        tok = hit.group(1)
        rest = rest[: hit.start()]
        if tok.startswith("+"):
            tags.insert(0, sym(tok[1:]))
        elif tok.startswith("@"):
            ctxs.insert(0, sym(tok[1:]))
        else:
            key, val = tok.split(":", 1)
            kv[key] = val

    title = rest.strip()
    if not title:
        raise Bad("empty title")

    out = [indent, "- @(", state.lower().replace("_", "-")]
    if tid:
        out.append(f" T{tid}")
    out.append(' "' + title.replace("\\", "\\\\").replace('"', '\\"') + '"')

    if tags:
        out.append(" (tag " + " ".join(tags) + ")")
    if ctxs:
        out.append(" (ctx " + " ".join(ctxs) + ")")
    for key in KEYS:
        if key in kv:
            out.append(f" ({key} {kv[key]})")
    if pri:
        out.append(f" (pri {pri})")
    out.append(")")

    return "".join(out)


def walk(root):
    """Yield every markdown file under root, skipping SKIP dirs and repeat visits."""
    seen = set()

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
            yield path


def migrate(path):
    """Convert one file. Returns (lines converted, new text, error). Writes nothing."""
    try:
        text = open(path, encoding="utf-8").read()
    except (UnicodeDecodeError, OSError) as err:
        return 0, None, str(err)

    out, count, fenced = [], 0, False

    for n, line in enumerate(text.splitlines(keepends=True), 1):
        bare = line.strip()

        # A form inside a fence is an example of the format, not work.
        if bare.startswith(FENCE):
            fenced = not fenced
            out.append(line)
            continue

        if fenced or not LINE.match(line):
            out.append(line)
            continue

        end = "\n" if line.endswith("\n") else ""
        try:
            form = convert(line.rstrip("\n"))
            check(form)
        except Bad as err:
            return 0, None, f"{path}:{n} - {err}"

        out.append(form + end)
        count += 1

    return count, "".join(out), None


def repo(path):
    """The git repo a path belongs to, or None."""
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


def main():
    ap = argparse.ArgumentParser(description="Convert line-schema todos to the lisp schema.")
    ap.add_argument("roots", nargs="+", help="directories to scan")
    ap.add_argument("--apply", action="store_true", help="write files and commit per repo")
    args = ap.parse_args()

    # repo -> [(path, text, count)], plus files that could not be converted.
    plan, skipped, loose = {}, [], []

    for root in args.roots:
        for path in walk(os.path.expanduser(root)):
            count, text, err = migrate(path)
            if err:
                skipped.append(err)
                continue
            if not count:
                continue
            home = repo(path)
            if not home:
                loose.append((path, text, count))
                continue
            plan.setdefault(home, []).append((path, text, count))

    total = sum(c for files in plan.values() for _, _, c in files) + sum(c for _, _, c in loose)
    print(f"{total} lines in {sum(len(f) for f in plan.values()) + len(loose)} files\n")

    for home, files in sorted(plan.items()):
        lines = sum(c for _, _, c in files)
        state = "dirty, would skip" if dirty(home) else "clean"
        print(f"  {os.path.basename(home):<20} {lines:>5} lines  {len(files):>4} files  ({state})")

    if loose:
        print(f"\n  {len(loose)} files outside any git repo, not committed")

    for err in skipped:
        print(f"  skipped {err}")

    if not args.apply:
        print("\nDry run. Nothing written. Re-run with --apply to convert.")
        return 0

    for home, files in sorted(plan.items()):
        if dirty(home):
            print(f"\nskipping {home}: working tree is dirty")
            continue

        for path, text, _ in files:
            open(path, "w", encoding="utf-8").write(text)

        lines = sum(c for _, _, c in files)
        subprocess.run(["git", "-C", home, "add"] + [p for p, _, _ in files], check=True)
        subprocess.run(
            ["git", "-C", home, "commit", "-q", "-m",
             "refactor: convert todos to the lisp schema",
             "-m", f"{lines} items in {len(files)} files, converted by migrate_todo.py."],
            check=True,
        )
        print(f"\ncommitted {home}: {lines} lines in {len(files)} files")

    return 0


if __name__ == "__main__":
    sys.exit(main())
