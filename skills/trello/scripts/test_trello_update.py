"""Offline tests for trello_update.py: no credentials, no network.

Every HTTP call goes through trello_update._request, which these tests replace
with a fake board. Run: python3 -m unittest discover -s skills/trello/scripts
"""
import importlib.util
import os
import sys
import unittest
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

HERE = Path(__file__).resolve().parent
os.environ.setdefault("TRELLO_API_KEY", "test-key")
os.environ.setdefault("TRELLO_TOKEN", "test-token")
os.environ["TRELLO_CREDENTIALS_FILE"] = os.devnull
_spec = importlib.util.spec_from_file_location("trello_update", HERE / "trello_update.py")
tu = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tu)

CHECKOUT = {"id": "a" * 24, "idShort": 12, "shortLink": "Zq3kP9xA", "name": "Fix checkout flow"}
OTHER = {"id": "b" * 24, "idShort": 13, "shortLink": "Lm8nB2cD", "name": "Photo report"}
LISTS = [{"id": "l1", "name": "Todo", "closed": False},
         {"id": "l2", "name": "✅ Done Week 3/9/2026", "closed": True}]


class FakeTrello:
    """Answers the few endpoints resolve_card and cmd_move touch."""

    def __init__(self):
        self.calls = []

    def __call__(self, method, path, params=None, json_body=None, retries=3, missing_ok=False):
        self.calls.append((method, path))
        if path.startswith("/cards/") and method == "GET":
            ref = path.split("/")[2]
            for c in (CHECKOUT, OTHER):
                if ref in (c["id"], c["shortLink"]):
                    return c
            if missing_ok:
                return None
            tu.die(f"GET {path} -> 404")
        if path.endswith("/cards/all") or path.endswith("/cards/open"):
            return [CHECKOUT, OTHER]
        if path.endswith("/lists"):
            return LISTS
        if method == "PUT":
            return {}
        raise AssertionError(f"unexpected call {method} {path}")


class ResolveCardTest(unittest.TestCase):
    def setUp(self):
        self.api = FakeTrello()
        patcher = mock.patch.object(tu, "_request", self.api)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_eight_letter_name_falls_back_to_name_search(self):
        self.assertEqual(tu.resolve_card("checkout")["id"], CHECKOUT["id"])
        self.assertIn(("GET", "/cards/checkout"), self.api.calls)

    def test_real_short_link_is_fetched_directly(self):
        self.assertEqual(tu.resolve_card("Lm8nB2cD")["id"], OTHER["id"])
        self.assertEqual(self.api.calls, [("GET", "/cards/Lm8nB2cD")])

    def test_short_link_from_url(self):
        card = tu.resolve_card("https://trello.com/c/Zq3kP9xA/12-fix-checkout-flow")
        self.assertEqual(card["id"], CHECKOUT["id"])

    def test_short_id(self):
        self.assertEqual(tu.resolve_card("#13")["id"], OTHER["id"])

    def test_unknown_eight_letter_word_fails_with_name_error(self):
        with mock.patch.object(tu, "die", side_effect=SystemExit) as die:
            with self.assertRaises(SystemExit):
                tu.resolve_card("nothings")
        self.assertIn("No card matching 'nothings'", die.call_args[0][0])


class MoveTest(unittest.TestCase):
    def setUp(self):
        self.api = FakeTrello()
        patcher = mock.patch.object(tu, "_request", self.api)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _move(self, to):
        tu.cmd_move(SimpleNamespace(card="#12", to=to, top=False, bottom=False, comment=None))

    def test_move_to_archived_list_is_refused(self):
        with mock.patch.object(tu, "die", side_effect=SystemExit) as die:
            with self.assertRaises(SystemExit):
                self._move("Done Week 3/9")
        self.assertIn("archived", die.call_args[0][0])
        self.assertFalse([c for c in self.api.calls if c[0] == "PUT"])

    def test_move_to_open_list(self):
        with mock.patch("builtins.print"):
            self._move("Todo")
        self.assertIn(("PUT", f"/cards/{CHECKOUT['id']}"), self.api.calls)


class RequestMissingOkTest(unittest.TestCase):
    def test_404_returns_none_only_when_missing_ok(self):
        err = urllib.error.HTTPError("u", 404, "Not Found", {}, None)
        err.read = lambda: b"not found"
        with mock.patch("urllib.request.urlopen", side_effect=err):
            self.assertIsNone(tu._request("GET", "/cards/x", missing_ok=True))
            with mock.patch.object(tu, "die", side_effect=SystemExit):
                with self.assertRaises(SystemExit):
                    tu._request("GET", "/cards/x")


if __name__ == "__main__":
    unittest.main()
