# Common

## General

At session start, Read these files

- [Emoji Legend](emoji_legend.md) - in the same directory as this file

At session start, Read these files if they exist

- ~/dot/docs/todo-schema.md

## Don't

- Apple Reminders

## Working style

- Use agile work. Tight scope.
- Nothing vague - precise goal / result.
- Use a second AI model to critique the output.
- Define the precise criteria for a great result up front.
- Use a past example as the format to match.
- Interview me and ask clarifying questions before starting a task.
- Ask one question at a time.
- Minimal fix - apply the smallest change that solves the problem; do not expand scope across layers unless each layer is genuinely load-bearing.
- Make the smallest possible change to satisfy the request.

## Output style

- Goal: clarity and easy reading 
- I should be able to consume any response fast, at a glance.
- Don't write long paragraphs. Prefer short, concise ones.
- Lots of information to show? Split it into bullets.
- Format status reports and summaries for fast human scanning
- Use checklists, tables, symbols, icons and status emojis instead of dense prose.
- Use visually pleasing colors, emoji, icons, symbols and fonts.
- Emoji meanings live in the canonical [emoji legend](emoji_legend.md).
- Punctuation: use plain hyphens (`-`) only; never em dashes (`—`) or en dashes (`–`).
- Write code and docs that is easily greppable. `find`, `rg` and `grep` must easily find any information.
- A actionable list must always be a numbered list. This is so i can reply referring to those numbers.

The reader has ADHD. Shape every response so it can be acted on:

1. Lead with the answer or next action: command, path, or snippet first.
2. Number multi-step work; one bounded action per step.
3. End with one next action doable in under two minutes.
4. Finish the current issue before raising a new one.
5. Restate progress each turn ("step 3 of 5 done").
6. Give time estimates in concrete units, never "a bit".
7. After a change, show what now works.
8. Errors: state location, cause, and fix. No drama.
9. Cap lists at 5 items.
10. No preamble, no recaps, no closers.

Exceptions: explain fully when asked to explain. Confirm before destructive actions. After three failed fixes, stop and name the doubtful assumption. If the request is ambiguous, ask one short question.

## Plan mode and Brainstorming

Remind me to brainstorm and plan depending on the prompt and task. Decide based on your best judgement - for multi-step, ambiguous, or high-impact work; skip it for small, well-defined changes.

## Effort level

High effort is the default. Before executing **any** prompt:

1. Analyse the prompt and task.
2. Determine the best effort level for it (low / medium / high / extra / max).
3. If it **differs** from the current effort level, recommend the change with a
   one-line reason and **wait for confirmation** before executing.
4. If it **matches** the current level, proceed without asking.


## Editing

- Before changing files, ask clarifying questions when direction or scope is unclear, and suggest useful improvements when you spot them.

## Memories

Always saved memories locally. Save location: `docs/memories.md`

## Repeatability

The context must be maintained between every chat and session. Irrespective ot the App. I use both Claude and Codex.

Repeatability is required: every session must reconstruct identical context from this repo alone. Store all durable project rules, conventions, context, and "memories" in version-controlled repo files (preferably under `docs/`) - never in agent session/private memory. No agent knowledge is assumed to carry across sessions; if something is worth remembering, commit it to the repo. Agent-private memory may hold only pointers back to the canonical repo location.

All durable rules and context live in this repo, never in agent session/private memory. Every session reconstructs identical context from the repo alone.

## Documentation

- Documentation lives in [docs](docs).
- Every subdirectory under `docs/` must have an `index.md`.
- As you work, keep the docs/ up to date. Always recoincile documentation and codebase after every edit/change.
- As we work on the project write useful information and documentation into docs/ directory in the root. Write it like a wiki using markdown files.
- When writing documentation, add citations when you can.

## AGENTS.md

Keep the AGENTS.md file up to date with the repository. Suggest me if any new guideline or rule worth adding.

## Verification

Before you do any work, mention how you could verify that work.

## Responses

- Suggest me some follow-up prompts after you finish the work.
- Always replay in clear and concise tone.
- Be concise.
- Always respond in active voice.

## Directory path

- Docs: `docs/`
- Scripts: `scripts/`
- Tests: `tests/`
- Todos and Inbox: `docs/notes/inbox.md` - items follow the [Todo Schema](~/dot/docs/todo-schema.md)
- Temporary files: `tmp/`

## Naming

Files and directories use `snake_case` - lowercase words joined by underscores.

- Files: `use_case.md`, `hello_world.py`
- Directories: `docs/`, `scripts/`

Exceptions:

- Tool-recognized / conventional files keep their canonical casing: `README.md`,
  `LICENSE`, `AGENTS.md`, `CLAUDE.md`, `SKILL.md`, `.gitignore`.

## Markdown

When linking file paths, use markdown links.

Do      : [File Name](/path/to/file_name.md)
Don't   : `/path/to/file_name.md`

Same goes for images and media. For images and media use links with preview `![]()`.

Use relative paths when writing documents. For `@` imports in agent startup instruction files (CLAUDE.md, AGENTS.md), use a `~/` path. Shell variables like `$HOME` are not expanded, and an absolute `/Users/<name>/` path breaks on another machine.

## Tokens

- Automatically suggest when to compact or clear at the end of your response.

## Commits and PR Titles

When committing don't add co author by claude.

### Commit Conventions

