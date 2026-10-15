---
name: trello-task
description: Write a new Trello task card in the product voice, then push it to the Redline OS or AutoTurn board. Use when the user says "crea una tarjeta de Trello", "create a Trello card", "make a card for this", "add this to the backlog", or describes work that should become a ticket. For editing or moving an EXISTING card, use the trello skill instead.
---

# Write and push a Trello card

Help the user write a Trello task card, then push it. If details are unclear,
ask clarifying questions **before** writing.

## The card body

Use this exact structure:

**Title** — short, outcome-focused, no technical wording.

**Context/Problem:** 1–2 sentences on the context, motivation or goal. This does
NOT have to describe a problem — it can be an opportunity, a vision, or the
purpose of the feature. Frame it around what the user or business needs, not
necessarily what's broken.

**Solution:** 1–3 bullets describing the feature from a user or product
perspective. Do NOT describe implementation, services, endpoints, refactors or
data contracts.

**Acceptance Criteria:** 2–5 short outcome-based statements describing what the
user can see, experience or do once this is complete. Write them as simple
sentences, not checkboxes.

Rules:

- Be brief and direct. No fluff.
- Plain language, not technical jargon.
- Focus on visible behavior and business outcome, not how it's built.
- Never mention APIs, endpoints, refactors, services, database changes, contracts or plumbing.
- If the task mixes multiple independent changes (rename, export, content, etc.), split them into separate cards automatically.
- Keep the entire card under 130 words.
- **Write the card in English**, whatever language the conversation is in. The board is the team's, and it is English. Match the artifact's language, not the chat's.
- Output raw markdown for the card body, and show it to the user before pushing.

## Setup (once per person)

Same credentials and default board as the `trello` skill, in
`~/.config/trello/credentials`. If anything is missing, run
`python3 ~/.claude/skills/trello/scripts/trello_update.py setup`. It prints the exact
clicks on trello.com for the token, and the commands to save it and to pick a board.

Cards are pushed with the same standard-library CLI the `trello` skill uses — no
venv, no `pip install`:

```bash
python3 ~/.claude/skills/trello/scripts/trello_update.py create ...
```

Never hand-roll REST calls for this, and never put a key or token on a command
line. The CLI resolves every list, label and custom-field id **by name, against
the board being written to** — see "Custom field ids are PER BOARD" below for
why that is the whole ballgame.

## Which board — ask, never assume

Two boards, and they are not interchangeable:

| Board | Short id | Reach it with | Use for |
|---|---|---|---|
| **Redline OS** | `JEcYPEdW` | `TRELLO_BOARD=redline` | Redline OS: the rebuild, ports, parity work, bugs |
| **Autoturn.ai Wholesale** | `t7CdxreR` | `TRELLO_BOARD=autoturn` | AutoTurn: pricing, scraping, dealer match, checkout, data lake |

The user's `TRELLO_BOARD_ID` default is a **fallback, not the answer**. If the user
names a board ("the AutoTurn board"), prefix the command with
`TRELLO_BOARD=<short id or name>`. If no board is named and the work's subject
doesn't make it obvious, **ask**. Getting this wrong means the user has to move
the card by hand. `... trello_update.py boards` lists every board they can write to.

`JEcYPEdW` was renamed from "Lotgentix" to **"Redline OS"**, so a name check
against the old label finds nothing. When you confirm a board mapping against
the API, match on `shortLink`, never on name.

## Required values

Before pushing, you MUST have these five. If any is missing from the user's
message, ASK. Do not guess.

1. **List** — the two boards differ:
   - Redline OS: `Backlog`, `On-Deck`, `Todo`, `In-progress`, `QA & Testing`
   - AutoTurn: `Backlog`, `On-Deck`, `Sprint Todo`, `In-progress`, `QA & Testing`

   Both also carry a rolling `✅ Done Week <date>` list — don't file new cards
   there. `create` refuses an archived list outright.
