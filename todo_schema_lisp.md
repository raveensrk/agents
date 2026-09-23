# TODO Schema (Lisp)

**Abandoned.** This format was never adopted, and
[Todo Schema (Org)](todo_schema.org) is where the vault is going instead. This
document is kept for the record and takes no new features.

Both markdown formats are allowed during the migration. [Todo Schema](todo_schema.md) -
the line format - still parses, still gets written by existing tools, and takes
no new features. This schema was to replace it, and never did: it holds no real
items anywhere in the vault.

`todo_schema.md` is deleted once the migration finishes, and this schema is then
the only one. See [Migration](#migration).

## Inspiration

[todo.txt format](https://github.com/todotxt/todo.txt/blob/master/README.md) for
the fields, [s-expressions](https://en.wikipedia.org/wiki/S-expression) for the
shape.

The line schema needs a 400-character regex because the title and the metadata
share one flat line. Parentheses separate them, so a reader replaces the regex.

## Format

One form, one syntax, every file type:

```text
%%task(<state> <id> "<title>" (<key> <value>...) ...)
```

It needs no bullet, no comment marker and no container. The same string is a
task in markdown prose, in a list item, in a table cell, in a code comment, in
a YAML file and in a plain `.txt` note.

```markdown
- %%task(todo T1 "Pay rent" (due 2026-08-05))
```

```rust
// %%task(todo T13 "Free the buffer on the error path" (tag bug))
```

```python
# %%task(todo T12 "Drop the shim once v2 lands" (tag backend))
```

One item is one balanced form, and it stays on one line, so `grep`, `sed` and
line diffs keep working. In a source file it may wrap across comment lines,
because a comment is often narrower than the form; see
[In code comments](#in-code-comments).

### Line

- One item per line: `- ` then `@(`, then a single balanced form. `-` is the
  only bullet.
- The head symbol is the state, from [States](#states): `@(todo ...)`,
  `@(done ...)`. There is no `task` head - `@(` already says this is a task.
- A bare symbol after the head is the optional task ID: `T3`. Allocate
  `1 + the highest ever used`, and never reuse a number.
- The title is a double-quoted string, and it is the first quoted token. Write
  `\"` for a quote and `\\` for a backslash. Everything else - parens, colons,
  `@`, URLs - is literal text, so a title can never look like metadata.
- Metadata are nested forms after the title, in any order. Every one is
  optional.
- Text may follow the closing paren. The form ends at its balanced paren, so a
  comment terminator (`*/`, `-->`, `#|`) or a trailing sentence is ignored, not
  an error.
- Everything is case-sensitive. States and keys are lowercase;
  `%%task(TODO ...)` is not a task. An ID is an uppercase `T` then digits: `T3`,
  never `t3`.
- Details go in `(note "...")`, inside the form. Prose near an item carries no
  task data, and no tool reads it.
- Change state by editing the head symbol in place. Drop an item by deleting the
  form (git keeps history).

### Delimiters

`%%task(` opens every item, in every file type. A bare `(` opens every nested
form inside it. There is no synonym: one spelling goes into files, so a single
fixed string finds everything.

```bash
rg -F -- '%%task('
```

A marker's whole job is to be unique, so the choice is measured, not argued.
Counted 2026-09-23 across every repo under `~/repos`, excluding `node_modules`,
build output, `tmp/` and minified files, and rendered through pandoc's
GitHub-flavoured renderer:

| Candidate | Hits today | Renders intact | `grep` as typed | Verdict |
|---|---|---|---|---|
| `%%task(` | 0 | yes | yes | chosen - the only doubled sigil no code can hold |
| `%task(`, `,task(`, `+task(` | 0 | yes | yes | out - single sigils sit next to code: `%` prefixes format directives, `,task(` is one removed space from `f(x,task(y))`, `+task(x)` is a legal unary-plus call |
| `!task(` | 0 | yes | yes | bash history expansion when typed interactively |
| `@(` | 227 | yes | yes | `always @(posedge clk)` in the SystemVerilog notes |
| `_task(` | 646 | yes | yes | common in source |
| `.task(` | 13 | yes | no - `.` matches any character | silent false positives |
| `-task(`, `--task(` | 0 | yes | no - reads as a command-line flag | `rg -task( .` fails |
| `>task(` | 0 | no - becomes a blockquote at line start | yes | out |
| `&task(` | 0 | no - escapes to `&amp;task(` | yes | out |
| `^task(` | 0 | yes | no - anchors to line start | out |
| `*task(` | 0 | yes | no - syntax error | out |
| `<todo ...>` | - | no - parsed as raw HTML | yes | out |
| `[todo ...]` | - | no - becomes a link | no - `[` opens a character class | out |
| `,,task(` | 0 | yes | yes | out - `,,` is unquote in Lisp, a valid reader sequence |
| `;;task(` | 0 | yes | yes | out - a Lisp comment style, and legal C empty statements |
| `::task(` | 0 | yes | yes | out - `::` is the scope resolution operator, 16,851 `::id(` sites. See [q6](#q6---resolved-a-code-inert-marker) |
| `(task ` | 16 | yes | yes | no sigil: collides with live code, see [q7](#q7---resolved-no-bare-s-expression) |
| `(todo ` | 21 | yes | yes | same |

The marker is settled. `%%` is printf-format punctuation and the doubling makes
it the literal percent - this schema forbids forms in strings, so `%%task(`
cannot be code in any C-family language. `::` is the scope resolution operator
in C++, Rust and PHP, so a `ns::task(x)` call is exactly what a `::`-prefixed
marker cannot tell from a task; see [q6](#q6---resolved-a-code-inert-marker).

Note that `(` opens a group in any regex engine, so `rg '%%task('` is a parse
error for this marker and for every candidate above. Search with `rg -F` or
escape it: `rg '%%task\('`. Plain `grep` treats it as a literal.

### Symbols are lowercase kebab-case

Markdown italicizes paired `_` inside a list item, so a bare symbol like
`raveen_kumar_xyz` renders as `raveen*kumar*xyz`. Symbols use kebab-case
instead: `raveenkumar-xyz`, `in-progress`. An underscore is invalid in a symbol.

Symbols are lowercase. `Finance` and `finance` would otherwise be two tags, and
the existing corpus already holds both spellings of exactly that word.

The line schema escapes this because its tags sit behind `+` and `@`, which most
renderers leave alone. Measured through pandoc: a `%%task(` form survives intact
in prose, list items, table cells and blockquotes.

### Fenced code blocks

A form inside a ``` or ~~~ fence is an example of the format, not work. Readers
skip fenced blocks, which is what keeps this document's own examples out of your
task list.

A form in a source file is the exception: code is where real work items live, so
a comment inside a fenced block in markdown is still an example, while the same
comment in a `.rs` file is a task.

### Checklists

`- [ ]` and `- [x]` lines are checklists - steps in a procedure, audit or test
run that you tick each time - not todo items. A todo is a `%%task(` form, so
the two never collide, wherever either one sits.

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
- %%task(todo "Reset sequencing is incorrect" (tag bug))
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
item      = { any } marker form { any }           (* anywhere, in any file *)
marker    = "%%task("

form      = head { space } [ id space ] title { space meta } ")"
head      = state
state     = "todo" | "in-progress" | "optional" | "later" | "done" | "obsolete"
id        = "T" digit { digit }
title     = string                                (* non-empty *)
string    = '"' { char - '"' - "\\" | '\\"' | "\\\\" } '"'   (* one line *)

meta      = "(" key space value { space value } ")"
key       = "tag" | "ctx" | "created" | "completed" | "due" | "recurring"
          | "pri" | "note"
value     = symbol | date | priority | recurrence | string
priority  = "A" | "B" | "C"
recurrence= [ "from-done" space ] ( "daily" | "weekly" | "monthly" | "yearly"
          | digit { digit } ( "d" | "w" | "m" | "y" ) )
symbol    = letter { letter | digit | "-" }       (* kebab-case, no "_" *)
date      = YYYY "-" MM "-" DD [ "T" hh ":" mm ]
space     = ( " " | "\t" ) { " " | "\t" }
```

`any` is any text, so a form is found by scanning for the marker and reading
the balanced form that follows. Nothing before or after it is inspected, which
is why no file type needs its own rule. Inside a form `:` and `@` are ordinary
characters.

`letter`, `digit`, `char`, `YYYY`, `MM`, `DD`, `hh` and `mm` are the obvious
terminals. `recurrence` is a rate or a period - a count starts with a digit, so
`symbol` cannot hold it - and `priority` is uppercase by design, because
`(pri A)` is a value, not a symbol.

The reader is a character scan: push on `(`, pop on `)`, take a quoted string as
one token, split everything else on whitespace. No lookahead, no backtracking,
and it reports the column where a line breaks instead of just failing to match.

### Conformance

A reader:

- Scans every line of every file for the marker, with no knowledge of the
  file's language. In markdown it skips fenced blocks.
- Rejects a form whose head is not a state, whose title is missing or empty, or
  whose key is unknown. A form inside a string literal fails here, because its
  quotes arrive escaped. An unknown key is an error, not a silent drop - a typo
  like `(nite "x")` must not lose the note.
- Rejects a repeated key. `(tag a) (tag b)` is an error; write `(tag a b)`.
- Rejects a `(key)` with no value.
- Rejects an uppercase letter in a symbol. `(tag Finance)` is an error, not a
  second tag.
- Accepts one or more spaces between tokens, and a tab as whitespace.
- Accepts any UTF-8 in a title or note. Only `\"` and `\\` are escapes; any
  other backslash is an error, reported as `path:line:col`. A string never
  spans lines, so no other escape exists.
- Reports every rejection as `path:line:col` and exits non-zero.

A writer, verified on 2026-09-23 across 9,698 converted items with no lossy
round-trip and no unstable rewrite:

- Emits `%%task(`. There is no synonym to choose between.
- Emits keys in this order, skipping absent ones: `tag ctx created completed due
  recurring pri note`. A fixed order keeps diffs to the field that changed.
- Emits exactly one space between tokens.
- Leaves every line it did not change byte-identical.

### Parser and libraries

No library. Write the reader.

| Language | Library | Verdict |
|---|---|---|
| Python | [sexpdata](https://pypi.org/project/sexpdata/) | Parses the primary form, including a title holding `(parens)` and `@home`. Rejects a `%%task(` prefix with a bare `AssertionError` - no message, no position |
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
- %%task(todo T7 "Ship the parser" (tag parser))
- %%task(done T8 "Write the reader" (tag parser) (completed 2026-09-22))
- %%task(todo T9 "Write tests" (tag parser))
```

Parens could nest, and that was the loudest argument for this schema. The data
says otherwise: across 9,698 task lines in this vault there are 0 nested ones,
and the existing model has no parent or child, only notes. A reader that has to
handle depth costs every tool a recursion it never uses.

### Verified across file types

The claim that one scanner finds every task in every file type is tested, not
asserted. Run 2026-09-24 over a fixture of 17 files, 22 forms:

| Files | Comment style | Found |
|---|---|---|
| `.md` - prose, list item, table cell, blockquote | none | 4 of 4 |
| `.py` `.sh` `.toml` `.yaml` | `#` | 4 of 4 |
| `.rs` `.js` `.c` `.css` | `//` and `/* */` | 5 of 5 |
| `.html` | `<!-- -->` | 1 of 1 |
| `.sql` `.lua` | `--` | 2 of 2 |
| `.tex` `.vim` `.txt` | `%`, `"`, none | 3 of 3 |
| `.json` | string value | 1 of 1 |
| `.sv` | `//` | 1 of 1 |

Also verified in that run:

- A form wrapping two lines inside a `/* ... */` block parses.
- A form with a trailing `*/` parses; the text after the balanced paren is
  ignored.
- A title holding `(parens)` and a `:colon:` parses.
- The 2 `always @(posedge clk)` lines in the `.sv` fixture produce nothing.
- The form inside a fenced block in the `.md` fixture is skipped.

The scanner used no language knowledge beyond skipping fenced blocks in
markdown.

### In code comments

A form carries its own start and end, so it embeds in any language's comment:

```python
# %%task(todo T12 "Drop the shim once v2 lands" (tag backend) (due 2026-10-01))
```

```rust
// %%task(todo T13 "Free the buffer on the error path" (tag bug))
```

```c
/* %%task(todo T14 "Debounce the resize handler" (pri B)) */
```

Rules:

- No comment marker is required and none is stripped. The reader scans raw text
  for `%%task(` in any file, so one algorithm covers every language.
- A form inside a string literal is not allowed. The host language escapes the
  inner quotes, so the title never opens:

  ```rust
  let s = "%%task(todo T1 \"not a task\")";
  ```

  On disk that line holds `\"`, not `"`. The reader finds no title and reports
  `path:line:col`. Move the form into a comment, which is where it belongs.
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
This schema anchors on nothing: the marker and the balanced parens carry both
ends with them.

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
- %%task(todo T1 "File quarterly GST return" (tag finance) (ctx home) (created 2026-07-01) (due 2026-07-20) (pri A) (note "Collect purchase invoices from the shared drive first"))
- %%task(todo T2 "Pay rent" (tag finance) (due 2026-08-05) (recurring monthly) (pri A))
- %%task(in-progress T3 "Create a methodology presentation on wiki documentation" (note "Showcase and demos with real use cases"))
- %%task(done T4 "Create discord bot with claude" (completed 2026-06-28))
```

## Differences from the line schema

| Aspect | Line schema | This |
|---|---|---|
| Parser | one regex, ~400 chars | 60-line reader |
| Title ambiguity | title must not end like metadata | quoted, no ambiguity |
| Repeated tags | `+a +b` | `(tag a b)` |
| In code comments | not expressible | native, and identical to the markdown form |
| Notes | sub-bullets, prose only | `(note "...")`, same line |
| Line length | - | +15 chars median, +27 worst: measured at +10 and +22 converting 9,698 real items with a 2-character marker, plus 5 for `%%task(` |
| Renders as a bullet | yes | yes |
| Underscores in tags | allowed | invalid |
| Malformed by an agent | rare | unbalanced parens |

## Migration

Nothing reads this format yet. Until that changes, writing an item in it makes
the item invisible to every existing tool.

The work, in order:

1. Reader: 60 lines, scanning `%%task(`, balanced parens, quoted strings, with
   `path:line:col` errors. A working Python one exists.
2. Parser: replace the 275-line total parser for the line format. Nine files
   depend on it, including the writer and three test suites.
3. Writer: emit forms instead of lines, keeping every untouched line verbatim.
4. Code scanner: a second source that reads comment text in source files.
5. Data: 9,901 task lines across 3,604 markdown files convert. Trial-run on
   2026-09-23 over a 9,698-line subset - all converted and reparsed with no
   failures, growing by 10 characters at the median and 22 at the worst. That
   trial used a 2-character marker; `%%task(` adds 5 more to every item. The
   converter normalises two things: symbols fold to lowercase, and `_` becomes
   `-`. No title needed a `\"` escape.

   Two traps the converter must handle: 27 of those lines sit inside fenced
   blocks and are format examples, not work; and some roots reach the same file
   twice through a symlink, so a file must be converted once however many paths
   find it.
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

## Marker questions

Two questions about the marker were open; both are resolved, and the reasoning
and measurements stay below for the record. Everything else this document
raised is answered in [Decisions](#decisions).

### q6 - resolved: a code-inert marker

`::` is the scope resolution operator in C++, Rust and PHP, so `ns::task(x)` is
legitimate code. Measured 2026-09-24 across `~/repos`, excluding `node_modules`
and build output:

| Measurement | Count |
|---|---|
| `::<identifier>(` in `.cpp`, `.hpp`, `.h`, `.cc`, `.rs` | 16,851 |
| Of those, an identifier named `task` | 0 |
| Leading `::` at global scope | 1,450 |

The shape is everywhere and the name happens to be free - but the collision is
one function name away: `Main_Quest` is a Rust task manager, which is where
`crate::task(...)` would plausibly first appear. Measurement cannot retire the
risk, because the unknown-head rule cannot tell a typo from a call when the call
is legal. Either the marker or the conformance rule had to move; the marker
moved.

`%%task(` is chosen because `%%` cannot be code: no C-family language has a `%%`
operator, and the one place `%%` means anything is inside printf-style format
strings, which this schema already forbids (a form must not sit in a string
literal). Compilers have nothing to collide with, so an unknown head stays a
loud `path:line:col` error, consistent with unbalanced forms and unknown keys.

Rejected:

1. Keep `::task(` and downgrade an unknown head from an error to a skip. A form
   whose head is not a state is code, not a task. Cost: a typo such as
   `%%task(todoo "x")` then disappears silently, exactly the failure the
   fail-loudly rule exists to prevent.
2. Keep `::task(` and keep erroring on an unknown head. Cost: one ordinary C++
   call would fail the build - the combination this section's own measurement
   rules out.

### q7 - resolved: no bare s-expression

Proposed shape: `(task (todo (data)))`, a pure s-expression with no sigil, which
an off-the-shelf lisp reader could parse.

Measured 2026-09-24:

| Marker | Hits today |
|---|---|
| `(task ` | 16 |
| `(todo ` | 21 |
| `%%task(` | 0 |

The 16 hits are live code, for example `tasks.filter(task => {` and
`_ssh_prefix_for_task(task or {})`.

Two separable questions sit inside the proposal; both are rejected.

- **Dropping the sigil.** It buys direct parsing by `sexpdata` or `lexpr`. The
  measured saving is about 20 lines of a 60-line reader, because slicing a
  balanced form out of mixed text stays hand-written either way. It costs 16
  collisions today in code that is still being written, and it collides with
  Lisp-family code by construction - native parentheses are the exact shape this
  format gives up. The sigil is what keeps a scan free of false positives.
- **Nesting the state.** `(task (todo (data)))` puts the metadata one level
  below the state. That reads as "the data belongs to the state", but
  `(due 2026-08-05)` belongs to the task, not to its todo-ness. It also adds a
  level to every reader and 2 characters to every item, against a measured 0
  nested items in 9,698 - see the [flat-by-design](#flat-by-design) decision.

The sigil and the flat form are the specification, and they stay.

## Decisions

| Date | Decision | Why |
|---|---|---|
| 2026-09-23 | `[` and `<` rejected as delimiters | Measured: `grep '[todo'` errors, and `- <todo>` renders as an empty bullet |
| 2026-09-23 | A single marker opens every item, everywhere (q5) | One grep pattern, and a form moves between code and markdown without an edit |
| 2026-09-24 | `::task(` tried, then rejected - `::` is the scope resolution operator | Measured: `@(` occurs 227 times in 78 hand-written markdown files, all `always @(posedge clk)`; `::task(` measures 0. But the shape is 16,851 `::id(` sites wide, so a free name is one `fn task` from a collision. See [q6](#q6---resolved-a-code-inert-marker) |
| 2026-09-24 | No bullet, no container, no comment marker | The marker is unique enough to stand alone, so prose, list items, table cells, code comments and plain text all take the same string |
| 2026-09-24 | The reader scans raw text in every file | Dropping language awareness removes the comment-marker rule and the quote-counting rule, and leaves one algorithm |
| 2026-09-24 | One scanner, verified on 17 file types | 22 of 22 forms found, 0 false positives, including a 2-line wrap, a trailing `*/`, a title holding parens, and a `.sv` file whose `always @(posedge clk)` lines matched nothing |
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
| 2026-09-24 | A form inside a string literal is not allowed | The host language escapes the inner quotes, so the title never opens and the reader errors with `path:line:col`. Chosen over unescaping (rewards a bad habit) and over skipping (needs the per-language quote counting this schema deleted) |
| 2026-09-23 | Symbols are lowercase | The corpus holds `+Finance` and `+finance`; case-sensitive symbols would keep them apart forever |
| 2026-09-23 | A form in a fenced block is an example, not work | Otherwise this document's own examples become tasks |
| 2026-09-23 | An unknown or repeated key is an error | A typo like `(nite "x")` must not silently lose the note |
| 2026-09-23 | Writers emit keys in a fixed order | Diffs then show the field that changed, not a reshuffle |
| 2026-09-23 | `recurring` counts from `(due ...)` | Rent stays on the 5th when paid on the 9th. `from-done` opts into the other behaviour |
| 2026-09-23 | State is the head symbol, not a value (q1) | The marker already says "task", and `%%task(todo` to `%%task(done` is the same edit as `TODO:` to `DONE:` today |
| 2026-09-23 | The marker is `%%task(` (q6) | `%%` is printf-format punctuation, not an operator, and this schema forbids forms in strings - so no compiling code can contain `%%task(`. The unknown-head rule stays a loud error, and the collision question closes for good |
| 2026-09-23 | No bare s-expression; the sigil and the flat form stay (q7) | `(task ` already occurs 16 times in live code, and a sigil-less form collides with Lisp-family code by construction. Nesting the state contradicts flat-by-design: 0 nested items in 9,698 |
| 2026-09-23 | Grammar errata: `recurrence` and `priority` are productions, and tabs are space | `2w` and `3w` start with a digit, so `symbol` never matched them; `(pri A)` is uppercase where symbols must be lowercase; the EBNF `space` omitted the tab the conformance accepts |
| 2026-09-23 | A backslash before anything but `"` or `\` is an error | The reader already raised a bad escape; the doc called `\n` two literal characters. One fail-loudly rule for every malformed form, matching unbalanced parens and unknown keys |
