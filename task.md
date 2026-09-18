# Task Protocol

Plain-text kanban for AI coding agents. Any agent can pick up and complete tasks.
All rules below are agent-agnostic - "the active agent" means whichever agent is running.

## Files

| File | Location | Purpose |
|---|---|---|
| `inbox.md` | `docs/notes/` | Raw capture buffer: unsorted ideas awaiting review (see [Inbox Workflow](inbox.md)) |
| `todo.md` | `docs/notes/` | Active board: `TODO` and `IN_PROGRESS` items |
| `archive.md` | `docs/notes/` | History: `DONE` and `OBSOLETE` items. Append-only. |
| `tmp/` | project root | Scratch/temporary data for active tasks. Gitignored. |

## Heading

`todo.md` must start with `# TODO`. `archive.md` must start with `# Archive`.

## Task IDs

- Format: `[T<n>]` - e.g. `[T1]`, `[T12]`, `[T100]`
- Placed in the content field, right after the state: `- TODO: [T3] Add login handler +Auth created:2026-09-16 (A)`
- Allocation: scan both `todo.md` and `archive.md`, next = max + 1
- Monotonic: never reuse or recycle, even if task is `OBSOLETE`

## States

| State | Where | Meaning |
|---|---|---|
| `TODO` | `todo.md` | Not started |
| `IN_PROGRESS` | `todo.md` | Agent claimed it, actively working |
| `OPTIONAL` | `todo.md` | Nice to have, not blocking |
| `LATER` | `todo.md` | Deferred, worth doing eventually |
| `DONE` | `archive.md` | Completed |
| `OBSOLETE` | `archive.md` | Dropped / no longer relevant |

## Lifecycle

```
New task ─→ TODO (todo.md)
              ↓
         IN_PROGRESS (todo.md)
              ↓
         DONE (archive.md)

Any state ─→ OBSOLETE (archive.md)
```

- `OPTIONAL`/`LATER` can be promoted to `TODO`/`IN_PROGRESS`, or dropped to `OBSOLETE`.
- When completing: change prefix to `DONE:`, add `completed:YYYY-MM-DD`, move line to `archive.md`.
- Append-only in `archive.md` - never reorder or delete.

## Task line format

Follows the [Todo Schema](todo_schema.md).

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
No ordering rule within `todo.md`.

## Claiming a task

1. Find a `TODO` task (any agent can pick any task).
2. Change `TODO:` to `IN_PROGRESS:` **before** starting work.
3. If the task is already `IN_PROGRESS` by another agent - skip it, pick another.
4. No ownership metadata - the `IN_PROGRESS` state itself is the claim.

## Completing a task

1. Verify against acceptance criteria (sub-bullets).
2. Change prefix to `DONE:`, add `completed:YYYY-MM-DD`.
3. Move the line from `todo.md` to `archive.md`.
4. Append to `archive.md` - never edit existing lines.

## Dropping a task

1. Change prefix to `OBSOLETE:`.
2. Move the line from `todo.md` to `archive.md`.

## Temporary vs durable data

| What | Where | Git |
|---|---|---|
| Scratch notes, logs, debug output | `tmp/<T<n>>.md` | Ignored |
| Detailed specs, architecture notes | `docs/` | Tracked |
| All task metadata (state, id, priority, dates) | `todo.md` | Tracked |

## Priority

`(A)` > `(B)` > `(C)`. Agents pick highest priority first, then lowest ID.
Priority is the last element on the line per the todo-schema.

## When to create a task

- Multi-step work that benefits from persistence.
- When the human asks to track something.
- Not for single-command trivialities.

## Session start

At session start, the active agent must read:

- `docs/notes/todo.md` - current board state.
- `docs/notes/archive.md` - avoid re-doing completed work, find the next task ID.