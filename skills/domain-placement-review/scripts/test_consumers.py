from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("consumers", HERE / "consumers.py")
consumers = importlib.util.module_from_spec(_spec)
sys.modules["consumers"] = consumers
_spec.loader.exec_module(consumers)

CONFIG = {
    "shared": ["app/shared"],
    "domains": ["app/*"],
    "roots": ["app/server.ts"],
    "compositionRoots": ["app/shared/wiring.ts"],
    "urlRoots": {"/js/": ["app/*/js", "app/shared/js"]},
    "references": [
        {"targets": "app/*/layouts/*.html", "pattern": r"include\(\s*['\"]{stem}['\"]"},
        {"targets": "app/*/views/_*.html", "pattern": r"include\(\s*['\"]{stem}['\"]"},
    ],
    "justified": [{"path": "app/shared/platform/**", "why": "platform"}],
}


class Repo:
    def __init__(self, files: dict[str, str]):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)
        self.git("init", "-q", "-b", "main")
        self.commit(files)

    def git(self, *args: str) -> str:
        done = subprocess.run(
            ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
            cwd=self.path, capture_output=True, text=True, check=True,
        )
        return done.stdout.strip()

    def commit(self, files: dict[str, str | None]) -> str:
        for name, body in files.items():
            file = self.path / name
            if body is None:
                file.unlink()
                continue
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(body)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "change")
        return self.git("rev-parse", "HEAD")

    def run(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = consumers.main([*argv, "--repo", str(self.path)])
        return code, out.getvalue()

    def census(self, ref: str = "HEAD") -> dict[str, dict]:
        code, out = self.run("census", "--ref", ref, "--json", "--unit", "export")
        self.assert_ok(code)
        return {row["path"]: row for row in json.loads(out)["rows"]}

    @staticmethod
    def assert_ok(code: int) -> None:
        if code != 0:
            raise AssertionError(f"exit {code}")

    def close(self) -> None:
        self.tmp.cleanup()


def js_repo(extra: dict[str, str] | None = None) -> Repo:
    files = {
        ".claude/domain-placement.json": json.dumps(CONFIG),
        "app/server.ts": "import { boot } from './shared/boot.ts';\n",
        "app/shared/boot.ts": "export function boot() {}\n",
        "app/shared/both.ts": "export function both() {}\nexport function lonely() {}\n",
        "app/shared/only-admin.ts": "export const x = 1;\n",
        "app/shared/unused.ts": "export const y = 1;\n",
        "app/shared/kernel.ts": "import { inner } from './inner.ts';\nexport const k = inner;\n",
        "app/shared/inner.ts": "export const inner = 1;\n",
        "app/shared/job.ts": "export function job() {}\n",
        "app/shared/wiring.ts": "import { job } from './job.ts';\nimport { a } from '../admin/a.ts';\n",
        "app/shared/platform/helper-user.ts": "import { h } from '../helper.ts';\n",
        "app/shared/helper.ts": "export const h = 1;\n",
        "app/shared/js/widget.mjs": "export function widget() {}\n",
        "app/shared/layouts/_card.html": "<div></div>\n",
        "app/admin/a.ts": (
            "import {\n\tboth,\n// a comment with a `tick` and 'quote'\n} from '../shared/both.ts';\n"
            "import { x } from '../shared/only-admin.ts';\nimport { k } from '../shared/kernel.ts';\n"
        ),
        "app/admin/js/page.mjs": "import { widget } from './widget.mjs';\n",
        "app/admin/views/page.html": "<%~ include('_card', it) %>\n",
        "app/dealer/d.ts": "import { both } from '../shared/both.ts';\nimport { k } from '../shared/kernel.ts';\n",
        "app/dealer/views/page.html": "<%~ include('_card', it) %>\n",
        "test/a.test.mjs": "import { y } from '../app/shared/unused.ts';\n",
    }
    files.update(extra or {})
    return Repo(files)


class CensusTest(unittest.TestCase):
    def setUp(self):
        self.repo = js_repo()
        self.rows = self.repo.census()

    def tearDown(self):
        self.repo.close()

    def test_two_domains_is_shared(self):
        self.assertEqual(self.rows["app/shared/both.ts"]["status"], "SHARED")
        self.assertEqual(sorted(self.rows["app/shared/both.ts"]["domains"]), ["admin", "dealer"])

    def test_comment_inside_import_braces_still_counts(self):
        self.assertIn("admin", self.rows["app/shared/both.ts"]["domains"])

    def test_one_domain_is_single_with_a_home(self):
        row = self.rows["app/shared/only-admin.ts"]
        self.assertEqual(row["status"], "SINGLE")
        self.assertEqual(row["move_to"], "app/admin/")

    def test_tests_do_not_count(self):
        self.assertEqual(self.rows["app/shared/unused.ts"]["status"], "NONE")

    def test_file_only_a_shared_hub_imports_is_kept_not_shared(self):
        row = self.rows["app/shared/inner.ts"]
        self.assertEqual(row["status"], "KEEP")
        self.assertEqual(row["kept_by"], ["app/shared/kernel.ts"])
        self.assertEqual(row["domains"], {})

    def test_composition_root_is_not_a_consumer(self):
        row = self.rows["app/shared/job.ts"]
        self.assertEqual(row["status"], "NONE")
        self.assertTrue(row["wiring"][0].startswith("app/shared/wiring.ts"))

    def test_entry_point_makes_root(self):
        self.assertEqual(self.rows["app/shared/boot.ts"]["status"], "ROOT")

    def test_justified_glob(self):
        self.assertEqual(self.rows["app/shared/platform/helper-user.ts"]["status"], "JUSTIFIED")

    def test_file_only_a_justified_file_needs_is_kept(self):
        row = self.rows["app/shared/helper.ts"]
        self.assertEqual(row["status"], "KEEP")
        self.assertIn("helper-user.ts", row["why"])

    def test_url_root_resolves_client_import_to_shared_js(self):
        self.assertEqual(self.rows["app/shared/js/widget.mjs"]["domains"], {"admin": "app/admin/js/page.mjs:1"})

    def test_reference_pattern_counts_template_includes(self):
        self.assertEqual(self.rows["app/shared/layouts/_card.html"]["status"], "SHARED")

    def test_exports_used_by_one_domain_are_listed(self):
        exports = self.rows["app/shared/both.ts"]["exports"]
        self.assertEqual(exports["both"], ["admin", "dealer"])
        self.assertEqual(exports["lonely"], [])

    def test_scope_limits_rows(self):
        code, out = self.repo.run("census", "--scope", "app/shared/js", "--json")
        self.assertEqual(code, 0)
        self.assertEqual([r["path"] for r in json.loads(out)["rows"]], ["app/shared/js/widget.mjs"])


class DiffTest(unittest.TestCase):
    def setUp(self):
        self.repo = js_repo()
        self.base = self.repo.git("rev-parse", "HEAD")

    def tearDown(self):
        self.repo.close()

    def diff(self, head: str = "HEAD") -> tuple[int, list[dict]]:
        code, out = self.repo.run("diff", "--base", self.base, "--head", head, "--json")
        return code, json.loads(out)["findings"]

    def test_clean_change_passes(self):
        self.repo.commit({"app/admin/a.ts": "import { both } from '../shared/both.ts';\nimport { k } from '../shared/kernel.ts';\nimport { x } from '../shared/only-admin.ts';\n"})
        code, findings = self.diff()
        self.assertEqual((code, findings), (0, []))

    def test_new_shared_file_with_one_consumer_fails(self):
        self.repo.commit({
            "app/shared/new.ts": "export const n = 1;\n",
            "app/dealer/e.ts": "import { n } from '../shared/new.ts';\n",
        })
        code, findings = self.diff()
        self.assertEqual(code, 1)
        self.assertEqual([(f["kind"], f["path"]) for f in findings], [("NEW_SINGLE", "app/shared/new.ts")])

    def test_removing_the_second_consumer_fails_in_that_change(self):
        self.repo.commit({"app/dealer/d.ts": "import { k } from '../shared/kernel.ts';\n"})
        code, findings = self.diff()
        self.assertEqual(code, 1)
        self.assertEqual(findings[0]["kind"], "LOST_SECOND")
        self.assertIn("dropped: dealer", findings[0]["detail"])
        self.assertIn("app/dealer/d.ts", findings[0]["detail"])

    def test_new_import_between_domains_fails(self):
        self.repo.commit({"app/dealer/f.ts": "import { x } from '../admin/a.ts';\n"})
        code, findings = self.diff()
        self.assertEqual(code, 1)
        self.assertEqual(findings[0]["kind"], "CROSS")

    def test_moving_a_single_owner_file_out_of_shared_passes(self):
        self.repo.git("mv", "app/shared/only-admin.ts", "app/admin/only-admin.ts")
        self.repo.commit({"app/admin/a.ts": "import { both } from '../shared/both.ts';\nimport { x } from './only-admin.ts';\nimport { k } from '../shared/kernel.ts';\n"})
        code, findings = self.diff()
        self.assertEqual((code, findings), (0, []))

    def test_editing_existing_debt_is_a_question(self):
        self.repo.commit({"app/shared/only-admin.ts": "export const x = 2;\n"})
        code, findings = self.diff()
        self.assertEqual(code, 0)
        self.assertEqual([(f["kind"], f["blocking"]) for f in findings], [("TOUCHED_DEBT", False)])

    def test_new_justified_entry_is_a_question(self):
        config = dict(CONFIG, justified=[*CONFIG["justified"], {"path": "app/shared/only-admin.ts", "why": "trust me"}])
        self.repo.commit({".claude/domain-placement.json": json.dumps(config)})
        code, findings = self.diff()
        self.assertEqual(code, 0)
        self.assertEqual([f["kind"] for f in findings], ["RULES_EDITED", "NEW_JUSTIFIED"])

    def test_a_justified_line_added_by_the_change_turns_a_block_into_a_question(self):
        config = dict(CONFIG, justified=[{"path": "app/shared/**", "why": "everything"}])
        self.repo.commit({
            ".claude/domain-placement.json": json.dumps(config),
            "app/shared/new.ts": "export const n = 1;\n",
            "app/dealer/e.ts": "import { n } from '../shared/new.ts';\n",
        })
        code, findings = self.diff()
        self.assertEqual(code, 0)
        self.assertIn("NEW_JUSTIFIED", [f["kind"] for f in findings])
        self.assertIn("NEW_SINGLE turned into a decision", " ".join(f["detail"] for f in findings))

    def test_working_tree_head(self):
        (self.repo.path / "app/shared/new.ts").write_text("export const n = 1;\n")
        (self.repo.path / "app/dealer/e.ts").write_text("import { n } from '../shared/new.ts';\n")
        code, findings = self.diff(".")
        self.assertEqual(code, 1)
        self.assertEqual(findings[0]["kind"], "NEW_SINGLE")


class EdgeCaseTest(unittest.TestCase):
    def setUp(self):
        self.repo = js_repo()
        self.base = self.repo.git("rev-parse", "HEAD")

    def tearDown(self):
        self.repo.close()

    def kinds(self, files: dict[str, str | None]) -> list[str]:
        self.repo.commit(files)
        _, out = self.repo.run("diff", "--base", self.base, "--head", "HEAD", "--json")
        return [f["kind"] for f in json.loads(out)["findings"]]

    def test_unused_reexport_is_not_a_consumer(self):
        kinds = self.kinds({
            "app/shared/new.ts": "export const n = 1;\n",
            "app/dealer/e.ts": "import { n } from '../shared/new.ts';\n",
            "app/admin/b.ts": "export { n } from '../shared/new.ts';\n",
        })
        self.assertEqual(kinds, ["NEW_SINGLE"])

    def test_barrel_passes_only_the_names_a_domain_imports(self):
        kinds = self.kinds({
            "app/shared/new.ts": "export const n = 1;\n",
            "app/shared/index.ts": "export * from './new.ts';\nexport * from './both.ts';\n",
            "app/dealer/e.ts": "import { n } from '../shared/index.ts';\n",
            "app/admin/b.ts": "import { both } from '../shared/index.ts';\n",
        })
        self.assertEqual(kinds, ["NEW_SINGLE"])

    def test_strings_and_trailing_comments_are_not_imports(self):
        kinds = self.kinds({
            "app/shared/new.ts": "export const n = 1;\n",
            "app/dealer/e.ts": "import { n } from '../shared/new.ts';\n",
            "app/admin/b.ts": "const s = \"import('../shared/new.ts')\"; // import('../shared/new.ts')\n",
        })
        self.assertEqual(kinds, ["NEW_SINGLE"])

    def test_commented_template_include_is_not_a_consumer(self):
        kinds = self.kinds({
            "app/shared/layouts/_new.html": "<p></p>\n",
            "app/dealer/views/q.html": "<%~ include('_new') %>\n",
            "app/admin/views/q.html": "<%/* include('_new') */%>\n<!-- include('_new') -->\n",
        })
        self.assertEqual(kinds, ["NEW_SINGLE"])

    def test_layout_behind_a_hub_belongs_to_the_export_that_uses_it(self):
        kinds = self.kinds({
            "app/shared/render.ts": (
                "export function renderPage() { return include('_card'); }\n"
                "export function renderPhoto() { return include('_photo'); }\n"
            ),
            "app/shared/layouts/_photo.html": "<p></p>\n",
            "app/admin/r.ts": "import { renderPage } from '../shared/render.ts';\n",
            "app/dealer/r.ts": "import { renderPage, renderPhoto } from '../shared/render.ts';\n",
        })
        self.assertEqual(kinds, ["NEW_SINGLE"])

    def test_moving_client_js_out_while_another_domain_loads_it_is_cross(self):
        (self.repo.path / "app/dealer/js").mkdir(parents=True)
        self.repo.git("mv", "app/shared/js/widget.mjs", "app/dealer/js/widget.mjs")
        self.assertEqual(self.kinds({}), ["CROSS"])

    def test_moving_a_partial_out_while_another_domain_includes_it_is_cross(self):
        self.repo.git("mv", "app/shared/layouts/_card.html", "app/dealer/views/_card.html")
        self.assertEqual(self.kinds({}), ["CROSS"])

    def test_same_url_twice_is_a_clash(self):
        kinds = self.kinds({"app/dealer/js/widget.mjs": "export function widget() {}\n"})
        self.assertIn("CLASH", kinds)

    def test_path_alias_counts_as_an_import(self):
        kinds = self.kinds({
            "tsconfig.json": '{\n  // aliases\n  "compilerOptions": {"baseUrl": ".", "paths": {"@shared/*": ["app/shared/*"], "@dealer/*": ["app/dealer/*"],},},\n}\n',
            "app/shared/new.ts": "export const n = 1;\n",
            "app/dealer/e.ts": "import { n } from '@shared/new.ts';\n",
            "app/admin/b.ts": "import { n } from '@shared/new';\nimport { both } from '@dealer/d.ts';\n",
        })
        self.assertEqual(kinds, ["CROSS"])

    def test_shared_file_left_only_to_the_entry_point_is_a_question(self):
        self.repo.commit({"app/server.ts": "import { boot } from './shared/boot.ts';\nimport { both } from './shared/both.ts';\n"})
        self.base = self.repo.git("rev-parse", "HEAD")
        kinds = self.kinds({
            "app/admin/a.ts": "import { x } from '../shared/only-admin.ts';\nimport { k } from '../shared/kernel.ts';\n",
            "app/dealer/d.ts": "import { k } from '../shared/kernel.ts';\n",
        })
        self.assertEqual(kinds, ["NOW_ROOT"])

    def test_editing_the_rules_is_a_question(self):
        kinds = self.kinds({".claude/domain-placement.json": json.dumps(dict(CONFIG, unit="file"))})
        self.assertEqual(kinds, ["RULES_EDITED"])

    def test_merged_head_warns(self):
        _, out = self.repo.run("diff", "--base", "HEAD", "--head", "HEAD~0")
        self.assertIn("WARNING", out)


class HubTest(unittest.TestCase):
    def census(self, render: str, admin: str, dealer: str) -> dict:
        repo = Repo({
            ".claude/domain-placement.json": json.dumps(CONFIG),
            "app/shared/layouts/_photo.html": "<p></p>\n",
            "app/shared/render.ts": render,
            "app/admin/a.ts": admin,
            "app/dealer/d.ts": dealer,
        })
        try:
            return repo.census()["app/shared/layouts/_photo.html"]
        finally:
            repo.close()

    def test_private_helper_belongs_to_the_exports_that_call_it(self):
        row = self.census(
            "function wrap(v) { return include('_photo'); }\nexport function a() { return wrap(); }\n"
            "export function b() { return wrap(); }\nexport function c() {}\n",
            "import { c } from '../shared/render.ts';\n",
            "import { a, b, c } from '../shared/render.ts';\n",
        )
        self.assertEqual((row["status"], list(row["domains"])), ("SINGLE", ["dealer"]))

    def test_helper_called_from_two_domains_exports_is_shared(self):
        row = self.census(
            "function wrap(v) { return include('_photo'); }\nexport function a() { return wrap(); }\n"
            "export function b() { return wrap(); }\n",
            "import { a } from '../shared/render.ts';\n",
            "import { b } from '../shared/render.ts';\n",
        )
        self.assertEqual(row["status"], "SHARED")

    def test_module_level_code_keeps_it(self):
        row = self.census(
            "export function a() { return 1; }\ninclude('_photo');\n",
            "import { a } from '../shared/render.ts';\n",
            "import { a } from '../shared/render.ts';\n",
        )
        self.assertEqual(row["status"], "KEEP")

    def test_arrow_function_export(self):
        row = self.census(
            "export const a = () => 1;\nexport const photo = (v) =>\n\tinclude('_photo');\n",
            "import { a } from '../shared/render.ts';\n",
            "import { a, photo } from '../shared/render.ts';\n",
        )
        self.assertEqual((row["status"], list(row["domains"])), ("SINGLE", ["dealer"]))


class MoreDiffTest(unittest.TestCase):
    def setUp(self):
        self.repo = js_repo()
        self.base = self.repo.git("rev-parse", "HEAD")

    def tearDown(self):
        self.repo.close()

    def kinds(self, head: str = "HEAD") -> list[str]:
        _, out = self.repo.run("diff", "--base", self.base, "--head", head, "--json")
        return [f["kind"] for f in json.loads(out)["findings"]]

    def test_shared_code_importing_a_domain_is_upward(self):
        self.repo.commit({"app/shared/both.ts": "import { a } from '../admin/a.ts';\nexport function both() {}\n"})
        self.assertEqual(self.kinds(), ["UPWARD"])

    def test_inlining_a_hub_helper_is_not_a_block(self):
        self.repo.commit({
            "app/shared/render.ts": "function wrap() { return include('_card'); }\nexport function card() { return wrap(); }\n",
            "app/admin/r.ts": "import { card } from '../shared/render.ts';\n",
            "app/dealer/r.ts": "import { card } from '../shared/render.ts';\n",
        })
        self.base = self.repo.git("rev-parse", "HEAD")
        self.repo.commit({"app/shared/render.ts": "export function card() { return include('_card'); }\n"})
        self.assertEqual(self.kinds(), [])

    def test_stale_branch_compares_with_its_merge_base(self):
        self.repo.git("branch", "feature")
        self.repo.commit({"app/dealer/x.ts": "import { x } from '../shared/only-admin.ts';\n"})
        main = self.repo.git("rev-parse", "HEAD")
        self.repo.git("checkout", "-q", "feature")
        (self.repo.path / "app/admin/new.ts").write_text("export const n = 1;\n")
        _, out = self.repo.run("diff", "--base", main, "--head", ".", "--json")
        self.assertEqual(json.loads(out)["findings"], [])

    def test_python_decorated_helper(self):
        repo = Repo({
            ".claude/domain-placement.json": json.dumps({"shared": ["pkg/shared"], "domains": ["pkg/*"]}),
            "pkg/shared/hub.py": (
                "import functools\n\n@functools.cache\ndef _load():\n    from . import heavy\n    return heavy\n\n"
                "def billing_only():\n    return _load()\n\ndef common():\n    return 1\n"
            ),
            "pkg/shared/heavy.py": "X = 1\n",
            "pkg/billing/v.py": "from pkg.shared.hub import billing_only, common\n",
            "pkg/orders/v.py": "from pkg.shared.hub import common\n",
        })
        row = repo.census()["pkg/shared/heavy.py"]
        repo.close()
        self.assertEqual((row["status"], list(row["domains"])), ("SINGLE", ["billing"]))


class WorklistTest(unittest.TestCase):
    def setUp(self):
        config = dict(
            CONFIG,
            justified=[*CONFIG["justified"], {"path": "app/shared/both.ts", "why": "kept on purpose"}],
            planned=[
                {"path": "app/shared/only-admin.ts", "ticket": "#9", "to": "app/admin/"},
                {"path": "app/shared/gone.ts", "ticket": "#9", "to": "app/admin/"},
            ],
        )
        self.repo = js_repo({".claude/domain-placement.json": json.dumps(config)})

    def tearDown(self):
        self.repo.close()

    def test_strict_fails_while_violations_remain(self):
        code, out = self.repo.run("census", "--strict")
        self.assertEqual(code, 1)
        self.assertIn("STRICT: 5 violation(s)", out)

    def test_strict_passes_on_a_clean_scope(self):
        code, _ = self.repo.run("census", "--strict", "--scope", "app/shared/js")
        self.assertEqual(code, 1)
        code, _ = self.repo.run("census", "--strict", "--scope", "app/shared/layouts")
        self.assertEqual(code, 0)

    def test_planned_rows_name_their_ticket(self):
        code, out = self.repo.run("census", "--ticket", "#9")
        self.assertEqual(code, 0)
        self.assertIn("SINGLE app/shared/only-admin.ts", out)
        self.assertIn("planned in #9: app/admin/", out)
        self.assertNotIn("unused.ts", out)

    def test_a_finished_plan_warns(self):
        _, out = self.repo.run("census")
        self.assertIn("planned entry matches no shared file, done? remove it: app/shared/gone.ts (#9)", out)

    def test_justified_row_shows_what_it_would_be(self):
        row = self.repo.census()["app/shared/both.ts"]
        self.assertEqual((row["status"], row["would_be"]), ("JUSTIFIED", "SHARED"))

    def test_justified_file_losing_its_second_user_is_a_question(self):
        base = self.repo.git("rev-parse", "HEAD")
        self.repo.commit({"app/dealer/d.ts": "import { k } from '../shared/kernel.ts';\n"})
        code, out = self.repo.run("diff", "--base", base, "--head", "HEAD", "--json")
        findings = json.loads(out)["findings"]
        self.assertEqual(code, 0)
        self.assertEqual([f["kind"] for f in findings], ["JUSTIFIED_LOST"])

    def test_glob_scope(self):
        _, out = self.repo.run("census", "--scope", "app/shared/*.ts", "--json")
        paths = [r["path"] for r in json.loads(out)["rows"]]
        self.assertIn("app/shared/only-admin.ts", paths)
        self.assertNotIn("app/shared/js/widget.mjs", paths)

    def test_browser_module_moves_to_the_domain_js_folder(self):
        row = self.repo.census()["app/shared/js/widget.mjs"]
        self.assertEqual(row["move_to"], "app/admin/js/")

    def test_new_file_only_the_entry_point_uses_blocks(self):
        base = self.repo.git("rev-parse", "HEAD")
        self.repo.commit({
            "app/shared/boot2.ts": "export const b = 1;\n",
            "app/server.ts": "import { boot } from './shared/boot.ts';\nimport { b } from './shared/boot2.ts';\n",
        })
        code, out = self.repo.run("diff", "--base", base, "--head", "HEAD", "--json")
        self.assertEqual(code, 1)
        self.assertEqual([f["kind"] for f in json.loads(out)["findings"]], ["NEW_ROOT"])


class PythonBarrelTest(unittest.TestCase):
    def test_package_init_reexport_is_followed_by_name(self):
        repo = Repo({
            ".claude/domain-placement.json": json.dumps({"shared": ["pkg/shared"], "domains": ["pkg/*"]}),
            "pkg/__init__.py": "",
            "pkg/shared/__init__.py": "from .dates import today\n",
            "pkg/shared/dates.py": "def today():\n    pass\n",
            "pkg/billing/views.py": "from pkg.shared import today\n",
            "pkg/orders/views.py": "from pkg.shared import today\n",
        })
        base = repo.git("rev-parse", "HEAD")
        repo.commit({
            "pkg/shared/__init__.py": "from .dates import today\nfrom .tax import rate\n",
            "pkg/shared/tax.py": "def rate():\n    pass\n",
            "pkg/billing/views.py": "from pkg.shared import today, rate\n",
        })
        _, out = repo.run("diff", "--base", base, "--head", "HEAD", "--json")
        repo.close()
        found = [(f["kind"], f["path"]) for f in json.loads(out)["findings"]]
        self.assertEqual(found, [("NEW_SINGLE", "pkg/shared/tax.py")])


class InferenceTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repo({
            "main.py": "from routes import low_inventory\n",
            "routes/__init__.py": "",
            "routes/low_inventory.py": "from services.utils.cache import CacheManager\nfrom services.low_inventory_service import run\n",
            "routes/pricing.py": "from services.utils import (\n    formatters,\n)\n",
            "services/__init__.py": "",
            "services/low_inventory_service.py": "from .utils.cache import CacheManager\nfrom services.utils.grouping import group\n\ndef run():\n    pass\n",
            "services/pricing_service.py": "from services.utils.cache import CacheManager\n",
            "services/utils/__init__.py": "",
            "services/utils/cache.py": "class CacheManager:\n    pass\n",
            "services/utils/grouping.py": "def group():\n    pass\n",
            "services/utils/formatters.py": "def money():\n    pass\n",
            "tests/test_cache.py": "from services.utils.formatters import money\n",
        })
        self.rows = self.repo.census()

    def tearDown(self):
        self.repo.close()

    def test_layout_is_inferred(self):
        code, out = self.repo.run("layout")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["config"], "inferred")
        self.assertEqual(data["effective"]["shared"], ["services/utils"])

    def test_layer_files_of_one_feature_are_one_domain(self):
        self.assertEqual(self.rows["services/utils/grouping.py"]["status"], "SINGLE")
        self.assertEqual(list(self.rows["services/utils/grouping.py"]["domains"]), ["low_inventory"])

    def test_two_features_share(self):
        self.assertEqual(sorted(self.rows["services/utils/cache.py"]["domains"]), ["low_inventory", "pricing"])

    def test_from_package_import_submodule(self):
        self.assertEqual(list(self.rows["services/utils/formatters.py"]["domains"]), ["pricing"])


if __name__ == "__main__":
    unittest.main()
