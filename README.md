# agents

Reusable AI agent instructions. Import them into your own project instead of
copying and drifting.

## 1. Clone

```bash
git clone https://github.com/raveensrk/agents.git ~/repos/agents
```

Any path works. The rest of this file assumes `~/repos/agents`.

## 2. Point your agent at it

| Agent | Scope | File to edit |
|---|---|---|
| Claude Code | one project | `<project>/CLAUDE.md` |
| Claude Code | every project | `~/.claude/CLAUDE.md` |
| Codex | one project | `<project>/AGENTS.md` |
| Codex | every project | `~/.codex/AGENTS.md` |

### Claude Code

Claude Code expands `@` imports, so one line pulls the whole file in:

```markdown
@~/repos/agents/common.md
```

### Codex

Codex has no import syntax - it reads `AGENTS.md` verbatim. Give it an
instruction it can act on instead:

```markdown
At session start, read `~/repos/agents/common.md` and follow it.
```

### Both in one project

Keep the rules in `AGENTS.md` and make `CLAUDE.md` a one-line pointer, so the
two agents never drift apart:

```markdown
@AGENTS.md
```

## Path rules

- Use a `~/` path. `$HOME` is not expanded, and `/Users/<name>/` breaks on
  another machine.
- Confirm it resolves before you rely on it:

  ```bash
  ls ~/repos/agents/common.md
  ```

  A wrong path fails silently. The agent told to read a missing file just
  carries on without the rules.

## 3. Verify it loaded

Start a session and ask:

> What punctuation rule do I follow for dashes?

Correct answer: plain hyphens only, never em dashes or en dashes. Any other
answer means the import did not load.

## Files

| File | What it covers |
|---|---|
| `code_style.md` | How to write code |
| `common.md` | Session start, working style, output style |
| `emoji_legend.md` | Status emoji vocabulary for agent reports |
| `git.md` | Commits and pull requests |
| `inbox.md` | Inbox workflow - raw capture buffer (`docs/notes/inbox.md`) |
| `jobs.md` | ETA rules for long-running jobs |
| `prompts.md` | Personal paste-bin of chat prompts |
| `task.md` | Task protocol - kanban in `docs/notes/todo.md` / `archive.md` |
| `todo_schema.md` | Canonical todo item format |
| `terminologies.md` | Shared prompting vocabulary |
| `use_case.md` | What these agents get used for |