2. **Label** — the label sets are very different:
   - **Redline OS (18)** — a card often takes one surface label plus one kind-of-work label:
     - *Surface:* `/admin`, `/dealer`, `/redline`, `No-login view`
     - *Kind of work:* `Rebuild`, `PARITY MISSING`, `UX Simplify`, `Documentation`, `System Config`
     - *Domain:* `CDK sync`, `CS Agent`, `SMS & Emails`, `Notification System`
     - *Triage:* `BUGGY BUG BUG`, `Found in QA`, `HOLD`, `QUESTIONS`
     - *Legacy:* `Lotgentix`
   - **AutoTurn (35)**: `Core Platform`, `Pricing Service`, `Infrastructure`, `Scraping`, `Dealer Match V3`, `Mobile App`, `BI & Data Science`, `Dealership Page`, `Checkout Workflow`, `Backend`, `Why Buy Page`, `Why Sell Page`, `Notification System`, `Data Lake Migration`, `BUGGY BUG BUG`, `Cross-Org Fix`, `Redline QA`, `Planning`, `Feedback`, `QUESTIONS`, `BLOCKED`, `Org Features`, `Research`, `Requests`, `Emails`, `CapitalOne`, `Trade Wizard`, `Self-Healing`, `CarGurus`, `Lotgentix`, `CarMax`, `Trade Agent`, `Carvana`, `Rebuild`, `Data QA`

   These lists are documentation and go stale. Fetch the live set with
   `trello_update.py board` rather than trusting them, and offer real options
   when you ask.
3. **Effort (1–10)** — a number for the `Effort (1-10)` custom field.
4. **Priority** — one of `Highest`, `High`, `Medium`, `Low`, `Lowest`, `Not sure` (same options on both boards).
5. **Due Date** — REQUIRED. ISO 8601 (`YYYY-MM-DD`). If the user gives a relative
   phrase ("today", "tomorrow", "this Wednesday", "next Friday", "in 2 weeks"),
   INFER the exact date from today's date in system context and state the
   inferred date back when reporting the card, so they can correct it. Only ask
   if there's no due-date hint at all.

## Custom field ids are PER BOARD — resolve them, don't hardcode

This is the trap. Both boards have fields with the same names and different ids:

| Field | Redline OS | AutoTurn |
|---|---|---|
| `Effort (1-10)` (number) | `6a43e0ad8fb17dd17b92c303` | `696efb921a4080297fa40bfa` |
| `Priority` (list) | `6a43e0ad8fb17dd17b92c2f4` | `696efeb22a49a20fc3da0bfd` |

The ids above are documentation, not inputs. `create` looks every one of them up
by name from `GET /boards/{board}/customFields` for the board it is writing to —
a hardcoded AutoTurn id silently fails to set the field on a Redline OS card,
with no error. Same for list ids, label ids and Priority option ids.

## Flow

1. Write the card body and show it to the user.
2. Resolve the target board from the request (table above); fall back to the
   default board only when no board was named and the subject doesn't imply one.
3. Confirm you have all five required values. Ask for whatever is missing; run
   `trello_update.py board` to offer the live lists and labels.
4. Push it, passing the body on stdin so no quoting mangles it:

```bash
python3 ~/.claude/skills/trello/scripts/trello_update.py create \
  "Short outcome-focused title" \
  --list "Backlog" \
  --label "/admin" --label "Rebuild" \
  --effort 3 --priority Medium --due 2026-09-24 \
  --desc - <<'BODY'
Context/Problem:
…
BODY
```

   For AutoTurn, prefix the command with `TRELLO_BOARD=autoturn`.
5. Report back what `create` prints: the short URL, **which board**, list,
   labels, effort, priority and due date — including any date you inferred.

## Rules

- These boards are **shared with the team**. A card appears for everyone the
  moment it is created. Show the body and confirm the five values before
  pushing; don't push a card the user hasn't seen.
- One card per independent change. Split rather than bundle.
- Never edit or move an existing card here — that's the `trello` skill.
