#!/usr/bin/env python3
"""Install this repo's skills and commands into each agent harness, as symlinks.

Every installed item is a symlink back to this checkout, so `git pull` updates
all harnesses at once. Directories that several harnesses read (like
~/.agents/skills) get one link, not one per harness.

Usage:
  ./install.py              install or update
  ./install.py --dry-run    show what would change, change nothing
  ./install.py --force      also replace symlinks that point somewhere else
  ./install.py --uninstall  remove every link that points into this checkout

Safety:
  - Never deletes or overwrites a real file or directory, even with --force.
  - Only removes symlinks that point into this checkout.
  - A harness that is not installed (its home directory is missing) is skipped.

To add a harness or item type, add a line to HARNESSES or TARGETS.
"""
import glob, os, sys

REPO = os.path.dirname(os.path.realpath(__file__))

# Harness name -> directory whose presence means the harness is installed.
HARNESSES = {
    "claude": "~/.claude",
    "codex": "~/.codex",
    "pi": "~/.pi",
}

# (source glob in this repo, destination directory, harnesses that read it).
# A glob ending in SKILL.md installs the directory holding it, so a stray file
# in skills/ is never installed as a skill.
TARGETS = [
    ("skills/*/SKILL.md", "~/.claude/skills", ["claude"]),
    ("skills/*/SKILL.md", "~/.agents/skills", ["codex", "pi"]),  # shared: one link for both
    ("commands/*.md", "~/.claude/commands", ["claude"]),
    ("commands/*.md", "~/.pi/agent/prompts", ["pi"]),  # Codex has no custom commands
]


def sources(pattern):
    out = []
    for path in sorted(glob.glob(os.path.join(REPO, pattern))):
        if os.path.basename(path) == "SKILL.md":
            path = os.path.dirname(path)
        elif not os.path.isfile(path):
            continue
        out.append(path)
    return out


def link_target(link):
    """Absolute, resolved path a symlink points to (it may not exist)."""
    return os.path.realpath(os.path.join(os.path.dirname(link), os.readlink(link)))


def ours(link):
    return os.path.islink(link) and link_target(link).startswith(REPO + os.sep)


class Run:
    def __init__(self, dry, force):
        self.dry, self.force, self.conflicts, self.errors = dry, force, 0, 0

    def apply(self, fn, *args):
        """Run one change; report an OS error and carry on with the rest."""
        try:
            fn(*args)
        except OSError as e:
            self.errors += 1
            self.say("error", args[-1], f"{e.strerror or e}")

    def say(self, action, path, note=""):
        home = os.path.expanduser("~")
        path = "~" + path[len(home):] if path.startswith(home + os.sep) else path
        print(f"{action:<9} {path}{'  ' + note if note else ''}")

    def remove(self, link, note):
        self.say("remove", link, note)
        if not self.dry:
            self.apply(os.unlink, link)

    def link(self, src, dest):
        if os.path.islink(dest):
            if link_target(dest) == os.path.realpath(src):
                return self.say("ok", dest)
            if not (self.force or ours(dest)):
                self.conflicts += 1
                return self.say("conflict", dest, f"symlink to {os.readlink(dest)}; use --force")
            self.say("replace", dest, f"was -> {os.readlink(dest)}")
            if not self.dry:
                self.apply(os.unlink, dest)
        elif os.path.lexists(dest):
            self.conflicts += 1
            return self.say("conflict", dest, "real file or directory; move it away by hand")
        else:
            self.say("link", dest)
        if not self.dry:
            self.apply(self._symlink, src, dest)

    @staticmethod
    def _symlink(src, dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        os.symlink(src, dest)

    def prune(self, dest_dir, wanted):
        """Remove our links whose source is gone or no longer installed here."""
        if not os.path.isdir(dest_dir):
            return
        for name in sorted(os.listdir(dest_dir)):
            path = os.path.join(dest_dir, name)
            if ours(path) and name not in wanted:
                self.remove(path, "stale")


def installed(harness):
    return os.path.isdir(os.path.expanduser(HARNESSES[harness]))


def main():
    args = set(sys.argv[1:])
    unknown = args - {"--dry-run", "--force", "--uninstall", "-h", "--help"}
    if unknown or args & {"-h", "--help"}:
        print(__doc__.strip())
        sys.exit(2 if unknown else 0)
    run = Run("--dry-run" in args, "--force" in args)
    if run.dry:
        print("dry run: nothing will change")

    dest_dirs = sorted({os.path.expanduser(d) for _, d, _ in TARGETS})
    if "--uninstall" in args:
        for d in dest_dirs:
            if os.path.isdir(d):
                for name in sorted(os.listdir(d)):
                    if ours(os.path.join(d, name)):
                        run.remove(os.path.join(d, name), "uninstall")
        sys.exit(1 if run.errors else 0)

    # Plan everything first, so a bad table stops before any change.
    wanted, plan = {d: set() for d in dest_dirs}, []
    for pattern, dest_dir, readers in TARGETS:
        dest_dir = os.path.expanduser(dest_dir)
        if not any(installed(h) for h in readers):
            run.say("skip", dest_dir, f"{', '.join(readers)} not installed")
            continue
        for src in sources(pattern):
            name = os.path.basename(src)
            if name in wanted[dest_dir]:
                sys.exit(f"ERROR: two sources named {name} target {dest_dir}; rename one")
            wanted[dest_dir].add(name)
            plan.append((src, os.path.join(dest_dir, name)))
    for src, dest in plan:
        run.link(src, dest)
    for d in dest_dirs:
        run.prune(d, wanted[d])

    if run.conflicts or run.errors:
        print(f"\n{run.conflicts} conflict(s), {run.errors} error(s); see the lines above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
