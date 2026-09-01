# Emoji Legend

Canonical emoji vocabulary for agent reports and summaries, across every project.

## Core legend (11)

### Item status - starts a checklist row or table cell

Answers: what happened to this item?

| Emoji | Meaning |
|-------|---------|
| ✅ | Done / success / verified |
| ❌ | Failed / missing / not done |
| ⚠️ | Warning - done but with caveats, or a non-blocking issue |
| ⏳ | Pending / in progress / waiting on something |
| 📥 | New / incoming / not yet triaged |
| 🗑️ | Obsolete / dropped / no longer relevant |

### Rollup health - one per project, area, or section heading

Answers: how is this area overall?

| Emoji | Meaning |
|-------|---------|
| 🟢 | On track / healthy |
| 🟡 | Needs attention / at risk |
| 🔴 | Blocked / critical |

### Markers - communication flags

| Emoji | Meaning |
|-------|---------|
| ❓ | Needs Raveen's input - a decision or answer only he can give |
| 💡 | Idea / suggestion / optional improvement |

## Code-project extension (+2)

For dev repos only:

| Emoji | Meaning |
|-------|---------|
| 🐛 | Bug / defect found |
| 🚀 | Shipped / deployed / released |

## Usage rules

- The emoji starts the line or cell; one status emoji per item.
- Item emojis (✅ ❌ ⚠️ ⏳ 📥) mark single items; health emojis (🟢 🟡 🔴) summarize areas - don't mix tiers. ⚠️ flags an item, 🟡 flags an area; ❌ fails an item, 🔴 blocks an area.
- Group ❓ items together (top or bottom of the report) so "what do you need from me" is scannable at a glance.
- A doc may define its own local legend for other purposes; reports and summaries always use the meanings on this page.

## Where to use emojis and symbols

Add an emoji or symbol next to text of these kinds:

- Directions
- Signs and Symbols
- Emotion and sentiment
- Place
- Animal
- Thing or Object
- Action
- Logo and Icons
- Math
- Shapes

Rules:

- Place the emoji next to the text - never in place of it.
- Treat the list as examples, not a closed set. Fill the gaps with judgement.
- Aim for a quick marker so a human can scan the prose.

## Using from other repos

Reference this file - do not copy it. In the target repo's `AGENTS.md` / `CLAUDE.md`, add an import line pointing at your clone:

```markdown
@<clone-path>/emoji_legend.md
```
