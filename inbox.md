# Inbox Workflow

Landing zone for raw, unsorted, unorganized ideas and notes. The capture buffer
of the [Task Protocol](task.md). Temporary by design - items get triaged, never
live here forever.

## Files

| File | Location | Purpose |
|---|---|---|
| `INBOX.md` | project root | Raw capture buffer: unsorted ideas and notes |
| `TODO.md` | project root | Active tasks - promoted from inbox |
| `ARCHIVE.md` | project root | Completed/dropped task history |
| `docs/` | project root | Durable knowledge - promoted from inbox |

## When to capture

The active agent must write to `INBOX.md` when the human says any of:

- "remember me to do X"
- "remind me to do X"
- "note this down"
- "save it for later"
- "save this"

Capture anything that cannot go into tasks or docs:

- Vague ideas not yet shaped into a task.
- Things without clear acceptance criteria.
- Raw information the human wants to review later.

## When NOT to capture

- Well-defined work with clear acceptance criteria - write it straight to `TODO.md` as a `[T<n>]` task (see [Task Protocol](task.md)). Inbox is only for vague or unorganized items - no queue, no confirmation step.
- Durable knowledge - write to `docs/`.
- Single-command trivialities - just do it, do not store.

## Format

One line per item. Follows the [Todo Schema](todo-schema.md) where possible (line prefix, absolute dates), minus states, IDs, and priorities - inbox items are raw.

```markdown
- 📥 <content> created:YYYY-MM-DD
  - <optional sub-bullet detail, free text>
```

Example:

```markdown
- 📥 Ideas for a dashboard to visualize agent task throughput created:2026-09-16
  - Maybe weekly trends, top blocked tasks
```

The `📥` prefix comes from the [emoji legend](emoji_legend.md): new / incoming / not yet triaged.

## Heading

`INBOX.md` must start with an H1 heading on line 1:

```markdown
# INBOX
```

## Review and triage

The human reviews `INBOX.md` and decides for each item. The agent may suggest, the human decides.

| Decision | Action |
|---|---|
| Make it a task | Move to `TODO.md`, assign next `[T<n>]`, keep the `created:` date |
| Durable knowledge | Move to `docs/`, file where appropriate |
| Drop it | Remove the line - git keeps history |

After triage, remove the line from `INBOX.md`. It is temporary, not a ledger.

## Session start

At session start, read:

- `INBOX.md` - pending ideas awaiting triage.
- `TODO.md` - active tasks.
- `ARCHIVE.md` - completed work and next task ID.