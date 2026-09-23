---
description: Convert line-schema todos to the lisp schema, one repo at a time
argument-hint: [dir ...] [--apply]
allowed-tools: Read, Glob, Grep, Bash(python3:*), Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git -C:*)
disable-model-invocation: false
---

# Migrate todos to the lisp schema

## Target

`$ARGUMENTS`

Directories to scan. Default to `~/repos ~/dot` when none are given.

## What this does

Rewrites every line-schema item as a form, per
[Todo Schema (Lisp)](../todo_schema_lisp.md):

```markdown
- TODO: [T3] Pay rent +finance @home due:2026-08-05 (A)
- @(todo T3 "Pay rent" (tag finance) (ctx home) (due 2026-08-05) (pri A))
```

The conversion is done by `scripts/migrate_todo.py`, beside this file. Run the
script. Do not convert lines yourself: a deterministic pass over thousands of
lines is the point, and an agent editing them by hand is slower, costlier and
less repeatable.

## Steps

1. Dry run first, always. It writes nothing.

   ```bash
   python3 <this plugin>/scripts/migrate_todo.py ~/repos ~/dot
   ```

2. Show me the report. Per repo: lines, files, and whether the tree is clean.
   Name every skipped file and why.

3. Stop if anything looks wrong. A repo you did not expect, a file count far
   off, any skipped file - raise it before writing.

4. On my go-ahead, apply. Each repo is converted and committed on its own, and
   a repo with a dirty tree is skipped rather than mixed into my work.

   ```bash
   python3 <this plugin>/scripts/migrate_todo.py --apply ~/repos ~/dot
   ```

5. Report what landed: the commit in each repo, and which repos were skipped for
   being dirty so I can come back to them.

## Rules

- Never pass `--apply` on your own. It is mine to authorise, every run.
- Never edit the script to get a file through. A file the script refuses is a
  schema question, not a script bug - tell me what it choked on.
- Do not touch `todo_schema.md`, `todo_schema_lisp.md` or any doc that teaches
  the old format. Their examples are documentation, and the script already skips
  fenced blocks.
- Do not convert test fixtures. The script skips `tests/` and `fixtures/`
  because code asserts on those exact strings.
- Both formats parse during the migration, so a half-converted vault is fine. A
  half-converted *file* is not, and the script guarantees that: one bad line
  leaves the whole file untouched.

## What the script guarantees

| Guarantee | How |
|---|---|
| A revert undoes one repo | One commit per repo, dirty trees refused |
| No half-converted file | Every line reparsed before the file is written |
| Examples survive | Fenced blocks skipped |
| Tests survive | `tests/`, `fixtures/`, `target/`, `node_modules/` skipped |
| A symlinked file converts once | Paths resolved before conversion |
| IDs untouched | Existing `[T<n>]` carried over, none invented |

## Report format

```
9787 lines in 18 files

  notebook              9681 lines     3 files  (dirty, would skip)
  website                 61 lines     3 files  (clean)
  work                    12 lines     3 files  (clean)
  skipped notes/old.md:44 - col 31: unterminated string

Dry run. Nothing written.
```

Lead with the totals, then the per-repo table, then skipped files. No preamble.
