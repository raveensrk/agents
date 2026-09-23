---
name: git-report
description: Report the git commits a person made across all their repos, local and remote, all branches, for any time window (default the last 24 hours, configurable). Use when the user asks what they worked on, for a work log, standup notes, a daily or weekly report, or "my commits since X".
---

# Git report

Report the git work I did in a time window. The bundled script collects the
data; you only choose the window and write the report.

## Requirements

- git 2.31+ and python 3.11+.
- A config at `~/.local/git_report.toml`. Each person keeps their own:

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

  # Optional. Window used when no start is given: the last N hours up to
  # the end. Any number above 0 (168 = one week). Defaults to 24.
  default_hours = 24
  ```

## What the script counts

- **Repos:** Every git repo under `dirs`, plus each entry in `repos`. Submodules and nested repos are included. Worktrees and duplicates are counted once.
- **Commits:** Local and remote commits on all branches. Merge commits are skipped.
- **Authors:** Only commits whose author email is in `emails`.
- **Time:** The author date must fall inside the window. A rebased or amended copy of the same commit is listed once.
- **Safety:** Read-only. The script only runs `git fetch` and, for remote URLs, `git clone --mirror` into `~/.cache/git_report/`. Fetch never prompts for a password, and each fetch times out after 180s.

## Hard rules

- Run `scripts/git_report.py` from this skill's directory, unchanged. Do not
  replace it with your own git commands.
- Read-only. Never pull, checkout, reset, stash, commit, push, or change git
  config in any repo.
- Report only what the script outputs. Never invent, merge, or drop commits,
  and never add authors that are not in the config.
- If the script prints a line starting with `ERROR:`, stop. Show that line
  and how to fix it. If the config is missing, show the template above.

## Step 1 - Window

1. If the user gave no window, pass no flags. The script uses the last
   `default_hours` from the config (24 if unset), ending now.
2. If the user gave a window, convert it to local time in the form
   `YYYY-MM-DD HH:MM` (or `YYYY-MM-DD` for midnight). Work out relative
   phrases ("yesterday 11am to 4am today", "since Monday") from the current
   local date and time (run `date`). Pass `--start` and `--end`. With only a
   start, omit `--end` (it defaults to now). With only an end, omit
   `--start` (it defaults to `default_hours` before the end).
3. If the window is ambiguous, ask one question before running anything.

## Step 2 - Run

Run from any directory, with `<skill_dir>` being the directory holding this
file. It can take a few minutes, because it fetches every repo first.

```bash
python3 <skill_dir>/scripts/git_report.py --start "YYYY-MM-DD HH:MM" --end "YYYY-MM-DD HH:MM"
```

The output is JSON:

- `window`: the start and end that were used
- `repos_scanned`: the number of unique repos
- `repos_with_commits`: for each repo, its commits with `time`, `hash`,
  `author`, `subject`, `body`, `stat`, `branches`, and `pushed`
  (false = local-only)
- `skipped`: config entries that do not exist or failed to clone
- `fetch_failed`: repos whose fetch failed (their remote data may be stale)

## Step 3 - Report

Write the report as plain text in chat. Do not create a file.

1. Header line: the window (start to end, with the timezone), the total
   number of commits, and the number of repos with commits.
2. Group commits by repo (use the repo folder name), in time order.
3. One line per commit: time (`HH:MM`, with the date when the window spans
   several days), short hash, branch, pushed or local-only, a plain-language
   summary drawn from the subject and body (not the raw subject line), size
   (+/- lines when notable), and author email.
4. "Themes": 3 bullets that group the work by topic.
5. "Skipped" and "Fetch failed": list each entry with its reason. Leave a
   section out if it is empty.
6. If there are no commits, say so plainly and still show item 5.
7. End with one next action.
