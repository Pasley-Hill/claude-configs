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
BOARDS = [
    {"id": "c" * 24, "shortLink": "JEcYPEdW", "name": "Redline OS", "organization": {"displayName": "Redline"}},
    {"id": "d" * 24, "shortLink": "t7CdxreR", "name": "Autoturn.ai Wholesale", "organization": None},
    {"id": "e" * 24, "shortLink": "Qq1Ww2Ee", "name": "Redline QA", "organization": {"displayName": "Redline"}},
]
COMMENTS = [  # newest first, as Trello returns them
    {"id": "c3", "idMemberCreator": "someone", "date": "2026-10-15T10:00:00Z", "data": {"text": "not mine"}},
    {"id": "c2", "idMemberCreator": "me", "date": "2026-10-14T10:00:00Z", "data": {"text": "deployed to staging"}},
    {"id": "c1", "idMemberCreator": "me", "date": "2026-10-13T10:00:00Z", "data": {"text": "started on it"}},
]
LISTS = [{"id": "l1", "name": "Todo", "closed": False},
         {"id": "l2", "name": "✅ Done Week 3/9/2026", "closed": True}]


class FakeTrello:
    """Answers the few endpoints resolve_card and cmd_move touch."""

    def __init__(self):
        self.calls = []

    def __call__(self, method, path, params=None, json_body=None, retries=3, missing_ok=False):
        self.calls.append((method, path))
        if path.endswith("/actions") and method == "GET":
            return COMMENTS
        if path.startswith("/cards/") and method == "GET":
            ref = path.split("/")[2]
            for c in (CHECKOUT, OTHER):
                if ref in (c["id"], c["shortLink"]):
                    return c
            if missing_ok:
                return None
            tu.die(f"GET {path} -> 404")
        if path == "/members/me/boards":
            return BOARDS
        if path == "/members/me":
            return {"id": "me"}
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


class BoardSelectionTest(unittest.TestCase):
    def setUp(self):
        self.api = FakeTrello()
        patcher = mock.patch.object(tu, "_request", self.api)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(setattr, tu, "BOARD_ID", tu.BOARD_ID)
        self.addCleanup(setattr, tu, "_BOARD_OVERRIDE", tu._BOARD_OVERRIDE)

    def _pick(self, override="", default=""):
        tu._BOARD_OVERRIDE, tu.BOARD_ID = override, default
        tu.require_board()
        return tu.BOARD_ID

    def _pick_fails(self, override="", default=""):
        with mock.patch.object(tu, "die", side_effect=SystemExit) as die:
            with self.assertRaises(SystemExit):
                self._pick(override, default)
        return die.call_args[0][0]

    def test_override_by_short_id(self):
        self.assertEqual(self._pick("t7CdxreR"), "t7CdxreR")

    def test_override_by_name_part(self):
        self.assertEqual(self._pick("autoturn"), "t7CdxreR")

    def test_override_by_exact_name_beats_substring(self):
        self.assertEqual(self._pick("redline os"), "JEcYPEdW")

    def test_override_wins_over_default(self):
        self.assertEqual(self._pick("autoturn", default="JEcYPEdW"), "t7CdxreR")

    def test_default_used_without_override(self):
        self.assertEqual(self._pick(default="JEcYPEdW"), "JEcYPEdW")
        self.assertEqual(self.api.calls, [])

    def test_ambiguous_override_lists_only_the_matches(self):
        msg = self._pick_fails("redline")
        self.assertIn("matches several boards", msg)
        self.assertIn("Qq1Ww2Ee", msg)
        self.assertNotIn("t7CdxreR", msg)

    def test_unknown_override_lists_every_board(self):
        msg = self._pick_fails("nope")
        self.assertIn("matches none of your boards", msg)
        self.assertIn("t7CdxreR", msg)

    def test_no_board_explains_how_to_set_one(self):
        msg = self._pick_fails()
        self.assertIn("No Trello board chosen", msg)
        self.assertIn("TRELLO_BOARD_ID=JEcYPEdW", msg)
        self.assertIn(str(tu.CREDENTIALS_FILE), msg)
        self.assertIn("TRELLO_BOARD=JEcYPEdW", msg)


class SetupHelpTest(unittest.TestCase):
    def test_setup_help_has_the_trello_clicks_and_save_commands(self):
        for needle in ("https://trello.com/power-ups/admin", '"New"', "Generate a new API key",
                       '"Token"', '"Allow"', "chmod 600", "boards"):
            self.assertIn(needle, tu.SETUP_HELP)

    def test_missing_credentials_stop_every_command(self):
        with mock.patch.dict(tu.AUTH, {"key": "", "token": ""}), \
             mock.patch.object(sys, "argv", ["trello_update.py", "board"]), \
             mock.patch.object(tu, "die", side_effect=SystemExit) as die:
            with self.assertRaises(SystemExit):
                tu.main()
        self.assertEqual(die.call_args[0][0], tu.SETUP_HELP)


class EditCommentTest(unittest.TestCase):
    def setUp(self):
        self.api = FakeTrello()
        patcher = mock.patch.object(tu, "_request", self.api)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _edit(self, **kw):
        args = SimpleNamespace(card="#12", id=None, match=None, set=None, replace=None)
        for k, v in kw.items():
            setattr(args, k, v)
        with mock.patch("builtins.print"):
            tu.cmd_edit_comment(args)
        return [c for c in self.api.calls if c[0] == "PUT"]

    def test_defaults_to_my_newest_comment_not_someone_elses(self):
        self.assertEqual(self._edit(set="x"), [("PUT", "/actions/c2/text")])

    def test_by_id(self):
        self.assertEqual(self._edit(id="c1", set="x"), [("PUT", "/actions/c1/text")])

    def test_by_match(self):
        self.assertEqual(self._edit(match="started", set="x"), [("PUT", "/actions/c1/text")])

    def test_replace_text_missing_is_refused(self):
        with mock.patch.object(tu, "die", side_effect=SystemExit):
            with self.assertRaises(SystemExit):
                self._edit(replace=("nope", "x"))
        self.assertFalse([c for c in self.api.calls if c[0] == "PUT"])

    def test_someone_elses_comment_id_is_refused(self):
        with mock.patch.object(tu, "die", side_effect=SystemExit):
            with self.assertRaises(SystemExit):
                self._edit(id="c3", set="x")


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
