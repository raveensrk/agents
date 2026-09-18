# TODO Schema

Canonical format for todo items in `inbox.md`, `todo.md`, and task lists.

## Inspiration

[todo.txt format](https://github.com/todotxt/todo.txt/blob/master/README.md)

But it is slightly adapted to my needs.

## Format

```markdown
- STATE: <content> +Project_Tag @Context_Tag created:YYYY-MM-DD completed:YYYY-MM-DD due:YYYY-MM-DD recurring:<interval> (A)
  - <optional sub-bullet details, free text>
```

- One item per top-level list line: uppercase state, colon, space, content.
- Metadata fields follow the content, in this order: `+Project_Tag @Context_Tag created: completed: due: recurring: (A)`. Each field is optional.
- `+Project_Tag` - optional project tag.
- `@Context_Tag` - optional context tag.
- `created:YYYY-MM-DD` - optional, absolute ISO dates only.
- `completed:YYYY-MM-DD` - optional, absolute ISO dates only.
- `due:YYYY-MM-DD` - optional, absolute ISO dates only.
- `recurring:<interval>` - optional recurrence: `daily`, `weekly`, `monthly`, `yearly`, or compact counts like `2d`, `3w`, `6m`. On completion, advance `due:` to the next occurrence instead of marking `DONE`.
- `(A)` - optional priority (A, B, or C); the last element on the line.
- Details go in nested sub-bullets (2-space indent), free-form.
- Change state by editing the prefix in place - don't delete items (git keeps the history); drop an item by marking it `OBSOLETE`.

## States

| State | Meaning |
|---|---|
| `TODO` | Not started |
| `IN_PROGRESS` | Actively being worked |
| `OPTIONAL` | Nice to have - do it if time permits |
| `LATER` | Deferred - worth doing, but not now |
| `DONE` | Completed |
| `OBSOLETE` | Dropped / no longer relevant (kept for history) |

Life cycle: `TODO → IN_PROGRESS → DONE`; any state can move to `OBSOLETE`. `OPTIONAL` and `LATER` items can be promoted to `TODO`/`IN_PROGRESS` or dropped to `OBSOLETE`.

## Reporting

When summarizing todos in reports, use the [Emoji Legend](emoji_legend.md):

| State | Emoji |
|---|---|
| `TODO`, `IN_PROGRESS`, `OPTIONAL`, `LATER` | ⏳ |
| `DONE` | ✅ |
| `OBSOLETE` | 🗑️ |
| Past `due:` date | ⚠️ (replaces the state emoji) |

## Example

```markdown
- TODO: File quarterly GST return +Finance @home created:2026-07-01 due:2026-07-20 (A)
  - Collect purchase invoices from the shared drive first
- TODO: Pay rent +Finance due:2026-08-05 recurring:monthly (A)
- IN_PROGRESS: Create a methodology presentation on wiki documentation
  - Showcase and demos with real use cases
- DONE: Create discord bot with claude completed:2026-06-28
- OBSOLETE: Create a skill to index all scripts in a directory
```

## Using from other repos

Reference this file - do not copy it. In the target repo's `AGENTS.md` / `CLAUDE.md`, add an import line pointing at your clone:

```markdown
@<clone-path>/todo_schema.md
```
