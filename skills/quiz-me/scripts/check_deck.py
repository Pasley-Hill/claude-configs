#!/usr/bin/env python3
"""Check a quiz-me deck before serving it.

Errors (exit 1) break the app or the deck: bad JSON, missing fields, an answer
index out of range, repeated cards or choices.
Warnings point at weak content: refs that don't resolve, answers that give
themselves away, cards that are too long to recall quickly.

usage: check_deck.py <deck.json> [--root <project root>]
The root defaults to the folder that holds .quiz-me/.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

MIN_CHOICES = 2
MAX_CHOICES = 6
LONG_BACK = 400
LONGEST_IS_RIGHT_LIMIT = 0.5
REF_PATTERN = re.compile(r"^(?P<path>[^:]+?)(?::(?P<start>\d+)(?:-(?P<end>\d+))?)?$")
GIVEAWAY_PHRASES = ("all of the above", "none of the above", "both a and b")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, where: str, message: str) -> None:
        self.errors.append(f"{where}: {message}")

    def warn(self, where: str, message: str) -> None:
        self.warnings.append(f"{where}: {message}")


def text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def check_top(deck: dict, report: Report) -> list[str]:
    if not text(deck.get("title")):
        report.error("deck", "missing title")
    if not text(deck.get("about")):
        report.warn("deck", "missing about (one sentence on what the deck covers)")
    if not text(deck.get("source")):
        report.warn("deck", "missing source (repo name and short commit)")
    for key in ("cards", "questions"):
        if not isinstance(deck.get(key, []), list):
            report.error("deck", f"{key} must be a list")
    if not deck.get("cards") and not deck.get("questions"):
        report.error("deck", "no cards and no questions")
    topics = deck.get("topics", [])
    if not isinstance(topics, list) or not all(text(t) for t in topics):
        report.error("deck", "topics must be a list of names")
        return []
    return topics


def check_topic(item: dict, topics: list[str], where: str, report: Report) -> None:
    topic = item.get("topic")
    if not topics:
        return
    if topic not in topics:
        report.error(where, f"topic {topic!r} is not in the deck's topics list")


def check_ref(ref: object, root: Path, where: str, report: Report) -> None:
    if not text(ref):
        report.warn(where, "no ref; say where this is true so the learner can check")
        return
    match = REF_PATTERN.match(text(ref))
    if not match:
        report.warn(where, f"ref {ref!r} should look like path/to/file.py:42")
        return
    path = root / match.group("path")
    if not path.exists():
        report.warn(where, f"ref file not found: {match.group('path')}")
        return
    line = int(match.group("end") or match.group("start") or 0)
    if line and path.is_file() and line > count_lines(path):
        report.warn(where, f"ref line {line} is past the end of {match.group('path')}")


def count_lines(path: Path) -> int:
    try:
        return len(path.read_text(errors="replace").splitlines())
    except OSError:
        return 0


def check_card(card: object, index: int, topics: list[str], root: Path, report: Report) -> None:
    where = f"cards[{index}]"
    if not isinstance(card, dict):
        report.error(where, "must be an object")
        return
    if not text(card.get("front")):
        report.error(where, "missing front")
    if not text(card.get("back")):
        report.error(where, "missing back")
    if len(text(card.get("back"))) > LONG_BACK:
        report.warn(where, f"back is over {LONG_BACK} characters; split it or trim it")
    check_topic(card, topics, where, report)
    check_ref(card.get("ref"), root, where, report)


def check_question(question: object, index: int, topics: list[str], root: Path, report: Report) -> None:
    where = f"questions[{index}]"
    if not isinstance(question, dict):
        report.error(where, "must be an object")
        return
    if not text(question.get("ask")):
        report.error(where, "missing ask")
    if not text(question.get("why")):
        report.warn(where, "missing why (explain the right answer)")
    check_choices(question, where, report)
    check_topic(question, topics, where, report)
    check_ref(question.get("ref"), root, where, report)


def check_choices(question: dict, where: str, report: Report) -> None:
    choices = question.get("choices")
    if not isinstance(choices, list) or not all(text(c) for c in choices):
        report.error(where, "choices must be a list of non-empty strings")
        return
    if not MIN_CHOICES <= len(choices) <= MAX_CHOICES:
        report.error(where, f"needs {MIN_CHOICES} to {MAX_CHOICES} choices, has {len(choices)}")
    if len({c.strip().lower() for c in choices}) != len(choices):
        report.error(where, "two choices are the same")
    answer = question.get("answer")
    if not isinstance(answer, int) or isinstance(answer, bool) or not 0 <= answer < len(choices):
        report.error(where, f"answer must be a 0-based index into choices, got {answer!r}")
    if any(phrase in c.lower() for c in choices for phrase in GIVEAWAY_PHRASES):
        report.warn(where, "avoid 'all/none of the above'; choices get shuffled")


def answer_is_longest(question: dict) -> bool:
    choices = question.get("choices") or []
    answer = question.get("answer")
    if not isinstance(answer, int) or not 0 <= answer < len(choices):
        return False
    lengths = [len(str(c)) for c in choices]
    return lengths[answer] == max(lengths) and lengths.count(max(lengths)) == 1


def check_whole_deck(deck: dict, report: Report) -> None:
    cards = [c for c in deck.get("cards", []) if isinstance(c, dict)]
    questions = [q for q in deck.get("questions", []) if isinstance(q, dict)]
    for front, count in Counter(text(c.get("front")) for c in cards).items():
        if front and count > 1:
            report.error("cards", f"front used {count} times: {front[:60]!r}")
    for ask, count in Counter(text(q.get("ask")) for q in questions).items():
        if ask and count > 1:
            report.error("questions", f"ask used {count} times: {ask[:60]!r}")
    longest = sum(answer_is_longest(q) for q in questions)
    if len(questions) >= 5 and longest / len(questions) > LONGEST_IS_RIGHT_LIMIT:
        report.warn(
            "questions",
            f"the right answer is the longest choice in {longest} of {len(questions)}; "
            "even out choice lengths so length doesn't give it away",
        )
    for topic in deck.get("topics", []) if isinstance(deck.get("topics"), list) else []:
        if not any(item.get("topic") == topic for item in cards + questions):
            report.warn("topics", f"{topic!r} has no cards or questions")


def default_root(deck_path: Path) -> Path:
    for parent in deck_path.resolve().parents:
        if parent.name == ".quiz-me":
            return parent.parent
    return Path.cwd()


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a quiz-me deck.")
    parser.add_argument("deck", type=Path)
    parser.add_argument("--root", type=Path, help="project root that refs are relative to")
    args = parser.parse_args()

    try:
        deck = json.loads(args.deck.read_text())
    except (OSError, json.JSONDecodeError) as problem:
        print(f"error: can't read {args.deck}: {problem}")
        return 1
    if not isinstance(deck, dict):
        print("error: deck must be a JSON object")
        return 1

    root = (args.root or default_root(args.deck)).resolve()
    report = Report()
    topics = check_top(deck, report)
    for index, card in enumerate(deck.get("cards") or []):
        check_card(card, index, topics, root, report)
    for index, question in enumerate(deck.get("questions") or []):
        check_question(question, index, topics, root, report)
    check_whole_deck(deck, report)

    for line in report.errors:
        print(f"error: {line}")
    for line in report.warnings:
        print(f"warning: {line}")
    cards, questions = len(deck.get("cards") or []), len(deck.get("questions") or [])
    status = "FAILED" if report.errors else "ok"
    print(f"{status}: {cards} cards, {questions} questions, {len(topics)} topics, "
          f"{len(report.errors)} errors, {len(report.warnings)} warnings")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
