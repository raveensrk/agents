# TODO Schema

Canonical format for todo items in `inbox.md`, `todo.md`, and task lists.

**Legacy, during migration.** [Todo Schema (Lisp)](todo_schema_lisp.md) is where
the format is going. This one still parses and is still written by the existing
tools, but it takes no new features, and it is deleted once every item and every
tool has moved. Both formats are valid until then, and a file may hold a mix.

## Inspiration

[todo.txt format](https://github.com/todotxt/todo.txt/blob/master/README.md)

But it is slightly adapted to my needs.

## Format

```markdown
- STATE: [T<n>] <title> <metadata...> (A)
  - <optional detail, free text>
```

Every todo item is one line, and one regex parses it: see
[Reference regex](#reference-regex). Tools copy that regex instead of writing their own.

### Line

- One item per line: `- `, a state from [States](#states), `: `, then the content.
  `-` is the only bullet.
- `[T<n>]` - optional task ID, first element of the content. Allocation rules live in
  [Task Protocol](task.md) - never reuse a number.
- The title is free text. It may contain anything - links, URLs, colons, an `@` in an
  email or domain - but it must not end in something that looks like metadata.
- Metadata follows the title as space-separated tokens, in any order. Every token is
  optional.
- The priority `(A)`, `(B)` or `(C)` is optional and comes last.
- Nothing follows the metadata or the priority. Notes go in sub-bullets.
- Details go in sub-bullets, indented 2 spaces per level.
- Change state by editing the prefix in place. Drop an item by deleting the line (git
  keeps history).

### Checklists

`- [ ]` and `- [x]` lines are checklists - steps in a procedure, audit or test run
that you tick each time - not todo items. The reference regex never matches them.
Work to be done is a todo line with a state.

### Metadata tokens

| Token | Format | Example |
|---|---|---|
| Tag | `+` then letters, digits, `_` - a project or a kind | `+raveenkumar_xyz`, `+bug` |
| Context tag | `@` then letters, digits, `_` | `@backend` |
| `created:` | date or date-time | `created:2026-09-15` |
| `completed:` | date or date-time | `completed:2026-09-19` |
| `due:` | date or date-time | `due:2026-08-19T09:00` |
| `recurring:` | `daily`, `weekly`, `monthly`, `yearly`, or a count plus `d`, `w`, `m` or `y` | `recurring:2w` |

A tag ends at the first character that is not a letter, digit or `_`, so
`@raveenkumar.xyz` inside a title stays title text.

A task's kind is a tag, not a state: `+bug` when something behaves wrongly, `+fixme`
when it works but needs rework. The state tracks progress and the tag records the kind,
so a fixed bug stays findable as a `DONE` line with `+bug`.

```markdown
- TODO: Reset sequencing is incorrect +bug
```

On completing a `recurring:` item, advance `due:` to the next occurrence instead of
marking it `DONE`.

### Dates and times

- Date `YYYY-MM-DD`, or date-time `YYYY-MM-DDTHH:MM`.
- 24-hour clock, local time, no seconds, no time zone.
- One word, no spaces: `due:2026-08-19 09:00` splits into two tokens and breaks the line.
- Always zero-padded, so text order is time order.

Tools warn on any `created:`, `completed:` or `due:` value that does not match:

```regex
DATE = \d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])
TIME = T([01]\d|2[0-3]):[0-5]\d
```

| Value | Result |
|---|---|
| `due:2026-09-10` | valid |
| `due:2026-08-19T09:00` | valid |
| `due:2026-9-10` | invalid - month needs a leading zero |
| `due:2026-19-08` | invalid - month and day swapped |
| `due:2026-08-19T9:00` | invalid - hour needs a leading zero |

The pattern checks shape and ranges only. It accepts impossible dates such as
`2026-02-30`; a date parser rejects those.

### Reference regex

Anchored, one line. Groups: 1 indent, 2 state, 3 task number, 4 title, 5 metadata,
6 priority.

```regex
^(\s*)- (TODO|IN_PROGRESS|OPTIONAL|LATER|DONE|OBSOLETE): (?:\[T(\d+)\] )?(.+?)((?: (?:\+\w+|@\w+|(?:created|completed|due):\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])(?:T(?:[01]\d|2[0-3]):[0-5]\d)?|recurring:(?:daily|weekly|monthly|yearly|\d+[dwmy])))*)(?: \(([ABC])\))?$
```

## States

| State | Meaning |
|---|---|
| `TODO` | Not started |
| `IN_PROGRESS` | Actively being worked |
| `OPTIONAL` | Nice to have - do it if time permits |
| `LATER` | Deferred - worth doing, but not now |
| `DONE` | Completed |
| `OBSOLETE` | No longer relevant - kept for the record |

Life cycle: `TODO -> IN_PROGRESS -> DONE`. `OPTIONAL` and `LATER` items can be promoted to `TODO`/`IN_PROGRESS`, or dropped (delete the line). Any item can become `OBSOLETE` instead of being deleted, to keep the record.

## Reporting

When summarizing todos in reports, use the [Emoji Legend](emoji_legend.md):

| State | Emoji |
|---|---|
| `TODO`, `IN_PROGRESS`, `OPTIONAL`, `LATER` | ⏳ |
| `DONE` | ✅ |
| Past `due:` date | ⚠️ (replaces the state emoji) |

## Example

```markdown
- TODO: File quarterly GST return +Finance @home created:2026-07-01 due:2026-07-20 (A)
  - Collect purchase invoices from the shared drive first
- TODO: Pay rent +Finance due:2026-08-05 recurring:monthly (A)
- IN_PROGRESS: Create a methodology presentation on wiki documentation
  - Showcase and demos with real use cases
- DONE: Create discord bot with claude completed:2026-06-28
```