Conventional Commits with scopes. Omit scope when spanning multiple scopes.

See: https://www.conventionalcommits.org/en/v1.0.0/

Use conventional commit-style messages and PR titles: type(scope): summary.

Types are feat, fix, docs, chore, refactor, and test.

Scopes are optional; use the affected package or area when helpful, e.g. core, web, tui, app, design, verif, desktop, etc.

### Example

- fix(tui): simplify thinking toggle styling
- docs: update contributing guide
- chore(verif): rename variables.

## Naming Enforcement (Read This)

THIS RULE IS MANDATORY FOR AGENT-WRITTEN CODE.

- Use single word names by default for new locals, params, and helper functions.
- Multi-word names are allowed only when a single word would be unclear or ambiguous.
- Do not introduce new camelCase compounds when a short single-word alternative is clear.
- Before finishing edits, review touched lines and shorten newly introduced identifiers where possible.
- Good short names to prefer: pid, cfg, err, opts, dir, root, child, state, timeout.
- Examples to avoid unless truly required: inputPID, existingClient, connectTimeout, workerPath.

## Avoid else statements

Prefer early returns (or an IIFE) over else. After an `if` that returns/throws, the else is redundant.

## Markdown Tables

Do not pad markdown table cells for column alignment. Use the compact form with single-space-padded content cells and a minimal separator row:

```
| Command | What it runs |
|---|---|
| `app serve` | runs app web ui |
```

Do **not** right-pad cells to line up columns:

```
| Command                       | What it runs             |
| ----------------------------- | ------------------------ |
| `app serve`                   | runs app web ui          |
```

Padding makes every content change rewrite the entire table, which blows up diffs on untouched rows.

## Pull Requests

PR descriptions should explain what changed, why the change is needed, and the intent or constraints a reviewer cannot infer from the diff alone. Keep simple PRs brief, but give non-trivial changes enough context to stand on their own. Skip file-by-file inventories, test result summaries, and anything obvious from the code itself.

## GUI Apps

- GUI apps you implement must be easily debuggable and navigatable from the claude code

## CLI and GUI Apps

- Always implement good logging mechanism to help you debug the programs and apps easily

## Unsorted

- ALWAYS USE PARALLEL TOOLS WHEN APPLICABLE.
- Keep things in one function unless composable or reusable
- Avoid unnecessary destructuring. Instead of const { a, b } = obj, use obj.a and obj.b to preserve context


## FAB's AGENT.MD

From <https://fabiensanglard.net/agent.md/index.html>.

- When writing something intended for human consumption, (comment, commit message, reply to prompt) use as few words as possible. Pick every word meticulously to reduce the volume to a strict minimum. Be down to the point. Less is more.

- Avoid superlatives and praise. Stop telling me I am absolutely right. Give me the cold hard truth.

- Avoid magic numbers and strings by extracting recurring or meaningful values into descriptive constants (const) or enums. Keep self-explanatory, one-off values inline to avoid clutter. If a value comes from a spec (e.g. HTTP 200 OK), use a constant regardless.

- Reduce code indentation. Avoid Arrow Anti-Pattern. Leverage early return and continue.

- Keep function names short. Less than 30 characters.

- Use enums instead of booleans for function parameters.

- Let the reader of the code breathe. Add empty lines between logical blocks of code.

- Add a small, to the point, comment to explain *what* the block does and *why*. Use examples when possible. Propose ASCII drawings to explain complete systems.

- Treat member visibility changes as a breaking design shift. Keep all fields and functions private unless external access is strictly required by the design. Prompt the user for explicit approval before changing any access modifier from private to internal or public.

- Program to levels of abstraction. Lower-level mechanics (e.g., raw hardware I/O, sector parsing, direct socket streams) must be encapsulated in a dedicated driver/abstraction layer. Expose clean, high-level APIs to the rest of the application so calling code works with domain concepts, not raw implementation details.

- Don't touch blocks of code unrelated to the feature you implement. e.g. Don't add comments to a block of code if you did not create it or modify it. As much as possible try to minimize the number of changed lines when implementing a feature.

- Strictly adhere to the layered boundary hierarchy: each layer may only communicate with its immediate neighbor directly below it. Never "punch holes" through layers (e.g., controllers or UI components must never directly call database queries, raw hardware drivers, or low-level network clients; always route through the intermediate service/abstraction layer).

- Always use {}, even on a one-line "if" statement.

When you write a commit message, follow these 7 rules:
Rule 1: Separate the subject line from the body with a single blank line.
Rule 2: Limit the subject line to 50 characters (72 is the absolute hard limit).
Rule 3: Capitalize the first letter of the subject line.
Rule 4: Do not end the subject line with a period.
Rule 5: Use the imperative mood in the subject line (e.g., "Fix bug," "Add feature," 
        not "Fixed" or "Adds"). Test formula: It must complete the sentence: "If applied,
        this commit will [your subject line here]".
Rule 6: Wrap the body text manually at 72 characters to prevent Git formatting issues.
Rule 7: Use the body to explain what and why vs. how. Assume the code explains the how;
        the message must explain the context and reasoning. 

- If the prompt indicates that a bug is being fixed, don't write the fix right away. First write the test. Observe it failing. Then write the fix. And observe the test passing.

## Confirmation

If i ask a question, "Have you read the startup files?", you must answer "HAI!".
