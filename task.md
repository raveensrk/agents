# Task Protocol

Plain-text kanban for AI coding agents. Any agent can pick up and complete tasks.
All rules below are agent-agnostic - "the active agent" means whichever agent is running.

## Files

| File | Location | Purpose |
|---|---|---|
| `INBOX.md` | project root | Raw capture buffer: unsorted ideas awaiting review (see [Inbox Workflow](inbox.md)) |
| `TODO.md` | project root | Active board: `TODO` and `IN_PROGRESS` items |
| `ARCHIVE.md` | project root | History: `DONE` and `OBSOLETE` items. Append-only. |
| `tmp/` | project root | Scratch/temporary data for active tasks. Gitignored. |

## Heading

`TODO.md` and `ARCHIVE.md` must start with an H1 heading on line 1:

```markdown
# TODO

# ARCHIVE
```

## Task IDs

- Format: `[T<n>]` - e.g. `[T1]`, `[T12]`, `[T100]`
- Placed in the content field, right after the state: `- TODO: [T3] Add login handler +Auth created:2026-09-16 (A)`
- Allocation: scan both `TODO.md` and `ARCHIVE.md`, next = max + 1
- Monotonic: never reuse or recycle, even if task is `OBSOLETE`

## States

| State | Where | Meaning |
|---|---|---|
| `TODO` | `TODO.md` | Not started |
| `IN_PROGRESS` | `TODO.md` | Agent claimed it, actively working |
| `OPTIONAL` | `TODO.md` | Nice to have, not blocking |
| `LATER` | `TODO.md` | Deferred, worth doing eventually |
| `DONE` | `ARCHIVE.md` | Completed |
| `OBSOLETE` | `ARCHIVE.md` | Dropped / no longer relevant |

## Lifecycle

```
New task ─→ TODO (TODO.md)
              ↓
         IN_PROGRESS (TODO.md)
              ↓
         DONE (ARCHIVE.md)

Any state ─→ OBSOLETE (ARCHIVE.md)
```

- `OPTIONAL`/`LATER` can be promoted to `TODO`/`IN_PROGRESS`, or dropped to `OBSOLETE`.
- When completing: change prefix to `DONE:`, add `completed:YYYY-MM-DD`, move line to `ARCHIVE.md`.
- Append-only in `ARCHIVE.md` - never reorder or delete.

## Task line format

Follows the [Todo Schema](todo-schema.md).

```markdown
- IN_PROGRESS: [T4] Implement OAuth2 login flow +Auth @backend created:2026-09-16 due:2026-09-20 (A)
  - Acceptance criteria:
    - User can sign in via Google OAuth
    - Session persists across page reload
    - Logout clears session
  - Depends on: T2
```

Sub-bullets carry: acceptance criteria, dependencies, references, notes.
No `tags:` field - use `+Project` and `@Context` from the todo-schema.
No ordering rule within `TODO.md`.

## Claiming a task

1. Find a `TODO` task (any agent can pick any task).
2. Change `TODO:` to `IN_PROGRESS:` **before** starting work.
3. If the task is already `IN_PROGRESS` by another agent - skip it, pick another.
4. No ownership metadata - the `IN_PROGRESS` state itself is the claim.

## Completing a task

1. Verify against acceptance criteria (sub-bullets).
2. Change prefix to `DONE:`, add `completed:YYYY-MM-DD`.
3. Move the line from `TODO.md` to `ARCHIVE.md`.
4. Append to `ARCHIVE.md` - never edit existing lines.

## Dropping a task

1. Change prefix to `OBSOLETE:`.
2. Move the line from `TODO.md` to `ARCHIVE.md`.

## Temporary vs durable data

| What | Where | Git |
|---|---|---|
| Scratch notes, logs, debug output | `tmp/<T<n>>.md` | Ignored |
| Detailed specs, architecture notes | `docs/` | Tracked |
| All task metadata (state, id, priority, dates) | `TODO.md` | Tracked |

## Priority

`(A)` > `(B)` > `(C)`. Agents pick highest priority first, then lowest ID.
Priority is the last element on the line per the todo-schema.

## When to create a task

- Multi-step work that benefits from persistence.
- When the human asks to track something.
- Not for single-command trivialities.

## Session start

At session start, the active agent must read:

- `TODO.md` - current board state.
- `ARCHIVE.md` - avoid re-doing completed work, find the next task ID.