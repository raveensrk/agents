# TODO Schema (Lisp)

The todo format this vault is moving to, in markdown files and in code
comments alike.

Both formats are allowed during the migration. [Todo Schema](todo_schema.md) -
the line format - still parses, still gets written by existing tools, and takes
no new features. This one is where the format is going.

`todo_schema.md` is deleted once the migration finishes, and this schema is then
the only one. See [Migration](#migration).

## Inspiration

[todo.txt format](https://github.com/todotxt/todo.txt/blob/master/README.md) for
the fields, [s-expressions](https://en.wikipedia.org/wiki/S-expression) for the
shape.

The line schema needs a 400-character regex because the title and the metadata
share one flat line. Parentheses separate them, so a reader replaces the regex.

## Format

In a markdown file:

```markdown
- @(<state> <id> "<title>" (<key> <value>...) ...)
```

In a source file, after any comment marker:

```rust
// @(<state> <id> "<title>" (<key> <value>...) ...)
```

One item is one balanced form. In markdown it stays on one line, so `grep`,
`sed` and line diffs keep working. In a source file it may wrap across comment
lines, because a comment is often narrower than the form; see
[In code comments](#in-code-comments).

### Line

- One item per line: `- ` then `@(`, then a single balanced form. `-` is the
  only bullet.
- The head symbol is the state, from [States](#states): `@(todo ...)`,
  `@(done ...)`. There is no `task` head - `@(` already says this is a task.
- A bare symbol after the head is the optional task ID: `T3`. Allocation rules
  live in [Task Protocol](task.md) - never reuse a number.
- The title is a double-quoted string, and it is the first quoted token. Write
  `\"` for a quote and `\\` for a backslash. Everything else - parens, colons,
  `@`, URLs - is literal text, so a title can never look like metadata.
- Metadata are nested forms after the title, in any order. Every one is
  optional.
- Nothing follows the closing paren on a markdown line. In a source file one
  comment terminator may follow - `*/`, `-->` or `#|` - and nothing else:
  `/* @(todo "x") */` is valid, `@(todo "x") see also foo` is not.
- A markdown item may be indented. Leading whitespace is not part of the item.
- Everything is case-sensitive. States and keys are lowercase; `@(TODO ...)` is
  not a task. An ID is an uppercase `T` then digits: `T3`, never `t3`.
- Details go in `(note "...")`, inside the form. A sub-bullet under an item is
  prose for a human, carries no task data, and no tool reads it.
- Change state by editing the head symbol in place. Drop an item by deleting the
  line (git keeps history).

### Delimiters

`@(` opens every item, in markdown and in code alike. One rule, one grep
pattern, and a form copied out of a code comment into `todo.md` stays valid
unchanged.

A bare `(` opens every nested form inside it.

`#(` is a synonym: a reader must accept it, a writer must never emit it. One
spelling goes into files, so `rg '@\(' ` finds everything.

Measured 2026-09-23 against pandoc's GitHub-flavoured renderer and `grep`:

| Form | In markdown | `grep` as typed | Collides with |
|---|---|---|---|
| `(todo ...)` | literal | yes | a real `(todo ...)` call in Lisp source |
| `#(todo ...)` | literal | yes | near nothing |
| `@(todo ...)` | literal | yes | near nothing |
| `[todo ...]` | becomes a link when a paren follows | no, `[` opens a character class | array syntax |
| `<todo ...>` | disappears, parsed as raw HTML | yes | generics |
| `{todo ...}` | literal | yes | every C-family brace |

Square and angle brackets are out on evidence, not taste: `- <todo>` renders as
an empty bullet, and `grep '[todo'` is a syntax error.

### Symbols are lowercase kebab-case

Markdown italicizes paired `_` inside a list item, so a bare symbol like
`raveen_kumar_xyz` renders as `raveen*kumar*xyz`. Symbols use kebab-case
instead: `raveenkumar-xyz`, `in-progress`. An underscore is invalid in a symbol.

Symbols are lowercase. `Finance` and `finance` would otherwise be two tags, and
the existing corpus already holds both spellings of exactly that word.

The line schema escapes this because its tags sit behind `+` and `@`, which most
renderers leave alone.

### Fenced code blocks

A form inside a ``` or ~~~ fence is an example of the format, not work. Readers
skip fenced blocks, which is what keeps this document's own examples out of your
task list.

A form in a source file is the exception: code is where real work items live, so
a comment inside a fenced block in markdown is still an example, while the same
comment in a `.rs` file is a task.

### Checklists

`- [ ]` and `- [x]` lines are checklists - steps in a procedure, audit or test
run that you tick each time - not todo items. In markdown a todo line always
starts with `- @(`, so the two never collide.

### Metadata forms

| Form | Contents | Example |
|---|---|---|
| `(tag ...)` | one or more symbols - project or kind | `(tag raveenkumar-xyz bug)` |
| `(ctx ...)` | one or more context symbols | `(ctx backend home)` |
| `(created ...)` | date or date-time | `(created 2026-09-15)` |
| `(completed ...)` | date or date-time | `(completed 2026-09-19)` |
| `(due ...)` | date or date-time | `(due 2026-08-19T09:00)` |
| `(recurring ...)` | `daily`, `weekly`, `monthly`, `yearly`, or a count plus `d`, `w`, `m` or `y`. An optional leading `from-done` counts from `(completed ...)` instead of from `(due ...)` | `(recurring 2w)`, `(recurring from-done 3w)` |
| `(pri ...)` | `A`, `B` or `C` | `(pri A)` |
| `(note ...)` | one or more quoted strings, each a detail | `(note "only leaks on the retry path")` |

Keys are singular and each appears at most once. One key holds many values:
`(tag a b c)` replaces repeating `+a +b +c`.

A note is a quoted string, so it lives on the item's line and never spans lines.
Several notes go in one key: `(note "first" "second")`. Markdown inside a note
stays literal - a link in a note renders as its raw text, and a `"` inside it is
written `\"`.

A person is a tag value too - `(tag sam)` - until delegation needs more.

A task's kind is a tag, not a state: `bug` when something behaves wrongly,
`fixme` when it works but needs rework. The state tracks progress and the tag
records the kind, so a fixed bug stays findable as a `done` form with `bug`.

```markdown
- @(todo "Reset sequencing is incorrect" (tag bug))
```

On completing a `(recurring ...)` item, advance `(due ...)` to the next
occurrence instead of marking it `done`.

The new `(due ...)` is computed from the old `(due ...)`, not from the day you
finished. Rent stays on the 5th even when paid on the 9th. For an item that
should space itself from the actual completion - a gym visit, a haircut - use
`(recurring from-done 3w)`, which counts from `(completed ...)`.

### Dates and times

Unchanged from the line schema. Parentheses fix the structure, not the values.

- Date `YYYY-MM-DD`, or date-time `YYYY-MM-DDTHH:MM`.
- 24-hour clock, local time, no seconds, no time zone.
- One token, no spaces. `(due 2026-08-19 09:00)` reads as two values and is
  invalid.
- Always zero-padded, so text order is time order.

Tools warn on any `created`, `completed` or `due` value that does not match:

```regex
DATE = \d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])
TIME = T([01]\d|2[0-3]):[0-5]\d
```

The pattern checks shape and ranges only. It accepts impossible dates such as
`2026-02-30`; a date parser rejects those.

### Reference grammar

The line schema's [reference regex](todo_schema.md#reference-regex)
becomes a grammar:

```ebnf
md-item   = { space } "- " marker form            (* markdown list item *)
code-item = comment-marker { any } marker form    (* source file comment *)
marker    = "@(" | "#("                           (* writers emit "@(" *)

form      = head { space } [ id space ] title { space meta } ")"
head      = state
state     = "todo" | "in-progress" | "optional" | "later" | "done" | "obsolete"
id        = "T" digit { digit }
title     = string                                (* non-empty *)
string    = '"' { char - '"' - "\\" | '\\"' | "\\\\" } '"'   (* one line *)

meta      = "(" key space value { space value } ")"
key       = "tag" | "ctx" | "created" | "completed" | "due" | "recurring"
          | "pri" | "note"
value     = symbol | date | string
symbol    = letter { letter | digit | "-" }       (* kebab-case, no "_" *)
date      = YYYY "-" MM "-" DD [ "T" hh ":" mm ]
space     = " " { " " }
```

`marker` is the only place `@` is special. Inside a form `@` is an ordinary
character.

`comment-marker` is whatever starts a comment in that language (`#`, `//`, `--`,
`;`, `/*`). `letter`, `digit`, `char`, `YYYY`, `MM`, `DD`, `hh` and `mm` are the
obvious terminals.

The reader is a character scan: push on `(`, pop on `)`, take a quoted string as
one token, split everything else on whitespace. No lookahead, no backtracking,
and it reports the column where a line breaks instead of just failing to match.

### Conformance

A reader:

- Skips fenced blocks in markdown, and in a source file reads only text after a
  comment marker.
- Rejects a form whose head is not a state, whose title is missing or empty, or
  whose key is unknown. An unknown key is an error, not a silent drop - a typo
  like `(nite "x")` must not lose the note.
- Rejects a repeated key. `(tag a) (tag b)` is an error; write `(tag a b)`.
- Rejects a `(key)` with no value.
- Rejects an uppercase letter in a symbol. `(tag Finance)` is an error, not a
  second tag.
- Accepts one or more spaces between tokens, and a tab as whitespace.
- Accepts any UTF-8 in a title or note. Only `\"` and `\\` are escapes; `\n` is
  the two characters backslash and n, because a string never spans lines.
- Reports every rejection as `path:line:col` and exits non-zero.

A writer, verified on 2026-09-23 across 9,698 converted items with no lossy
round-trip and no unstable rewrite:

- Emits `@(`, never `#(`.
- Emits keys in this order, skipping absent ones: `tag ctx created completed due
  recurring pri note`. A fixed order keeps diffs to the field that changed.
- Emits exactly one space between tokens.
- Leaves every line it did not change byte-identical.

### Parser and libraries

No library. Write the reader.

| Language | Library | Verdict |
|---|---|---|
| Python | [sexpdata](https://pypi.org/project/sexpdata/) | Parses the primary form, including a title holding `(parens)` and `@home`. Rejects `#(` and `@(` with a bare `AssertionError` - no message, no position |
| Python | [sexp_parser](https://github.com/realthunder/sexp_parser) | Object model, aimed at KiCad files |
| Rust | [lexpr](https://lib.rs/crates/lexpr) | R6RS/R7RS plus Emacs Lisp, with `serde-lexpr` for serde |
| Rust | `sexp`, `sise` | Smaller, fewer features |
| OCaml | `sexplib`, [csexp](https://github.com/ocaml-dune/csexp) | Canonical form, for signing |
| Java | [sexp4j](https://github.com/csm/sexp4j) | Rivest-style |

Tested with sexpdata 1.0.2 on 2026-09-23.

Why no library carries its weight here:

- A library parses one whole string as one expression. Slicing a form out of a
  `/* ... */` comment needs a balanced scan first, and that scan is the part you
  would write yourself.
- Stripping a `#` or `@` before the paren is yours too.
- Errors must name file, line and column. sexpdata raises an assertion with an
  empty message.
- The existing Rust implementation of the line schema already hand-writes a
  275-line total parser with no parsing library, and nine files depend on it.

Measured: a reader written from this document alone is 60 lines of Python.
It parses every example here and rejects all ten hostile inputs tried against
it. A library would replace maybe 20 of those lines.

### Flat by design

A form holds only its own metadata. There are no subtasks.

Parts of a big job are peer tasks joined by a tag:

```markdown
- @(todo T7 "Ship the parser" (tag parser))
- @(done T8 "Write the reader" (tag parser) (completed 2026-09-22))
- @(todo T9 "Write tests" (tag parser))
```

Parens could nest, and that was the loudest argument for this schema. The data
says otherwise: across 9,698 task lines in this vault there are 0 nested ones,
and the existing model has no parent or child, only notes. A reader that has to
handle depth costs every tool a recursion it never uses.

### In code comments

A form carries its own start and end, so it embeds in any language's comment:

```python
# @(todo T12 "Drop the shim once v2 lands" (tag backend) (due 2026-10-01))
```

```rust
// @(todo T13 "Free the buffer on the error path" (tag bug))
```

```c
/* @(todo T14 "Debounce the resize handler" (pri B)) */
```

Rules:

- In a source file, only scan text that follows a comment marker. Code is then
  invisible to the extractor, which is what drops false positives to near zero.
- A comment marker inside a string is not a comment:

  ```rust
  let s = "// @(todo T1 \"fake task\")";
  ```

  A reader that does not lex the language must at least count the quotes before
  the marker on that line. An odd count means the marker sits inside a string,
  and the line is skipped.
- A form may continue onto the next line. The reader first strips a leading run
  of `*`, `//`, `#`, `;` and whitespace from each continuation line.
- A quoted title or note never spans lines.
- An unbalanced form is an error, reported as `path:line:col`, and it fails the
  build. It is never skipped silently.

A code todo stays in the code. The extractor indexes it where it lives, so it
moves with the function and dies with the function - there is no second copy in
`todo.md` to drift.

The line schema cannot do this. Its regex anchors on `- ` at the start and `$`
at the end, so a trailing `*/` breaks the match and `# TODO: x` has no bullet.

## States

| State | Meaning |
|---|---|
| `todo` | Not started |
| `in-progress` | Actively being worked |
| `optional` | Nice to have - do it if time permits |
| `later` | Deferred - worth doing, but not now |
| `done` | Completed |
| `obsolete` | No longer relevant - kept for the record |

Life cycle: `todo -> in-progress -> done`. `optional` and `later` items can be
promoted to `todo` or `in-progress`, or dropped (delete the line). Any item can
become `obsolete` instead of being deleted, to keep the record.

## Reporting

When summarizing todos in reports, use the [Emoji Legend](emoji_legend.md):

| State | Emoji |
|---|---|
| `todo`, `in-progress`, `optional`, `later` | ⏳ |
| `done` | ✅ |
| `obsolete` | 🗑️ |
| Past `(due ...)` date | ⚠️ (replaces the state emoji) |

## Example

```markdown
- @(todo T1 "File quarterly GST return" (tag finance) (ctx home) (created 2026-07-01) (due 2026-07-20) (pri A) (note "Collect purchase invoices from the shared drive first"))
- @(todo T2 "Pay rent" (tag finance) (due 2026-08-05) (recurring monthly) (pri A))
- @(in-progress T3 "Create a methodology presentation on wiki documentation" (note "Showcase and demos with real use cases"))
- @(done T4 "Create discord bot with claude" (completed 2026-06-28))
```

## Differences from the line schema

| Aspect | Line schema | This |
|---|---|---|
| Parser | one regex, ~400 chars | 60-line reader |
| Title ambiguity | title must not end like metadata | quoted, no ambiguity |
| Repeated tags | `+a +b` | `(tag a b)` |
| In code comments | not expressible | native |
| Notes | sub-bullets, prose only | `(note "...")`, same line |
| Line length | - | +10 chars median, +22 worst, measured converting 9,698 real items |
| Renders as a bullet | yes | yes |
| Underscores in tags | allowed | invalid |
| Malformed by an agent | rare | unbalanced parens |

## Migration

Nothing reads this format yet. Until that changes, writing an item in it makes
the item invisible to every existing tool.

The work, in order:

1. Reader: 60 lines, scanning `@(`, balanced parens, quoted strings, with
   `path:line:col` errors. A working Python one exists.
2. Parser: replace the 275-line total parser for the line format. Nine files
   depend on it, including the writer and three test suites.
3. Writer: emit forms instead of lines, keeping every untouched line verbatim.
4. Code scanner: a second source that reads comment text in source files.
5. Data: 9,698 task lines convert. Trial-run on 2026-09-23 - all 9,698 were
   converted and reparsed with no failures, growing by 10 characters at the
   median and 22 at the worst. The converter normalises two things: symbols fold
   to lowercase, and `_` becomes `-`. No title needed a `\"` escape.
6. The Python snapshot script keeps its own copy of the line regex and needs the
   same treatment.

Done means all of:

- The tools read and write forms.
- Every task file under the dotfiles repo and every project repo holds forms
  only.
- No line-format item remains anywhere.

At that point `todo_schema.md` is deleted and this document stands alone. Until
then both formats are valid, and a file may hold a mix.

The line format stops being *written* the day the writer emits forms, which is
earlier than the day the last item converts.

## Open questions

None. Every question this document opened is answered in
[Decisions](#decisions); the remaining work is in [Migration](#migration).

## Decisions

| Date | Decision | Why |
|---|---|---|
| 2026-09-23 | `[` and `<` rejected as delimiters | Measured: `grep '[todo'` errors, and `- <todo>` renders as an empty bullet |
| 2026-09-23 | `@(` opens every item, everywhere (q5) | One grep pattern, and a form moves between code and markdown without an edit |
| 2026-09-23 | No parsing library | Slicing, prefix stripping and error positions are custom either way |
| 2026-09-23 | Unbalanced forms fail loudly | Chosen over a silent skip: fix it when it errors |
| 2026-09-23 | Symbols are kebab-case | Paired `_` italicises inside a markdown bullet |
| 2026-09-23 | Keys are singular: `tag`, `note` | One key holds many values, so a plural name adds nothing |
| 2026-09-23 | This schema is canonical, for markdown and code | One format everywhere. The line format becomes legacy and gets no new features |
| 2026-09-23 | Both formats are valid until migration ends | Nothing reads forms yet. The line format is deleted only when every tool and every item has moved |
| 2026-09-23 | No `(who ...)` key - a person is a tag value | Rare enough not to earn a key: 1 person mention in 9,698 task lines |
| 2026-09-23 | No subtasks, the form is flat | Measured: 0 nested task lines in 9,698. Peers plus a shared tag cover it without teaching every tool recursion |
| 2026-09-23 | `(tag ...)` and `(ctx ...)` stay separate | Kept apart deliberately. Measured: across 9,698 task lines `+tag` appears 51 times and `@word` 4 times, so the split is by intent, not by current usage |
| 2026-09-23 | Notes are `(note "...")`, not sub-bullets | One mechanism everywhere, including code comments where sub-bullets do not exist. Cost: long notes make long lines, and markdown inside a note stays literal |
| 2026-09-23 | A comment marker inside a string is not a comment | `let s = "// @(todo ...)"` would otherwise index as a task. Counting quotes before the marker is enough without a full lexer |
| 2026-09-23 | Symbols are lowercase | The corpus holds `+Finance` and `+finance`; case-sensitive symbols would keep them apart forever |
| 2026-09-23 | A form in a fenced block is an example, not work | Otherwise this document's own examples become tasks |
| 2026-09-23 | An unknown or repeated key is an error | A typo like `(nite "x")` must not silently lose the note |
| 2026-09-23 | Writers emit keys in a fixed order | Diffs then show the field that changed, not a reshuffle |
| 2026-09-23 | `recurring` counts from `(due ...)` | Rent stays on the 5th when paid on the 9th. `from-done` opts into the other behaviour |
| 2026-09-23 | State is the head symbol, not a value (q1) | `@(` already says "task", and `@(todo` to `@(done` is the same edit as `TODO:` to `DONE:` today |
