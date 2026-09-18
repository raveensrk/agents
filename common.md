# Common

## General

At session start, Read these files

- [Emoji Legend](emoji_legend.md) - in the same directory as this file
- [Task Protocol](task.md) - plain-text kanban for AI coding agents
- [Inbox Workflow](inbox.md) - raw capture buffer for unsorted ideas and notes
- [Todo Schema](todo_schema.md) - canonical format for todo items
- [Code Style](code_style.md) - how to write code
- [Git](git.md) - commits and pull requests

Repo layout (`docs/`, `scripts/`, `inbox.md`, …) lives in that repo's `AGENTS.md`.

## Don't

- Apple Reminders. Never create or update them. If I say "create a task", "remind me", or "remind me later", write a short note in this repo instead ([Inbox Workflow](inbox.md), [Task Protocol](task.md)). If there is no repo, ask what to do.

## Working style

- Nothing vague - precise goal / result.
- For multi-step, ambiguous, or high-impact work, use a second AI model to critique the output. Skip it for small, well-defined changes.
- Define the precise criteria for a great result up front.
- Use a past example as the format to match.
- Interview me and ask clarifying questions before starting a task.
- Ask one question at a time.
- Minimal fix - the smallest change that solves the problem. Do not expand scope across layers unless each layer is load-bearing.
- Never measure anything off-screen. Render the content correctly, bring it to foreground and measure it.

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
3. End with one next action.
4. Finish the current issue before raising a new one.
5. Restate progress each turn ("step 3 of 5 done").
6. Give time estimates in concrete units, never "a bit".
7. After a change, show what now works.
8. Errors: state location, cause, and fix. No drama.
9. No preamble, no recaps. The only closer is one next action (item 3).

Exceptions: explain fully when asked to explain. Confirm before destructive actions. After three failed fixes, stop and name the doubtful assumption. If the request is ambiguous, ask one short question.

## Plan mode and Brainstorming

Remind me to brainstorm and plan depending on the prompt and task. Decide based on your best judgement - for multi-step, ambiguous, or high-impact work; skip it for small, well-defined changes.

## Effort level

High effort is the default. Before executing **any** prompt:

1. Analyse the prompt and task.
2. Determine the best effort level for it (low / medium / high / extra / max).
3. Proceed at that level. Do not wait for confirmation.

## Editing

- Before changing files, ask clarifying questions when direction or scope is unclear, and suggest useful improvements when you spot them.

## Memories

Always saved memories locally. Save location: `docs/memories.md`

## Repeatability

Every session must reconstruct identical context from this repo alone, across Claude, Codex, and any other app. Store durable rules, conventions, context, and memories in version-controlled files (preferably under `docs/`). Never in agent-private memory. If it is worth remembering, commit it. Agent-private memory may hold only pointers back to the repo.

## Documentation

Keep `docs/` in sync with the code. Cite sources when you can.

## AGENTS.md

Keep the AGENTS.md file up to date with the repository. Suggest me if any new guideline or rule worth adding.

## Verification

Before you do any work, mention how you could verify that work.

## Responses

- Always respond in active voice.

## Naming

Files and directories use `snake_case` - lowercase words joined by underscores.

- Files: `use_case.md`, `hello_world.py`
- Directories: `docs/`, `scripts/`
- Files under `docs/` use `snake_case` (underscores, not hyphens). Lowercase only.

Exceptions:

- Tool-recognized / conventional files keep their canonical casing: `README.md`,
  `LICENSE`, `AGENTS.md`, `CLAUDE.md`, `SKILL.md`, `.gitignore`.
- `README.md` may stay mixed-case under `docs/` when a host requires that name.

## Markdown

When linking file paths, use markdown links.

Do      : [File Name](/path/to/file_name.md)
Don't   : `/path/to/file_name.md`

Same goes for images and media. For images and media use links with preview `![]()`.

Use relative paths when writing documents. For `@` imports in agent startup instruction files (CLAUDE.md, AGENTS.md), use a `~/` path. Shell variables like `$HOME` are not expanded, and an absolute `/Users/<name>/` path breaks on another machine.

## Long-running jobs

Applies to any background job, and any foreground job expected to exceed 10 min.

Before launching:

1. Run `date "+%-I:%M %p"` to get the current local time, e.g. `2:23 PM`.
2. Check `tmp/job_timings.jsonl` for prior runs of the same job.
3. Estimate the duration in minutes as a range, e.g. `12-18 min`. State the basis: prior run, sample benchmark, or extrapolation.
4. State the completion time as 12-hour local time with AM/PM, e.g. `ETA 2:35-2:41 PM`. If the range crosses noon or midnight, mark both ends, e.g. `ETA 11:50 AM-12:10 PM`.
5. If the upper bound is 60 min or more: ⚠️ warn me and wait for confirmation before launching.

If the job runs past the upper bound: report once with a new estimate and ETA, and keep running.

After the job finishes, append one line to `tmp/job_timings.jsonl`:

```json
{"date": "2026-09-11T14:23:00-07:00", "job": "pytest tests/", "est_min": [12, 18], "actual_min": 15, "basis": "prior run"}
```

- One JSON object per line. Append only; never rewrite the file.
- Store times as ISO 8601 and durations as numbers in minutes. AM/PM is for display only.

`tmp/` is machine-local and must stay in `.gitignore`. Timings depend on hardware, so they are exempt from the Repeatability rule.

## Confirmation

If i ask a question, "Have you read the startup files?", you must answer "HAI!".
