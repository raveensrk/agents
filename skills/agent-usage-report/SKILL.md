---
name: agent-usage-report
description: Build a self-contained HTML report of every AI model used across agent harnesses (pi, Claude Code, Codex, opencode) with tokens, cost, cost per 1M, charts, and rankings for the most intelligent and most efficient model. Use when the user asks what models they used, token or spend totals, which model is smartest or cheapest, a usage report, or "how much have I spent on AI".
argument-hint: "[0d | -1d | -Nd | -N | -Nw | --since YYYY-MM-DD | --until YYYY-MM-DD]"
---

# Agent usage report

Read the token logs every agent harness on this machine writes, price them,
score the models, and open one HTML report. The bundled script does all the
reading and math; you choose the window and relay the result.

## Requirements

- python3 3.8+ and nothing else. Stdlib only, no pip install.
- Works on macOS and Linux.
- Network is optional. Pricing is fetched from
  [models.dev](https://models.dev/api.json) and cached for 24 hours; a bundled
  snapshot covers offline runs.

## What it reads

| Harness | Default location | Cost |
|---|---|---|
| pi | `~/.pi/agent/sessions/**/*.jsonl` | recorded |
| Claude Code | `~/.claude/projects/**/*.jsonl` | computed |
| Codex | `~/.codex/sessions/**/rollout-*.jsonl`, `~/.codex/archived_sessions/` | computed |
| opencode | `~/.local/share/opencode/opencode.db` (SQLite) | recorded |

Missing harnesses are skipped, not an error. Add others with
`extra_harnesses` in the config (see Setup).

## What the report contains

- Headline totals: spend, tokens, models, sessions, requests, cache hit rate.
- Model leaderboard: turns, input, output, total, blended $/1M, cost, and both
  ranks, with a recorded vs computed cost badge. Click any column header to
  sort, filter by model name, harness, or ranked-only, and the row count updates
  live. Sorting and filtering need JavaScript; without it the table still
  renders, just unsorted and unfiltered.
- Verdicts: **most intelligent** and **most efficient**, each with the signals
  that decided it.
- Charts: cost per 1M, where the money went, spend over time and burn rate,
  projects, tool usage, context pressure, an activity heatmap, model switching,
  and a waste report (failed or aborted turns and their cost).
- A JSON sidecar (`<report>.json`) with the same data, no raw turns.

Token fields are normalised so they always add up:
`total = input + cache_read + cache_write + output`, where `input` is uncached.
Codex folds cached tokens into its input counter, and the adapter subtracts
them, so totals stay comparable across harnesses.

## How the scores work

Intelligence is a weighted percentile composite of your own usage signals.
Signals are ranked across the models you used (not a public benchmark), then
shrunk toward the group mean by sample size so a model with few turns cannot
win on a lucky percentile.

| Signal | Weight | Direction |
|---|---|---|
| turns per request | 30% | lower better |
| failed turns + failed tool calls | 25% | lower better |
| reasoning share (reasoning / (reasoning + output)) | 20% | higher better |
| tokens per request | 15% | lower better |
| correction rate (short pushback messages) | 10% | lower better |

- Models under **30 turns** are listed but not ranked. Override with `min_turns`.
- **Efficiency** = intelligence divided by blended cost per 1M tokens, then
  ranked. A free model that also scores well wins outright.
- **Corrections** are user messages after the first, under 600 characters, that
  match pushback words ("no", "wrong", "actually", "try again", "revert").
  A heuristic, labelled as such in the report.

The report states this methodology in its footer. Do not present a score as a
fact about a model in general: it is a statement about your usage, and requests
differ in difficulty, so a model used for short questions can look thriftier
than one driving long agentic sessions.

## Hard rules

- Run `scripts/report.py` unchanged. Do not re-implement its parsing.
- Read-only. The script never writes to any harness log or database.
- Never invent, merge, or drop models, and never round a total by hand. Report
  only what the script prints or writes.
- The report holds your spend. It is written to `~/Downloads` by default, or
  to `output_dir` in the config, or `--out`. The script refuses to write inside
  a git repository and exits with `ERROR:` if you try.
- If the script prints a line starting with `ERROR:`, stop, show it, and fix
  the cause.

## Step 1 - Window

Pass a shortcut as the first argument, or `--since` / `--until`.

| Shortcut | Window |
|---|---|
| `0d` | today, midnight to now |
| `-1d` | yesterday only, midnight to midnight |
| `-Nd` | that one day, N days ago |
| `-N` | last N days, today included, ending now |
| `-Nw` | last N weeks, ending now |

- No argument means **all time**. This is the default; the report is a
  lifetime view unless asked otherwise.
- Map plain words: "today" is `0d`, "yesterday" is `-1d`, "last 7 days" is `-7`,
  "this week" is `-1w`.
- For any other window, work out the dates from the current local date
  (`date`) and pass `--since "YYYY-MM-DD HH:MM"` and `--until`.
- Ask one question if the window is ambiguous.

## Step 2 - Run

Run from this skill's directory, with `<skill_dir>` being the directory holding
this file. It takes a few seconds.

```bash
python3 <skill_dir>/scripts/report.py
python3 <skill_dir>/scripts/report.py -7
python3 <skill_dir>/scripts/report.py --since "2026-09-01" --until "2026-09-15"
python3 <skill_dir>/scripts/report.py --out ~/Downloads/agent_report.html
```

Useful flags:

- `--check` - detect harnesses, count records, resolve prices, write nothing.
- `--check --check-pricing` - also report how many models were priced.
- `--no-open` - write the report without opening a browser.
- `--json-only` - write only the JSON sidecar.
- `--offline` - never touch the network; use the cached or bundled prices.
- `--refresh-pricing` - re-fetch models.dev now.
- `--min-turns N` - override the ranking threshold.
- `--config PATH` - use a specific config file.

The script prints a summary: harnesses found, totals, the two winners, and both
output paths. It writes to `~/Downloads` unless `--out` or `output_dir` says
otherwise, and opens the HTML in the browser unless `--no-open`.

## Step 3 - Report

After running, reply in chat with:

1. The window and the harnesses that contributed.
2. Totals: tokens, spend, turns, requests, sessions. Say how much of the spend
   is recorded versus estimated.
3. Most intelligent model: name, score, turns, and the two or three signals
   that lifted it.
4. Most efficient model: name, blended $/1M, and its quality per dollar.
5. One line on the biggest cost driver.
6. The HTML path, and whether the browser opened.

Keep it short. The HTML carries the detail; the chat message is the summary.
If the user asks "why", open the report and quote the relevant section rather
than recomputing.

## Config

Optional, at `~/.local/share/agent_report/config.json`:

```json
{
  "min_turns": 30,
  "shrink_turns": 200,
  "output_dir": "~/Downloads",
  "score": {
    "weights": {
      "turns_per_request": 0.30,
      "failure_rate": 0.25,
      "reasoning_share": 0.20,
      "tokens_per_request": 0.15,
      "correction_rate": 0.10
    }
  },
  "extra_harnesses": [
    {"name": "amp", "label": "Amp", "glob": "~/.amp/**/*.jsonl"}
  ]
}
```

`extra_harnesses` turns on the generic JSONL sniffer, which finds any object
with an input-ish and output-ish token key (`input_tokens`/`output_tokens`,
`prompt_tokens`/`completion_tokens`, and camelCase variants).

Price overrides go in `~/.local/share/agent_report/prices.json`, keyed by
`provider/model`, in dollars per million:

```json
{ "anthropic/claude-opus-5": {"input": 5, "output": 25, "cache_read": 0.5, "cache_write": 6.25} }
```

Resolution order: your `prices.json`, then `~/.pi/agent/models-store.json`,
then models.dev, then the bundled snapshot.

## Setup - add a harness

1. Run `python3 <skill_dir>/scripts/report.py --check` to see what is detected.
2. If the harness is not listed, find its log directory and format.
3. If it writes JSONL with a usage object, add it under `extra_harnesses` and
   re-run `--check`.
4. If it needs real parsing (SQLite, protobuf, unusual field names), add a
   module in `scripts/adapters/` exposing `NAME`, `LABEL`, `available()`,
   `discover()`, `records()`, and register the name in
   `scripts/adapters/__init__.py`. Copy `adapters/pi.py` as the template and
   add a fixture under `tests/fixtures/`.

## Maintenance

- `python3 scripts/refresh_snapshot.py` updates the offline price snapshot.
- `python3 tests/run_tests.py` runs the adapter, pricing, scoring and render
  tests against fixtures. Run it after any edit.
