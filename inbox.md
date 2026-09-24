# Inbox Workflow

Landing zone for raw, unsorted, unorganized ideas and notes. The capture buffer
of the [task protocol](todo_schema.org). Temporary by design - items get triaged, never
live here forever.

## Files

| File | Location | Purpose |
|---|---|---|
| `inbox.md` | `docs/notes/` | Raw capture buffer: unsorted ideas and notes |
| `todo.md` | `docs/notes/` | Active tasks - promoted from inbox |
| `archive.md` | `docs/notes/` | Completed task history |
| `docs/` | project root | Durable knowledge - promoted from inbox |

## When to capture

The active agent must write to `inbox.md` when the human says any of:

- "remember me to do X"
- "remind me to do X"
- "create a task"
- "note this down"
- "save it for later"
- "save this"

Capture anything that cannot go into tasks or docs:

- Vague ideas not yet shaped into a task.
- Things without clear acceptance criteria.
- Raw information the human wants to review later.

## When NOT to capture

- Well-defined work with clear acceptance criteria - write it straight to the board as a task (see [task protocol](todo_schema.org)). Inbox is only for vague or unorganized items - no queue, no confirmation step.
- Durable knowledge - write to `docs/`.
- Single-command trivialities - just do it, do not store.

## Format

One line per item. Follows the [Todo Schema](todo_schema.md) (`TODO:` prefix, absolute dates), minus IDs and priorities - inbox items are raw.

```markdown
- TODO: <content> created:YYYY-MM-DD
  - <optional sub-bullet detail, free text>
```

Example:

```markdown
- TODO: Ideas for a dashboard to visualize agent task throughput created:2026-09-16
  - Maybe weekly trends, top blocked tasks
```

## Heading

`inbox.md` must start with an H1 heading on line 1:

```markdown
# INBOX
```

## Review and triage

The human reviews `inbox.md` and decides for each item. The agent may suggest, the human decides.

| Decision | Action |
|---|---|
| Make it a task | Move to `todo.md`, assign next `[T<n>]`, keep the `created:` date |
| Durable knowledge | Move to `docs/`, file where appropriate |
| Drop it | Remove the line - git keeps history |

After triage, remove the line from `inbox.md`. It is temporary, not a ledger.

## Session start

At session start, read:

- `docs/notes/inbox.md` - pending ideas awaiting triage.