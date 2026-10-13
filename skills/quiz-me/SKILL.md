---
name: quiz-me
description: Build a local study app (flashcards plus a multiple-choice quiz) for learning a codebase, a project's domain, its docs, or any topic, served with Vite from a git-ignored .quiz-me folder. Use whenever the user wants to learn, study, review, memorise, or get quizzed on something — "quiz me on this repo", "make flashcards for how auth works", "help me learn this codebase", "test what I know about the billing flow", "onboarding cards for new devs", or a bare /quiz-me with no topic (then pick the topics yourself). Not for writing unit tests, and not for grilling the user about a plan.
compatibility: Needs Python 3.9+ and Node with npx (Vite 8 is fetched on first run).
---

# Quiz Me

Turn a project, or one part of it, into a deck of flashcards and quiz questions, served as a small local web app.

The app is already built. It lives in `assets/template/` and every run reuses it, so decks look the same and runs stay fast. Your job is the content: read the source, decide what is worth knowing, and write one deck file. Don't rebuild or restyle the UI per run. If the user asks for UI changes, edit the template in this skill folder (follow the `frontend-design` skill), then rerun the scaffold script to copy it in.

## Steps

1. **Set up the folder.** Run `python3 <this skill>/scripts/scaffold.py [path]`.
   It creates `.quiz-me/` at the git root (or in the given folder if it is not a repo), copies the app in, and writes a `.gitignore` containing `*` inside the folder. That makes git ignore the whole folder without editing the project's own `.gitignore`. It also writes a Vite config with a port fixed for this project, and prints the URL. Existing decks are kept. Rerunning it refreshes the app files.

2. **Decide the scope.**
   - The user named a topic: that is the deck. Read the code and docs that cover it, following calls far enough to explain how it really works.
   - No topic: survey the project and pick what a newcomer most needs. Start with the README, CLAUDE.md or AGENTS.md, any docs folder, entry points, data models and schemas, routes or commands, and config. Pick 3 to 6 topics. Prefer the project's core domain (what it does and the words it uses) over tooling and boilerplate.
   - Not a code project (notes, docs, a research folder): same approach, grounded in the files there. If there are no relevant files and the user named a general subject, use what you know, and say so in `source`.
   - For a large repo, it is fine to send Explore subagents to read different areas in parallel. Write the deck yourself, in one pass, so it reads consistently.

3. **Write the deck** to `.quiz-me/decks/<slug>.json`, using the format below. The slug is a short kebab-case name for the topic, like `billing-flow` or `overview`. A new topic gets a new file. Don't overwrite an existing deck unless the user asks to update it.

4. **Check it.** Run `python3 <this skill>/scripts/check_deck.py .quiz-me/decks/<slug>.json`. Fix every error. Take warnings seriously: a ref that doesn't resolve usually means a wrong path or a detail you didn't actually see in the code.

5. **Serve it.** First check whether it is already running: `curl -s -o /dev/null -w '%{http_code}' <url>`. If you get 200, just tell the user to refresh; Vite picks up new deck files on its own. Otherwise start it in the background with the serve command the scaffold printed (`npx --yes vite@8 <folder>`), wait a few seconds, then open the URL with `open <url>` (macOS) or `xdg-open <url>`.

6. **Report back** in a few lines: the URL, the deck name, how many cards and questions, and the topics. Nothing else unless asked.

## What makes a good deck

A deck is only worth studying if it teaches the things that matter. Aim for understanding, not trivia. A useful test: would a senior person on this project be glad a new hire knew this?

- **Worth asking:** what a concept is and why it exists; how a flow works, step by step; what happens when something goes wrong; where you would go to change a behaviour; the project's own vocabulary; invariants and gotchas that bite people; how two parts relate.
- **Not worth asking:** line numbers, exact variable spellings, default values nobody needs to memorise, file sizes, or anything a quick search answers better than memory.
- **Ground every item.** Put the file it came from in `ref` (`path/from/root.py:42`, a line is optional). The learner can go and check, and it keeps you honest: if you can't point to where something is true, leave it out.
- **Flashcards:** the front is a clear question or prompt. The back is short, one to three sentences, so it can be recalled in a few seconds. One idea per card.
- **Quiz questions:** three or four choices. Wrong choices should be believable and come from the same project, like a sibling function, a neighbouring concept, or a common misreading. Then the question tests understanding, not spotting the odd one out. Keep choices similar in length and style; the longest answer being right is a classic giveaway. Skip "all of the above", since choices are shuffled. In `why`, say why the right answer is right and what is wrong with the most tempting wrong one.
- Cards and questions should cover the same ground from different angles, not repeat each other word for word.
- **Size:** about 20 to 30 cards and 10 to 15 questions by default. A narrow topic can be smaller; a whole-project overview can go to about 40 cards. If the user asks for a number, use it.
- Use backticks for inline code and fenced blocks for short snippets (8 lines or fewer). Both render on the cards. `**bold**` works too.

## Deck format

```json
{
  "title": "How payments flow through acme-api",
  "about": "From checkout to a settled invoice, and what happens when Stripe retries.",
  "source": "acme-api @ 3f2c1a9",
  "created": "2026-10-13",
  "topics": ["Invoices", "Webhooks", "Retries"],
  "cards": [
    {
      "topic": "Invoices",
      "front": "What turns a draft invoice into a sent one?",
      "back": "`InvoiceService.finalize()` locks the line items, assigns the number, then queues the email.",
      "ref": "src/billing/invoice_service.py:88"
    }
  ],
  "questions": [
    {
      "topic": "Webhooks",
      "ask": "Stripe delivers the same `payment_intent.succeeded` event twice. What stops a double credit?",
      "choices": [
        "`handle_event` skips event IDs already in `processed_events`",
        "The retry worker drops duplicates older than five minutes",
        "A unique index on `payments.amount` rejects the insert",
        "Stripe signs each event once, so the copy fails verification"
      ],
      "answer": 0,
      "why": "Events are recorded by ID before any side effects. The retry worker only handles outgoing calls, so it never sees inbound duplicates.",
      "ref": "src/webhooks/stripe.py:41"
    }
  ]
}
```

- `answer` is the 0-based index into `choices`. The app shuffles choices, so position doesn't matter.
- Every `topic` must appear in `topics`. Topics show as tabs.
- `source` is the project name and short commit (`git rev-parse --short HEAD`), so it is clear when a deck might be stale.
- Progress is saved in the browser per card, keyed by the card's text. Rewording a card resets its progress. When updating a deck, leave good cards alone.

## About the app

Useful when the user asks how it works:

- **Flashcards** use five boxes: New, Learning, Familiar, Strong, Known. "Got it" moves a card up one box. "Missed it" sends it back to Learning and brings it back a few cards later. Rounds are 20 cards, weakest first.
- **Quiz** draws 10 random questions, marks answers in red pen, and keeps recent scores.
- **Keys:** Space flips, 1 and 2 are missed and got, A to D (or 1 to 4) pick a choice, Enter moves on.
- Several decks in one folder show as a list to pick from.
- Progress lives in the browser's localStorage for that URL. A different browser, or clearing site data, starts fresh. The fixed port keeps the URL stable between runs.
- To remove everything, delete the `.quiz-me` folder.
