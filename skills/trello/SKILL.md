---
name: trello
description: Update existing Trello cards on the Redline OS or AutoTurn boards — move a card, comment progress, tick checklist items, set labels/assignees/due/effort/priority, or load a card as the spec for a feature. Use when the user says "comment on card X", "move 601 to QA", "what's on my plate", "let's work card #243", or names a Trello card. NOT for creating cards — that is the trello-task skill.
---

# Update a Trello card

Update **existing** Trello cards. This is for tracking progress and working a
specific feature — NOT for creating cards. If the user wants a new card, use the
`trello-task` skill instead.

## Setup (once per person)

Everyone uses their **own** Trello key and token, kept in
`~/.config/trello/credentials`, outside every repo, so they work from any checkout
and can never be committed. Every write lands under the token owner's name, so
never borrow someone else's token.

```bash
python3 ~/.claude/skills/trello/scripts/trello_update.py setup
```

`setup` walks through whatever is missing, in order:

1. **No credentials:** it prints the exact clicks on trello.com to get an API key
   and a token, and the commands that save them to the credentials file.
2. **No default board:** it lists every board the token can see, with short ids,
   and the exact command that sets `TRELLO_BOARD_ID` in the credentials file.
3. **All set:** it shows who the token belongs to and which board is the default.

Any other command stops with the same guidance when something is missing. When
that happens, show the user the output, let them run the commands that need their
key or token themselves, and never ask them to paste a token into the chat. Don't
go looking for a token anywhere else.

The script is **standard library only**, so there is no venv and no `pip install`:

```bash
python3 ~/.claude/skills/trello/scripts/trello_update.py <subcommand> ...
```

Never pass the key or token on the command line.

## Which board

There is no built-in default. Each person sets theirs as `TRELLO_BOARD_ID` in
`~/.config/trello/credentials`. To work on any other board, pass `TRELLO_BOARD`
for that one command. It takes the board's short id or any unique part of its name:

```bash
python3 ~/.claude/skills/trello/scripts/trello_update.py boards     # your boards + exact commands
TRELLO_BOARD=autoturn python3 ~/.claude/skills/trello/scripts/trello_update.py board
TRELLO_BOARD=JEcYPEdW python3 ~/.claude/skills/trello/scripts/trello_update.py board
```

The team's two boards are not interchangeable:

| Board | Short id | Use for |
|---|---|---|
| **Redline OS** (formerly "Lotgentix") | `JEcYPEdW` | The Redline OS rebuild, ports, parity work, bugs |
| **Autoturn.ai Wholesale** | `t7CdxreR` | AutoTurn: pricing, scraping, dealer match, checkout, data lake |

A card number can exist on both boards and resolve to the wrong card. If the user
names a board, pass it with `TRELLO_BOARD`. If they don't and the subject doesn't
make it obvious, ask. If `TRELLO_BOARD` matches none or several of the user's
boards, the CLI lists them. Pick the right one from that list, never guess.

Run `... trello_update.py board` any time you need the current lists, labels,
members and custom-field options. Run `--help` or `<subcommand> --help` for
exact flags. The script resolves list / label / member / custom-field ids **by
name at call time** for whichever board is targeted, so nothing is hardcoded.
That matters: the two boards' Effort and Priority fields share names but have
different ids.

## Referring to a card

Every subcommand takes a card reference as its first argument. Accepted forms:

- short id — `601` or `#601`
- name substring — `"Count one sale"`
- short link or full URL — `VkI26b0H`, `https://trello.com/c/VkI26b0H`

Ambiguous name matches fail loudly with the candidate list — pick from it, don't
guess. If the user names a card vaguely, run `search` first and confirm which one
they mean before mutating anything.

## Subcommands

**Read**
- `search <query> [--list NAME] [--archived]` — find cards by name, description, or short id
- `cards [LIST]` — cards in one list, or every open list
- `mine` — cards assigned to the token's owner, grouped by list
- `wip` — In-progress + QA & Testing at a glance
- `show <card> [--comments N]` — full detail: list, labels, members, due, custom fields, description, checklists, recent comments
- `board` — lists, labels, members, custom fields

**Write**
- `move <card> <list> [--comment TEXT] [--top|--bottom]` — move between lists
- `comment <card> "TEXT"` — post a progress note
- `desc <card> --append TEXT` / `--set TEXT` — edit the description
- `check <card> "ITEM"` / `uncheck <card> "ITEM"` — tick checklist items by substring (`--all` for every match)
- `add-items <card> "ITEM" ["ITEM"...] [--checklist NAME] [--checked]` — add checklist items, creating the checklist if needed
- `label <card> [--add NAME] [--remove NAME]` — repeatable flags
- `assign <card> [--add NAME] [--remove NAME]` — accepts full name or `@username`
- `due <card> [DATE|clear] [--complete|--incomplete]` — ISO 8601; infer `YYYY-MM-DD` from relative phrases using today's date and state the inferred date back
- `field <card> [--effort N] [--priority LEVEL]` — Effort (1–10), Priority (`Highest`/`High`/`Medium`/`Low`/`Lowest`/`Not sure`)
- `archive <card> [--unarchive]`

## Board conventions

Lists flow `Backlog` → `On-Deck` → `Todo` (AutoTurn: `Sprint Todo`) →
`In-progress` → `QA & Testing` → the current `✅ Done Week M/D/YYYY` list.

- Starting work → move to `In-progress` and assign yourself if you aren't already on it.
- Ready for review/testing → move to `QA & Testing`, and comment what changed and what to verify.
- Finished → move to the **current** week's Done list. There are many archived `✅ Done Week ...` lists; only one is open. Get its exact name from `board` (the one with no `(archived)` marker) — never move a card to an archived Done list.
- Merged to `dev` counts as done: move it to the week's Done list at merge time.
- Blocked → keep it where it is, add the `BLOCKED` label, and comment why plus what would unblock it.

## Common flows

**Progress update.** `show` the card first so the note builds on what's already
there, then `comment` and tick any checklist items the work completed. If the
work finished a stage, move the card in the same pass.

**Working a feature.** When the user wants to work on a card, `show` it and use
the description and acceptance criteria as the spec for the implementation.
Restate the acceptance criteria back before starting so you're aligned. Read
**every** row of a checklist, including the ticked ones — a ticked row can still
carry open work in its body. When the work is done, come back and update the
card: comment what was built, tick the criteria if they're checklist items, and
move the list forward.

**End-of-day sync.** `mine` or `wip`, then update each card the user reports on.

## Writing comments

Progress comments are for the team, so:

- Write them in **English**, whatever language the conversation is in. Match the artifact's language, not the chat's.
- Lead with status: what moved forward, what's left, what's blocked.
- Keep it to a few lines. No preamble, no restating the card.
- PR links, branch names and specific numbers are welcome here — comments are work-tracking, unlike descriptions.
- Descriptions stay product-facing in the `trello-task` voice: plain language, visible behavior, no endpoints or plumbing. If you `desc --append`, match that voice.

## Rules

- **These boards are shared with the team.** Every write is visible to others immediately, under the token owner's name, and there is no undo. When the user's instruction is unambiguous ("move 601 to QA", "comment on 593 that it's deployed"), just do it. When you're inferring the card, the target list, or writing a comment from your own read of the work, state the exact change you're about to make and confirm first.
- Never create cards here — that's the `trello-task` skill.
- Never edit or move a card the user didn't ask about, even if it looks stale.
- Batch related updates on one card into a single pass, then report once.
- After writing, report the card's short id, name, its new list, and what changed.
