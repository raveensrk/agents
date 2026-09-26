#!/usr/bin/env python3
"""Delete items from a declutter selection.json. Dry run by default."""
import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path

HOME = Path.home()
TRASH = HOME / ".Trash"
BREW_PREFIX = Path("/opt/homebrew")
CELLAR = BREW_PREFIX / "Cellar"
CASKROOM = BREW_PREFIX / "Caskroom"
SAFE_ROOTS = ["/Applications", str(HOME), str(CELLAR), str(CASKROOM)]


IGNORE_FILE = Path.home() / ".config" / "declutter" / "ignored.json"


def merge_ignore(existing, adding):
    return sorted(set(existing) | {a for a in adding if a})


def save_ignore(selection_path):
    sel = json.loads(Path(selection_path).read_text())
    adding = [i.get("path") for i in sel.get("ignore", [])]
    try:
        existing = json.loads(IGNORE_FILE.read_text())
    except Exception:
        existing = []
    IGNORE_FILE.parent.mkdir(parents=True, exist_ok=True)
    merged = merge_ignore(existing, adding)
    IGNORE_FILE.write_text(json.dumps(merged, indent=1))
    return len(merged)


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return p.stdout + p.stderr


def safe(path):
    # ponytail: absolute() not resolve() - /Applications apps are symlinks into /System
    p = Path(path).absolute()
    return p != Path("/") and any(str(p).startswith(r) for r in SAFE_ROOTS)


def trash(path):
    src = Path(path)
    if not src.exists():
        return f"skip (missing): {path}"
    dest = TRASH / src.name
    if dest.exists():
        dest = TRASH / f"{src.name}.{int(time.time())}"
    try:
        shutil.move(str(src), str(dest))
        return f"trashed {src}"
    except (PermissionError, OSError):
        # /Applications apps are root-owned - Finder prompts for admin
        out = run(["osascript", "-e",
                   f'tell application "Finder" to delete POSIX file "{src}"'])
        if out.strip() and "error" not in out.lower():
            return f"trashed via Finder {src}"
        return f"FAILED {src}: Finder said {out.strip()[:120]}"


def plan(item, execute):
    kind, name = item["kind"], item.get("name", "?")
    if not safe(item.get("path", "/")):
        return f"BLOCKED {name}: unsafe path {item.get('path')}"
    if kind == "cask":
        if not execute:
            return f"would run: brew uninstall --cask {item.get('cask') or name}"
        out = run(["brew", "uninstall", "--cask", item.get("cask") or name])
        return f"brew cask {item.get('cask') or name}: {out.strip().splitlines()[-1] if out.strip() else 'ok'}"
    if kind == "formula":
        used = run(["brew", "uses", "--installed", name]).split()
        if used:
            return f"BLOCKED {name}: required by {' '.join(used[:3])} - deselect it"
        if not execute:
            return f"would run: brew uninstall {name}"
        out = run(["brew", "uninstall", name])
        return f"brew formula {name}: {out.strip().splitlines()[-1] if out.strip() else 'ok'}"
    if kind in ("app", "leftover"):
        if not execute:
            return f"would trash {item['path']}"
        return trash(item["path"])
    return f"BLOCKED {name}: unknown kind {kind}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("selection", nargs="?", help="path to declutter-selection.json")
    ap.add_argument("--execute", action="store_true", help="apply for real (default: dry run)")
    ap.add_argument("--save-ignore", action="store_true",
                    help="merge selection's ignore list into the persistent ignore file, then exit")
    args = ap.parse_args()
    if args.save_ignore:
        n = save_ignore(args.selection)
        print(f"ignore list now has {n} entr(y/ies): {IGNORE_FILE}")
        return
    with open(args.selection) as f:
        items = json.load(f).get("items", [])
    print(f"{len(items)} item(s) selected\n")
    for it in items:
        try:
            print(plan(it, args.execute))
        except Exception as e:
            print(f"FAILED {it.get('name', '?')}: {e}")
    if not args.execute:
        print("\nDRY RUN - re-run with --execute to apply.")
    else:
        print("\nDone. Empty the Trash once happy to reclaim the space.")


if __name__ == "__main__":
    main()
