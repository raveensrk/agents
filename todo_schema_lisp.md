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
share one flat line. A real s-expression separates them, so a Lisp reader
replaces the regex.

## Format

One form, one syntax, every file type:

```text
(task <state> <title> (<key> <value>...)...)
```

The state and the title are fixed position. Everything after them is metadata,
in any order, and every one is optional.

```markdown
- (task "todo" "Pay rent" ("due" "2026-08-05"))
```

```rust
// (task "todo" "Free the buffer on the error path" ("tag" "bug"))
```

```python
# (task "todo" "Drop the shim once v2 lands" ("tag" "backend"))
```

One item is one balanced form, so `grep`, `sed` and line diffs keep working. In
markdown it stays on one line; in a source file it may wrap across comment
lines, because a comment is often narrower than the form; see
[In code comments](#in-code-comments).

### Line

- One item is one balanced form opened by `(task "`. It may appear anywhere on
  a line: on its own, after a list bullet, inside a sentence, or after any
  language's comment marker.
- The state is the first value, from [States](#states): `"todo"`, `"done"`.
- The title is the second value, a double-quoted string. Write `\"` for a quote
  and `\\` for a backslash.
- Everything after the title is a metadata form, in any order. Every one is
  optional. The task ID is one of them: `("id" "T3")`. Allocation rules live in
  [Task Protocol](task.md) - never reuse a number.
- Text may follow the closing paren. The form ends at its balanced paren, so a
  comment terminator (`*/`, `-->`, `#|`) or a trailing sentence is ignored, not
  an error.
- Everything is case-sensitive. States and keys are lowercase, and so are tag
  and context values; an uppercase state is not a task. An ID is an uppercase
  `T` then digits: `"T3"`, never `"t3"`. A priority is `A`, `B` or `C`.
- Details go in `("note" "...")`, inside the form. Prose near an item carries no
  task data, and no tool reads it.
- Change state by editing the first value in place. Drop an item by deleting the
  form (git keeps history).

### Every value is a string

The only symbol in a form is the head `task`. State, title, keys and values are
all strings. This is what makes the form conform to Common Lisp:

- Common Lisp upcases symbols on read, so a bare `todo` reads as `TODO` and the
  lowercase rule cannot survive. A string keeps its case.
- A bare `2026-08-19T09:00` is a reader error: `:` is the package marker, so the
  reader looks for a package named `2026-08-19T09`. Inside a string the colon is
  ordinary text.
- A string round-trips byte-for-byte, so a Lisp reader and writer lose nothing.

The head is the one exception. It is a marker, and its case-fold is harmless: a
reader matches `task` case-insensitively.

### Delimiters

`(task "` opens every item, in every file type: the head `task`, one or more
spaces, then the state's opening double quote. There is no synonym, so a single
fixed string finds everything.

```bash
rg -F -- '(task "'
```

The quote is not decoration. It is the first character of the state, which is
always a string, so it costs nothing and it removes every collision. Counted
2026-09-23 across every repo under `~/repos`, excluding `node_modules`, build
output, `tmp/`, dependency trees and minified files:

| Candidate | Hits today | Verdict |
|---|---|---|
| `(task "` | 0 | chosen - the head plus the state's opening quote |
| `(task ` | 9 | out - live code: `tasks.filter(task => {`, `_ssh_prefix_for_task(task or {})`, `(task phases)` in a SystemVerilog comment |
| `(todo ` | 5 | out - same |
| `::task(` | 0 | out - `::` is the scope resolution operator; the shape is 16,851 `::id(` sites wide |
| `%%task(` | 0 | out - not a real s-expression: the head sits outside the parens |
| `@(` | 351 | out - `always @(posedge clk)` |
| `_task(` | 321 | out - common in source |
| `>task(`, `&task(`, `^task(`, `*task(`, `.task(` | 0 | out - broken or ambiguous in a shell, a regex or a markdown renderer |

Note that `(` opens a group in any regex engine, so `rg '(task "'` is a parse
error. Search with `rg -F` or escape it. Plain `grep` treats it as a literal.

### Values are lowercase kebab-case

Markdown italicizes paired `_` inside a list item, so a tag value like
`raveen_kumar_xyz` renders as `raveen*kumar*xyz`. Values use kebab-case instead:
`raveenkumar-xyz`, `in-progress`. An underscore is invalid in a value.

Tag and context values are lowercase. `Finance` and `finance` would otherwise be
two tags, and the existing corpus already holds both spellings of exactly that
word. Dates, priorities and IDs have their own shapes and keep their case.

The line schema escapes this because its tags sit behind `+` and `@`, which most
renderers leave alone. Measured through pandoc: a `(task "` form survives intact
in prose and list items.

### Checklists

`- [ ]` and `- [x]` lines are checklists - steps in a procedure, audit or test
run that you tick each time - not todo items. A todo is a `(task "` form, so the
two never collide, wherever either one sits.

### Metadata forms

| Form | Contents | Example |
|---|---|---|
| `("id" ...)` | the task ID | `("id" "T3")` |
| `("tag" ...)` | one or more values - project or kind | `("tag" "raveenkumar-xyz" "bug")` |
| `("ctx" ...)` | one or more context values | `("ctx" "backend" "home")` |
| `("created" ...)` | date or date-time | `("created" "2026-09-15")` |
| `("completed" ...)` | date or date-time | `("completed" "2026-09-19")` |
| `("due" ...)` | date or date-time | `("due" "2026-08-19T09:00")` |
| `("recurring" ...)` | `daily`, `weekly`, `monthly`, `yearly`, or a count plus `d`, `w`, `m` or `y`. An optional leading `from-done` counts from `("completed" ...)` instead of from `("due" ...)` | `("recurring" "2w")`, `("recurring" "from-done" "3w")` |
| `("pri" ...)` | `A`, `B` or `C` | `("pri" "A")` |
| `("note" ...)` | one or more strings, each a detail | `("note" "only leaks on the retry path")` |

Keys are singular and each appears at most once. One key holds many values:
`("tag" "a" "b" "c")` replaces repeating `+a +b +c`.

A note is a string, so it lives on the item's line and never spans lines.
Several notes go in one key: `("note" "first" "second")`. Markdown inside a note
stays literal - a link in a note renders as its raw text, and a `"` inside it is
written `\"`.

A person is a tag value too - `("tag" "sam")` - until delegation needs more.

A task's kind is a tag, not a state: `"bug"` when something behaves wrongly,
`"fixme"` when it works but needs rework. The state tracks progress and the tag
records the kind, so a fixed bug stays findable as a `"done"` form with `"bug"`.

```markdown
- (task "todo" "Reset sequencing is incorrect" ("tag" "bug"))
```

On completing a `("recurring" ...)` item, advance `("due" ...)` to the next
occurrence instead of marking it `"done"`.

The new `("due" ...)` is computed from the old `("due" ...)`, not from the day
you finished. Rent stays on the 5th even when paid on the 9th. For an item that
should space itself from the actual completion - a gym visit, a haircut - use
`("recurring" "from-done" "3w")`, which counts from `("completed" ...)`.

### Dates and times

Unchanged from the line schema. The string fixes the token, not the values.

- Date `YYYY-MM-DD`, or date-time `YYYY-MM-DDTHH:MM`.
- 24-hour clock, local time, no seconds, no time zone.
- One token, no spaces. `("due" "2026-08-19 09:00")` is two values and is
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
item      = { any } marker form { any }           (* after the context pass *)
marker    = "(task" space '"'

form      = "(" "task" space state space title { space meta } ")"
state     = string
title     = string                                (* non-empty *)
string    = '"' { char - '"' - "\\" | '\\"' | "\\\\" } '"'   (* one line *)

meta      = "(" key space value { space value } ")"
key       = "id" | "tag" | "ctx" | "created" | "completed" | "due"
          | "recurring" | "pri" | "note"
value     = string
space     = ( " " | "\t" ) { " " | "\t" }
```

`any` is any text, so a form is found by scanning for the marker and reading the
balanced form that follows. Nothing before or after it is inspected; a small
context pass decides whether a line is captured, and that pass is the whole of
[Where the parser captures](#where-the-parser-captures). Inside a form `:` and
`@` are ordinary characters, because they sit in strings.

`char`, `YYYY`, `MM`, `DD`, `hh` and `mm` are the obvious terminals. The state,
key, id, tag, ctx, pri, date and recurrence shapes are validated by the reader,
not by the grammar.

The reader is a Lisp reader plus a validation pass. The scan around it is a
character walk: find `(task`, skip whitespace, require `"`, then push on `(` and
pop on `)`, taking a quoted string as one token. No lookahead, no backtracking,
and it reports the column where a line breaks instead of just failing to match.

### Conformance

A reader:

- Scans every line of every file for the marker, after the context pass: skip
  markdown fenced blocks, table rows and blockquotes; in a source file, accept
  the marker only inside a comment.
- Rejects a form whose head is not `task`, whose state is not in
  [States](#states), whose title is missing or empty, or whose key is unknown.
  An unknown key is an error, not a silent drop - a typo like `("nite" "x")`
  must not lose the note.
- Rejects a repeated key. `("tag" "a") ("tag" "b")` is an error; write
  `("tag" "a" "b")`.
- Rejects a `(key)` with no value.
- Rejects a value that does not match its key: a `tag` or `ctx` value must be
  lowercase kebab-case (`("tag" "Finance")` is an error, not a second tag),
  `pri` must be `A`, `B` or `C`, a date must match the date pattern, and
  `recurring` must be a rate or a period. A `note` is free text.
- Rejects an ID that is not `T` then digits.
- Accepts one or more spaces between tokens, and a tab as whitespace.
- Accepts any UTF-8 in a title or note. Only `\"` and `\\` are escapes; any
  other backslash is an error, reported as `path:line:col`. A string never
  spans lines, so no other escape exists.
- Reports every rejection as `path:line:col`; a tool exits non-zero. The reader
  raises the condition, and the file reader prefixes the path, line and column.

A writer:

- Emits `(task "`. There is no synonym to choose between.
- Emits keys in this order, skipping absent ones: `id tag ctx created completed
  due recurring pri note`. A fixed order keeps diffs to the field that changed.
- Emits exactly one space between tokens.
- Leaves every line it did not change byte-identical.

### Parser and libraries

The form is a single s-expression, so a Lisp reader parses the form itself. What
stays hand-written is the scan around it and the errors.

| Language | Library | Verdict |
|---|---|---|
| Python | [sexpdata](https://pypi.org/project/sexpdata/) | Parses the whole form. No positions on error, so the scan still reports `path:line:col` itself |
| Python | [sexp_parser](https://github.com/realthunder/sexp_parser) | Object model, aimed at KiCad files |
| Rust | [lexpr](https://lib.rs/crates/lexpr) | R6RS/R7RS plus Emacs Lisp, with `serde-lexpr` for serde |
| Rust | `sexp`, `sise` | Smaller, fewer features |
| OCaml | `sexplib`, [csexp](https://github.com/ocaml-dune/csexp) | Canonical form, for signing |
| Java | [sexp4j](https://github.com/csm/sexp4j) | Rivest-style |

Why a library is optional rather than required:

- Slicing a balanced form out of mixed text is yours either way. The library
  parses the form; it does not find it.
- Errors must name file, line and column. Most libraries raise a bare parse
  error with no position.
- The existing Rust implementation of the line schema already hand-writes a
  275-line total parser with no parsing library, and nine files depend on it.

### Flat by design

A form holds only its own metadata. There are no subtasks.

Parts of a big job are peer tasks joined by a tag:

```markdown
- (task "todo" "Ship the parser" ("id" "T7") ("tag" "parser"))
- (task "done" "Write the reader" ("id" "T8") ("tag" "parser") ("completed" "2026-09-22"))
- (task "todo" "Write tests" ("id" "T9") ("tag" "parser"))
```

Parens could nest, and that was the loudest argument for this schema. The data
says otherwise: across 9,698 task lines in this vault there are 0 nested ones,
and the existing model has no parent or child, only notes. A reader that has to
handle depth costs every tool a recursion it never uses.

### In code comments

A form carries its own start and end, so it embeds in any language's comment:

```python
# (task "todo" "Drop the shim once v2 lands" ("id" "T12") ("tag" "backend") ("due" "2026-10-01"))
```

```rust
// (task "todo" "Free the buffer on the error path" ("id" "T13") ("tag" "bug"))
```

```c
/* (task "todo" "Debounce the resize handler" ("id" "T14") ("pri" "B")) */
```

Rules:

- In a source file the form must sit in a comment. The scanner uses the
  language's comment syntax; it does not count quotes, because a string literal
  escapes the marker's opening quote and never matches.
- A form inside a string literal is not allowed. The host language escapes the
  inner quotes, so the marker never opens:

  ```rust
  let s = "(task \"todo\" \"not a task\")";
  ```

  On disk that line holds `\"`, not `"`, so the marker never opens. The scanner
  finds nothing. Move the form into a comment, which is where it belongs.
- A form may continue onto the next line. The reader strips a leading run of
  comment punctuation (`*`, `//`, `#`, `;`, `--`, `%`, `<!--`, `"`) and
  whitespace from each continuation line.
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

## Where the parser captures

The scanner applies a small, fixed set of context rules, then finds `(task "`
followed by a balanced form:

- Markdown prose and list items.
- A comment in a source file: `#`, `//`, `/* */`, `--`, `<!-- -->`, `%`, `;`,
  `"`.
- Plain `.txt`, YAML (plain or single-quoted scalars), TOML (literal strings).

Text before and after the form is ignored, so a bullet, a comment marker or a
trailing sentence changes nothing. Verified 2026-09-23 on two fixtures: a board
whose table row, blockquote and fenced example are skipped, and a `.js` file
where a one-line comment and a two-line block comment are captured while a form
in a string literal and a bare form in code are not.

## Where the parser does not capture

- **Markdown table cells.** A form in a cell is not work. `| (task "todo" "x") |`
  is an example, and a table is a natural place to compare forms side by side.
- **Markdown blockquotes.** A form in a `>` line is quoted text, not work.
  `> (task "todo" "x")` is an example.
- **Fenced code blocks.** A form inside a ``` or ~~~ fence is an example of the
  format, not work. This is what keeps this document's own examples out of a
  task list.
- **Code that is not a comment.** In a source file the form is captured only
  inside a comment. A string literal escapes its quotes, so `(task "` becomes
  `(task \"` and the marker does not match; a bare form in code is not a task.
- **A bare form in a `.lisp` file.** `.lisp` is code like any other, so the form
  must sit in a `;` comment. A bare `(task "todo" "x")` is a function call,
  not a task.
- **JSON.** A JSON string must escape `"` and JSON has no comments, so a valid
  form cannot appear in a `.json` file at all.
- **`(task ` without the opening quote.** The marker requires the quote. This is
  why `_ssh_prefix_for_task(task or {})`, `tasks.filter(task => {` and
  `// EXECUTING: (task phases)` produce nothing.
- **Checklists.** `- [ ]` and `- [x]` lines are a different construct.
- **An identifier that merely contains `task`.** `taskHead`, `subtask` and
  `task(x)` have no `(task "` and match nothing.

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
promoted to `todo` or `in-progress`, or dropped (delete the form). Any item can
become `obsolete` instead of being deleted, to keep the record.

## Reporting

When summarizing todos in reports, use the [Emoji Legend](emoji_legend.md):

| State | Emoji |
|---|---|
| `todo`, `in-progress`, `optional`, `later` | ⏳ |
| `done` | ✅ |
| `obsolete` | 🗑️ |
| Past `("due" ...)` date | ⚠️ (replaces the state emoji) |

## Example

```markdown
- (task "todo" "File quarterly GST return" ("id" "T1") ("tag" "finance") ("ctx" "home") ("created" "2026-07-01") ("due" "2026-07-20") ("pri" "A") ("note" "Collect purchase invoices from the shared drive first"))
- (task "todo" "Pay rent" ("id" "T2") ("tag" "finance") ("due" "2026-08-05") ("recurring" "monthly") ("pri" "A"))
- (task "in-progress" "Create a methodology presentation on wiki documentation" ("id" "T3") ("note" "Showcase and demos with real use cases"))
- (task "done" "Create discord bot with claude" ("id" "T4") ("completed" "2026-06-28"))
```

## Differences from the line schema

| Aspect | Line schema | This |
|---|---|---|
| Parser | one regex, ~400 chars | a Lisp reader plus validation |
| Title ambiguity | title must not end like metadata | quoted, no ambiguity |
| Repeated tags | `+a +b` | `("tag" "a" "b")` |
| In code comments | not expressible | native, and identical to the markdown form |
| Notes | sub-bullets, prose only | `("note" "...")`, same line |
| Line length | - | +15 chars median, +27 worst, measured converting 9,698 real items |
| Renders as a bullet | yes | yes |
| Underscores in tags | allowed | invalid |
| Malformed by an agent | rare | unbalanced parens |

## Migration

Nothing reads this format yet. Until that changes, writing an item in it makes
the item invisible to every existing tool.

The work, in order:

1. Reader: a Lisp reader plus a balanced scan, with `path:line:col` errors.
2. Parser: replace the 275-line total parser for the line format. Nine files
   depend on it, including the writer and three test suites.
3. Writer: emit forms instead of lines, keeping every untouched line verbatim.
4. Code scanner: a second source that reads comment text in source files.
5. Data: 9,901 task lines across 3,604 markdown files convert. Trial-run on
   2026-09-23 over a 9,698-line subset - all converted and reparsed with no
   failures. The converter normalises two things: values fold to lowercase, and
   `_` becomes `-`. No title needed a `\"` escape.

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

## Marker history

`(task "` is the fourth marker tried. The history is why.

| Marker | Outcome | Why |
|---|---|---|
| `::task(` | rejected | `::` is the scope resolution operator in C++, Rust and PHP, so `ns::task(x)` is legitimate code. Measured 16,851 `::id(` sites; the name `task` is one `fn task` from a collision |
| `%%task(` | rejected | `%%` cannot be code, so it is collision-free - but `%%task(...)` is not a real s-expression: the head sits outside the parens, so a Lisp reader sees a symbol followed by a list, two datum |
| `(task ` | rejected | A real s-expression, but `(task ` occurs 9 times in live code (`tasks.filter(task => {`, `_ssh_prefix_for_task(task or {})`, `(task phases)`). One of them scans as an unbalanced form |
| `(task "` | chosen | The head plus the state's opening quote. The quote is free, because the state is always a string, and it removes every collision: 0 hits |

## Decisions

| Date | Decision | Why |
|---|---|---|
| 2026-09-23 | The form is a single s-expression: `(task <state> <title> <meta>...)` | A Lisp reader parses it directly. `%%task(...)` put the head outside the parens, so a reader saw two datum |
| 2026-09-23 | The marker is `(task "` | The head plus the state's opening quote. The quote is free (the state is always a string) and removes every collision: `(task ` = 9 hits, `(task "` = 0 |
| 2026-09-23 | Every value is a string; only the head is a symbol | Common Lisp upcases symbols and treats `:` as a package marker, so a bare `todo` and a bare `2026-08-19T09:00` cannot survive a Lisp reader |
| 2026-09-23 | State and title are fixed position; everything else is metadata | Removes the positional-ID special case. The ID is `("id" "T3")`, so a title can never be read as an ID |
| 2026-09-23 | `[` and `<` rejected as delimiters | Measured: `grep '[todo'` errors, and `- <todo>` renders as an empty bullet |
| 2026-09-23 | A single marker opens every item, everywhere | One grep pattern, and a form moves between code and markdown without an edit |
| 2026-09-24 | `::task(` tried, then rejected | `::` is the scope resolution operator. Measured: `@(` occurs 351 times, `::task(` measures 0. But the shape is 16,851 `::id(` sites wide, so a free name is one `fn task` from a collision |
| 2026-09-24 | No bullet, no container, no comment marker | The marker is unique enough to stand alone, so prose, list items, code comments and plain text all take the same string |
| 2026-09-24 | The reader applies context rules, then scans for the marker | Markdown tables, blockquotes and fenced blocks are examples, not work; in a source file only a comment is captured. The form string stays identical everywhere |
| 2026-09-23 | Markdown table cells and blockquotes are not captured | A table or a quote is where examples live, so the document can compare forms without creating tasks |
| 2026-09-23 | In a source file, only comments are captured | Code and string literals are not tasks. The marker's opening quote already excludes string literals |
| 2026-09-23 | One scanner, verified on two fixtures | A board with a table row, a blockquote and a fenced example skipped; a `.js` file with a one-line comment and a two-line block comment captured, and a string literal and bare code ignored |
| 2026-09-23 | No parsing library is required | The form is a single s-expression, so a library can parse it. Slicing and error positions are custom either way |
| 2026-09-23 | Unbalanced forms fail loudly | Chosen over a silent skip: fix it when it errors |
| 2026-09-23 | Values are kebab-case | Paired `_` italicises inside a markdown bullet |
| 2026-09-23 | Keys are singular: `tag`, `note` | One key holds many values, so a plural name adds nothing |
| 2026-09-23 | This schema is canonical, for markdown and code | One format everywhere. The line format becomes legacy and gets no new features |
| 2026-09-23 | Both formats are valid until migration ends | Nothing reads forms yet. The line format is deleted only when every tool and every item has moved |
| 2026-09-23 | No `who` key - a person is a tag value | Rare enough not to earn a key: 1 person mention in 9,698 task lines |
| 2026-09-23 | No subtasks, the form is flat | Measured: 0 nested task lines in 9,698. Peers plus a shared tag cover it without teaching every tool recursion |
| 2026-09-23 | `tag` and `ctx` stay separate | Kept apart deliberately. Measured: across 9,698 task lines `+tag` appears 51 times and `@word` 4 times, so the split is by intent, not by current usage |
| 2026-09-23 | Notes are `("note" "...")`, not sub-bullets | One mechanism everywhere, including code comments where sub-bullets do not exist. Cost: long notes make long lines, and markdown inside a note stays literal |
| 2026-09-24 | A form inside a string literal is not allowed | The host language escapes the inner quotes, so the marker never opens and the reader reports `path:line:col`. Chosen over unescaping (rewards a bad habit) and over skipping (needs the per-language quote counting this schema deleted) |
| 2026-09-23 | Values are lowercase | The corpus holds `+Finance` and `+finance`; case-sensitive values would keep them apart forever |
| 2026-09-23 | A form in a fenced block is an example, not work | Otherwise this document's own examples become tasks |
| 2026-09-23 | An unknown or repeated key is an error | A typo like `("nite" "x")` must not silently lose the note |
| 2026-09-23 | Writers emit keys in a fixed order | Diffs then show the field that changed, not a reshuffle |
| 2026-09-23 | `recurring` counts from `("due" ...)` | Rent stays on the 5th when paid on the 9th. `from-done` opts into the other behaviour |
| 2026-09-23 | The state is the first value, not the head | The head `task` already says "task", and editing `"todo"` to `"done"` is the same edit as `TODO:` to `DONE:` today |
| 2026-09-23 | Grammar errata: the state, key, date and recurrence are validated by the reader | They are shapes over a string, not separate productions |
| 2026-09-23 | A backslash before anything but `"` or `\` is an error | The reader raises a bad escape; the doc once called `\n` two literal characters. One fail-loudly rule for every malformed form, matching unbalanced parens and unknown keys |
