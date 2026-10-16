#!/usr/bin/env python3
from __future__ import annotations

import argparse
import bisect
import json
import posixpath
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from pathlib import Path

CONFIG_PATH = ".claude/domain-placement.json"
JS_EXT = (".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs")
PY_EXT = (".py",)
MARKUP_EXT = (
    ".html", ".htm", ".eta", ".ejs", ".hbs", ".njk", ".jinja", ".jinja2", ".j2",
    ".vue", ".svelte", ".astro", ".erb",
)
SCANNED_EXT = JS_EXT + PY_EXT + MARKUP_EXT
UNPARSED_EXT = (".dart", ".go", ".rb", ".java", ".kt", ".swift", ".php", ".rs", ".cs", ".scala", ".ex", ".exs")
RESOLVE_ORDER = (".ts", ".tsx", ".mts", ".js", ".mjs", ".jsx", ".cjs", ".cts", ".d.ts")
JS_SWAP = {".js": (".ts", ".tsx"), ".mjs": (".mts",), ".cjs": (".cts",), ".jsx": (".tsx",)}
SHARED_NAMES = ("shared", "common", "commons", "core", "kernel", "lib", "libs", "utils", "util", "helpers")
LAYER_NAMES = {
    "routes", "route", "routers", "services", "service", "views", "view", "pages", "components",
    "models", "controllers", "handlers", "api", "middleware", "middlewares", "static", "templates",
    "schemas", "hooks", "store", "stores", "types", "assets", "styles", "public", "config", "db",
    "repositories", "workers", "jobs", "tasks", "js", "css", *SHARED_NAMES,
}
FEATURE_PARENTS = ("app", "apps", "features", "modules", "domains", "packages")
LAYER_SUFFIXES = (
    "_service", "_services", "_routes", "_route", "_router", "_controller", "_controllers",
    "_api", "_views", "_view", "_handler", "_handlers", "_repository", "_repo", "_model",
    "_models", "_schema", "_schemas", "_middleware", "-service", "-routes", "-route",
    "-router", "-controller", "-api", "-view", "-handler", "-repository", "-model", "-schema",
)
DEFAULT_IGNORE = (
    "**/node_modules/**", "**/.git/**", "**/__pycache__/**", "**/test/**", "**/tests/**",
    "**/e2e/**", "**/spec/**", "**/__tests__/**", "**/*.test.*", "**/*.spec.*", "**/test_*.py",
    "**/*_test.py", "**/conftest.py", "**/scripts/**", "docs/**", "**/fixtures/**", "**/migrations/**",
    "vendor/**", "dist/**", "build/**", "coverage/**", ".claude/**", ".github/**",
)
ENTRY_NAMES = (
    "main.py", "app.py", "server.py", "manage.py", "wsgi.py", "asgi.py", "index.js", "index.ts",
    "server.js", "server.ts", "main.ts", "main.js",
)
TSCONFIGS = ("tsconfig.json", "jsconfig.json", "tsconfig.base.json")
MAX_BYTES = 2_000_000
ORDER = {"SINGLE": 0, "NONE": 1, "ROOT": 2, "KEEP": 3, "JUSTIFIED": 4, "SHARED": 5}
STAYS = ("JUSTIFIED", "SHARED", "ROOT", "KEEP")
SHARED_ZONE = "@shared"
ROOT_ZONE = "@root"
OTHER_ZONE = "@other"
WIRING_ZONE = "@wiring"
PACKAGE = "<package>"
BLOCKING = ("NEW_SINGLE", "NEW_UNUSED", "NEW_ROOT", "LOST_SECOND", "CROSS", "UPWARD", "CLASH", "EXPORT")
VIOLATIONS = ("SINGLE", "NONE", "ROOT")
OPENERS = {"{": 1, "(": 1, "[": 1, "}": -1, ")": -1, "]": -1}
CONTINUES = ("=", "(", "[", "{", ",", "+", "-", "*", "?", ":", "&&", "||", "=>", ".", "\\")
REGEX_PREV = set("(,=:[!&|?{};+-*%~^") | {""}
REGEX_WORDS = {"return", "typeof", "case", "do", "else", "in", "of", "yield", "await", "void", "delete", "new", "throw", "instanceof"}

JS_FROM = re.compile(
    r"""(?:^|[;\n])[ \t]*(?P<kw>import|export)\b(?P<what>[^;'"`]*?)\bfrom[ \t]*['"](?P<spec>[^'"\n]+)['"]"""
)
JS_BARE = re.compile(r"""(?:^|[;\n])[ \t]*(?P<kw>import)[ \t]*['"](?P<spec>[^'"\n]+)['"]""")
JS_CALL = re.compile(r"""\b(?P<kw>import|require)\s*\(\s*['"](?P<spec>[^'"\n]+)['"]\s*\)""")
SRC_ATTR = re.compile(r"""\b(?:src|href)\s*=\s*['"](?P<spec>[^'"\n]+?\.(?:m?js|cjs|ts))['"]""")
TEMPLATE_NAME = re.compile(
    r"""['"](?P<name>[\w./-]+\.(?:html|htm|eta|ejs|hbs|njk|jinja|jinja2|j2))['"]"""
)
PY_FROM = re.compile(
    r"^[ \t]*from[ \t]+(?P<mod>\.+[\w.]*|[\w.]+)[ \t]+import[ \t]+(?P<names>\([^)]*\)|[^\n#;]+)",
    re.M,
)
PY_IMPORT = re.compile(
    r"^[ \t]*import[ \t]+(?P<mods>[\w.]+(?:[ \t]+as[ \t]+\w+)?(?:[ \t]*,[ \t]*[\w.]+(?:[ \t]+as[ \t]+\w+)?)*)",
    re.M,
)
PY_DOCSTRING = re.compile(r'("""|\'\'\').*?\1', re.S)
PY_STRING = re.compile(r"'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\"")
PY_COMMENT = re.compile(r"#[^\n]*")
MARKUP_COMMENT = re.compile(r"<!--.*?-->|/\*.*?\*/", re.S)
JS_DECL = re.compile(
    r"^(?P<export>export\s+(?P<default>default\s+)?)?(?:declare\s+)?(?:async\s+)?"
    r"(?P<kind>function(?:\s*\*\s*|\s+)|(?:const\s+enum|const|let|var|class|abstract\s+class|enum|interface|type|namespace)\s+)"
    r"(?P<name>[\w$]+)"
)
JS_EXPORT_DEFAULT = re.compile(r"^export\s+default\b")
JS_EXPORT_LIST = re.compile(r"^export\s*(?:type\s*)?\{(?P<body>[^}]*)\}\s*;?\s*$", re.S)
JS_IMPORT_STATEMENT = re.compile(r"^(?:import\b|export\s*\*|export\s*(?:type\s*)?\{[^}]*\}\s*from\b)", re.S)
PY_DECL = re.compile(r"^(?:async[ \t]+def|def|class)[ \t]+(?P<name>[A-Za-z_]\w*)|^(?P<const>[A-Za-z_]\w*)[ \t]*(?::[^=\n]+)?=(?!=)")


def git(repo: Path, *args: str, data: bytes | None = None, check: bool = True) -> bytes:
    done = subprocess.run(["git", "-C", str(repo), *args], input=data, capture_output=True)
    if check and done.returncode != 0:
        raise SystemExit(f"git {' '.join(args)}: {done.stderr.decode().strip()}")
    return done.stdout if done.returncode == 0 else b""


def succeeds(repo: Path, *args: str) -> bool:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True).returncode == 0


def read_at(repo: Path, ref: str, path: str) -> str | None:
    if ref == ".":
        file = repo / path
        return file.read_text(errors="replace") if file.is_file() else None
    done = subprocess.run(["git", "-C", str(repo), "show", f"{ref}:{path}"], capture_output=True)
    return done.stdout.decode("utf-8", errors="replace") if done.returncode == 0 else None


def compile_glob(pattern: str) -> re.Pattern:
    pattern = pattern.strip().removeprefix("./").rstrip("/")
    if not any(ch in pattern for ch in "*?["):
        return re.compile(re.escape(pattern) + r"(?:/.*)?\Z")
    out = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def any_match(patterns: list[re.Pattern], path: str) -> bool:
    return any(rx.match(path) for rx in patterns)


def line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def blank_span(chars: list[str], start: int, end: int) -> None:
    for i in range(start, end):
        if chars[i] != "\n":
            chars[i] = " "


def string_end(text: str, start: int, quote: str) -> int:
    i = start + 1
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == quote:
            return i + 1
        if ch == "\n":
            return i
        i += 1
    return len(text)


def template_end(text: str, start: int) -> int:
    i = start + 1
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "`":
            return i + 1
        if ch == "$" and text[i + 1 : i + 2] == "{":
            i = expression_end(text, i + 2)
            continue
        i += 1
    return len(text)


def expression_end(text: str, start: int) -> int:
    depth = 1
    i = start
    while i < len(text):
        ch = text[i]
        if ch in "'\"":
            i = string_end(text, i, ch)
            continue
        if ch == "`":
            i = template_end(text, i)
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(text)


def regex_end(text: str, start: int) -> int | None:
    i = start + 1
    in_class = False
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "\n":
            return None
        if ch == "[":
            in_class = True
        elif ch == "]":
            in_class = False
        elif ch == "/" and not in_class:
            return i + 1
        i += 1
    return None


def scan_js(text: str) -> tuple[str, list[tuple[int, int]]]:
    chars = list(text)
    literals: list[tuple[int, int]] = []
    prev = ""
    word = ""
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        ahead = text[i + 1] if i + 1 < n else ""
        if ch == "/" and ahead == "/":
            end = text.find("\n", i)
            end = n if end < 0 else end
            blank_span(chars, i, end)
            i = end
            continue
        if ch == "/" and ahead == "*":
            end = text.find("*/", i + 2)
            end = n if end < 0 else end + 2
            blank_span(chars, i, end)
            i = end
            continue
        if ch in "'\"`":
            end = template_end(text, i) if ch == "`" else string_end(text, i, ch)
            literals.append((i, end))
            prev, word, i = ch, "", end
            continue
        if ch == "/" and (prev in REGEX_PREV or word in REGEX_WORDS):
            end = regex_end(text, i)
            if end:
                literals.append((i, end))
                prev, word, i = "/", "", end
                continue
        if ch.isalnum() or ch in "_$":
            word = word + ch if prev and (prev.isalnum() or prev in "_$") else ch
        elif not ch.isspace():
            word = ""
        if not ch.isspace():
            prev = ch
        i += 1
    return "".join(chars), literals


def blank_literals(text: str) -> str:
    cleaned, literals = scan_js(text)
    chars = list(cleaned)
    for start, end in literals:
        blank_span(chars, start + 1, max(start + 1, end - 1))
    return "".join(chars)


def inside(spans: list[tuple[int, int]], starts: list[int], index: int) -> bool:
    pos = bisect.bisect_right(starts, index) - 1
    return pos >= 0 and spans[pos][0] <= index < spans[pos][1]


def blank_matches(rx: re.Pattern, text: str) -> str:
    return rx.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def module_name(path: str) -> str:
    stem = posixpath.splitext(posixpath.basename(path))[0]
    if stem in ("__init__", "index", "mod", "main") and "/" in path:
        stem = posixpath.basename(posixpath.dirname(path))
    return strip_layer(stem.replace("-", "_"))


def strip_layer(stem: str) -> str:
    for suffix in sorted(LAYER_SUFFIXES, key=len, reverse=True):
        if stem.endswith(suffix) and len(stem) > len(suffix):
            return stem[: -len(suffix)]
    return stem


def strip_json_comments(text: str) -> str:
    cleaned, _ = scan_js(text)
    return re.sub(r",(\s*[}\]])", r"\1", cleaned)


def clean_text(path: str, text: str) -> str:
    if path.endswith(JS_EXT):
        return scan_js(text)[0]
    if path.endswith(PY_EXT):
        return blank_matches(PY_DOCSTRING, text)
    return blank_matches(MARKUP_COMMENT, text)


def flat_text(path: str, text: str) -> str:
    if path.endswith(PY_EXT):
        return blank_matches(PY_COMMENT, blank_matches(PY_STRING, blank_matches(PY_DOCSTRING, text)))
    return blank_literals(text)


class Source:
    def __init__(self, repo: Path, ref: str):
        self.repo = repo
        self.ref = ref
        self.paths = self._list()
        self.pathset = set(self.paths)

    def _list(self) -> list[str]:
        if self.ref == ".":
            raw = git(self.repo, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
            names = {n for n in raw.decode().split("\0") if n}
            return sorted(n for n in names if (self.repo / n).is_file())
        raw = git(self.repo, "ls-tree", "-r", "-z", "--name-only", self.ref)
        return [n for n in raw.decode().split("\0") if n]

    def read(self, paths: list[str]) -> dict[str, str]:
        if self.ref == ".":
            return {
                p: (self.repo / p).read_text(errors="replace")
                for p in paths if (self.repo / p).stat().st_size <= MAX_BYTES
            }
        request = "".join(f"{self.ref}:{p}\n" for p in paths).encode()
        raw = git(self.repo, "cat-file", "--batch", data=request)
        texts = {}
        pos = 0
        for path in paths:
            end = raw.index(b"\n", pos)
            header = raw[pos:end].split()
            pos = end + 1
            if len(header) < 3 or header[1] != b"blob":
                continue
            size = int(header[2])
            if size <= MAX_BYTES:
                texts[path] = raw[pos : pos + size].decode("utf-8", errors="replace")
            pos += size + 1
        return texts

    def label(self) -> str:
        if self.ref == ".":
            head = git(self.repo, "rev-parse", "--short=7", "HEAD", check=False).decode().strip()
            return f"{head or 'none'}+worktree"
        return git(self.repo, "rev-parse", "--short=7", self.ref).decode().strip()


@dataclass
class Layout:
    shared: list[str]
    domain_globs: list[tuple[re.Pattern, int]]
    domain_regexes: list[re.Pattern]
    module_domains: bool
    ignore: list[re.Pattern]
    include: list[re.Pattern]
    not_domains: list[re.Pattern]
    roots: list[re.Pattern]
    wiring: list[re.Pattern]
    url_roots: list[tuple[str, re.Pattern, int]]
    aliases: list[tuple[str, list[str]]]
    references: list[dict]
    justified: list[tuple[re.Pattern, str, str]]
    planned: list[tuple[re.Pattern, dict]]
    unit: str
    ask_exports: bool
    python_roots: list[str]
    basename_fallback: bool
    origin: str
    raw: dict

    @property
    def inferred(self) -> bool:
        return self.origin == "inferred"

    def is_shared(self, path: str) -> bool:
        return any(path == s or path.startswith(s + "/") for s in self.shared)

    def ignored(self, path: str) -> bool:
        return any_match(self.ignore, path) and not any_match(self.include, path)

    def zone(self, path: str) -> str | None:
        if self.ignored(path):
            return None
        if any_match(self.wiring, path):
            return WIRING_ZONE
        if any_match(self.roots, path):
            return ROOT_ZONE
        if self.is_shared(path):
            return SHARED_ZONE
        if any_match(self.not_domains, path):
            return None
        return self.domain_of(path) or OTHER_ZONE

    def domain_of(self, path: str) -> str | None:
        parts = path.split("/")
        for rx, depth in self.domain_globs:
            if len(parts) > depth and rx.match("/".join(parts[:depth])):
                return parts[depth - 1]
        for rx in self.domain_regexes:
            found = rx.search(path)
            if found:
                return strip_layer(found.group("domain"))
        if self.module_domains and path.endswith(SCANNED_EXT):
            return module_name(path)
        return None

    def home_of(self, domain: str, evidence: str) -> str:
        parts = evidence.split("/")
        for rx, depth in self.domain_globs:
            if len(parts) > depth and rx.match("/".join(parts[:depth])) and parts[depth - 1] == domain:
                return "/".join(parts[:depth]) + "/"
        return f"the {domain} code ({posixpath.dirname(evidence)}/)"

    def urls_of(self, path: str) -> list[str]:
        parts = path.split("/")
        urls = []
        for prefix, rx, depth in self.url_roots:
            if len(parts) > depth and rx.match("/".join(parts[:depth])):
                urls.append(prefix.rstrip("/") + "/" + "/".join(parts[depth:]))
        return urls

    def justification(self, path: str) -> str | None:
        return justification(self.justified, path)

    def plan(self, path: str) -> dict:
        return next((entry for rx, entry in self.planned if rx.match(path)), {})

    def rule_files(self) -> set[str]:
        return {CONFIG_PATH, *self.raw.get("rules", [])}


def justification(entries: list[tuple[re.Pattern, str, str]], path: str) -> str | None:
    for rx, pattern, why in entries:
        if rx.match(path):
            return why or pattern
    return None


def compile_justified(config: dict) -> list[tuple[re.Pattern, str, str]]:
    return [(compile_glob(e["path"]), e["path"], e.get("why", "")) for e in config.get("justified", [])]


def depth_of(pattern: str) -> int:
    return len(pattern.strip("/").split("/"))


def tsconfig_aliases(repo: Path, ref: str) -> list[tuple[str, list[str]]]:
    for name in TSCONFIGS:
        text = read_at(repo, ref, name)
        if text is None:
            continue
        try:
            options = json.loads(strip_json_comments(text)).get("compilerOptions", {})
        except json.JSONDecodeError:
            continue
        base = options.get("baseUrl", ".")
        return [
            (key, [posixpath.normpath(posixpath.join(base, t)) for t in targets])
            for key, targets in options.get("paths", {}).items()
        ]
    return []


def make_layout(config: dict | None, origin: str, paths: list[str]) -> Layout:
    if config is None:
        config = infer_config(paths)
        origin = "inferred"
    domains = config.get("domains", [])
    url_roots = [
        (prefix, compile_glob(d), depth_of(d))
        for prefix, dirs in config.get("urlRoots", {}).items() for d in dirs
    ]
    return Layout(
        shared=[s.strip("/") for s in config.get("shared", [])],
        domain_globs=[(compile_glob(d), depth_of(d)) for d in domains if isinstance(d, str)],
        domain_regexes=[re.compile(d["regex"]) for d in domains if isinstance(d, dict) and "regex" in d],
        module_domains=bool(config.get("moduleDomains", False)),
        ignore=[compile_glob(g) for g in (*DEFAULT_IGNORE, *config.get("ignore", []))],
        include=[compile_glob(g) for g in config.get("include", [])],
        not_domains=[compile_glob(g) for g in config.get("notDomains", [])],
        roots=[compile_glob(g) for g in config.get("roots", [])],
        wiring=[compile_glob(g) for g in config.get("compositionRoots", [])],
        url_roots=url_roots,
        aliases=[(k, v if isinstance(v, list) else [v]) for k, v in config.get("aliases", {}).items()],
        references=config.get("references", []),
        justified=compile_justified(config),
        planned=[(compile_glob(e["path"]), e) for e in config.get("planned", [])],
        unit=config.get("unit", "file"),
        ask_exports=bool(config.get("askExports", False)),
        python_roots=config.get("pythonRoots", [""]),
        basename_fallback=bool(config.get("basenameFallback", False)),
        origin=origin,
        raw=config,
    )


def join_path(*parts: str) -> str:
    return "/".join(p for p in parts if p)


def child_dirs(code: list[str], parent: str) -> set[str]:
    prefix = parent + "/" if parent else ""
    return {p[len(prefix):].split("/")[0] for p in code if p.startswith(prefix) and "/" in p[len(prefix):]}


def infer_config(paths: list[str]) -> dict:
    ignore = [compile_glob(g) for g in DEFAULT_IGNORE]
    code = [p for p in paths if p.endswith(SCANNED_EXT) and not any_match(ignore, p)]
    counts: Counter = Counter()
    for path in code:
        parts = path.split("/")
        for i in range(1, len(parts)):
            if parts[i - 1] in SHARED_NAMES:
                counts["/".join(parts[:i])] += 1
    candidates = sorted(d for d, n in counts.items() if n >= 2)
    shared = [d for d in candidates if not any(d.startswith(o + "/") for o in candidates)]
    if not shared:
        raise SystemExit(f"no shared folder found; write {CONFIG_PATH} (see references/config.md)")
    domains: list[str] = []
    for folder in list(shared):
        parent = posixpath.dirname(folder)
        siblings = child_dirs(code, parent) - {posixpath.basename(folder)}
        weight = Counter()
        for path in code:
            for sibling in siblings:
                if path.startswith(join_path(parent, sibling) + "/"):
                    weight["layer" if sibling in LAYER_NAMES else "feature"] += 1
        if weight["feature"] < weight["layer"]:
            continue
        features = sorted(d for d in siblings if d not in LAYER_NAMES)
        layers = sorted(d for d in siblings if d in LAYER_NAMES)
        if len(features) == 1 and features[0] in FEATURE_PARENTS and child_dirs(code, join_path(parent, features[0])):
            domains.append(join_path(parent, features[0], "*"))
        elif features:
            domains.append(join_path(parent, "*"))
        shared += [join_path(parent, d) for d in layers if join_path(parent, d) not in shared]
    entries = sorted(
        p for p in paths
        if posixpath.basename(p) in ENTRY_NAMES and not any_match(ignore, p)
        and p.count("/") <= (0 if posixpath.basename(p).startswith("index.") else 2)
    )
    pyroots = [""] + sorted({posixpath.dirname(e) for e in entries if e.endswith(".py") and "/" in e})
    if any(p.startswith("src/") and p.endswith(".py") for p in code) and "src" not in pyroots:
        pyroots.append("src")
    return {
        "shared": sorted(set(shared)),
        "domains": sorted(set(domains)),
        "moduleDomains": True,
        "notDomains": [],
        "roots": entries,
        "pythonRoots": pyroots,
        "basenameFallback": True,
        "unit": "file",
    }


def read_config(repo: Path, ref: str, config_arg: str | None) -> tuple[dict | None, str]:
    if config_arg and Path(config_arg).is_file():
        return json.loads(Path(config_arg).read_text()), str(config_arg)
    path = config_arg or CONFIG_PATH
    text = read_at(repo, ref, path)
    if text is None:
        if config_arg:
            raise SystemExit(f"config not found: {config_arg}")
        return None, "inferred"
    return json.loads(text), f"{ref}:{path}"


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    uses: tuple[tuple[int, frozenset], ...]
    reexport: bool
    pairs: frozenset

    @property
    def lines(self) -> tuple[int, ...]:
        return tuple(line for line, _ in self.uses)

    @property
    def names(self) -> frozenset:
        return frozenset().union(*(names for _, names in self.uses))

    @property
    def evidence(self) -> str:
        return f"{self.source}:{self.uses[0][0]}"

    def toward(self, wanted: frozenset | None) -> Edge:
        if wanted is None:
            return self
        best = sorted(self.uses, key=lambda u: (not ("*" in u[1] or u[1] & wanted), u[0]))
        return replace(self, uses=tuple(best))


@dataclass
class Statement:
    start: int
    end: int
    name: str | None
    exported: tuple[str, ...]
    type_only: bool = False


class Structure:
    def __init__(self, path: str, text: str):
        python = path.endswith(PY_EXT)
        flat = flat_text(path, text)
        self.lines = flat.split("\n")
        self.statements = self._statements(python)
        names = {s.name for s in self.statements if s.name}
        self.calls: dict[str, set[str]] = defaultdict(set)
        for statement in self.statements:
            if statement.name:
                body = "\n".join(self.lines[statement.start - 1 : statement.end])
                self.calls[statement.name] |= (set(re.findall(r"[A-Za-z_$][\w$]*", body)) & names) - {statement.name}
        self.exports: dict[str, list[Statement]] = defaultdict(list)
        for statement in self.statements:
            for alias in statement.exported:
                self.exports[alias].append(statement)

    def _statements(self, python: bool) -> list[Statement]:
        starts = top_level_starts(self.lines, python)
        statements = []
        for i, start in enumerate(starts):
            end = starts[i + 1] - 1 if i + 1 < len(starts) else len(self.lines)
            block = "\n".join(self.lines[start - 1 : end])
            statements.append(classify(block, start, end, python))
        if not python:
            self._attach_export_lists(statements)
        return statements

    def _attach_export_lists(self, statements: list[Statement]) -> None:
        aliases = defaultdict(list)
        for statement in statements:
            block = "\n".join(self.lines[statement.start - 1 : statement.end]).strip()
            found = JS_EXPORT_LIST.match(block)
            if not found:
                continue
            for item in found.group("body").split(","):
                parts = [p.strip() for p in re.split(r"\s+as\s+", item.strip().removeprefix("type ").strip())]
                if parts[0]:
                    aliases[parts[0]].append(parts[-1])
        for statement in statements:
            if statement.name in aliases:
                statement.exported = tuple(sorted({*statement.exported, *aliases[statement.name]}))

    def value_exports(self) -> list[str]:
        return sorted(alias for alias, targets in self.exports.items() if not all(t.type_only for t in targets))

    def owners(self, line: int) -> set[str] | None:
        statement = next((s for s in self.statements if s.start <= line <= s.end), None)
        if statement is None or statement.name is None:
            return None
        owners = set(statement.exported)
        for alias, targets in self.exports.items():
            if any(t is not statement and self._reaches(t.name, statement.name) for t in targets):
                owners.add(alias)
        return owners or None

    def _reaches(self, start: str | None, goal: str) -> bool:
        seen = set()
        stack = [start]
        while stack:
            current = stack.pop()
            if current == goal:
                return True
            if current in seen or current is None:
                continue
            seen.add(current)
            stack.extend(self.calls.get(current, ()))
        return False


def top_level_starts(lines: list[str], python: bool) -> list[int]:
    starts = []
    depth = 0
    previous = ""
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        at_top = depth == 0 and stripped and (not python or not line[:1].isspace())
        continues = previous.endswith(CONTINUES) or stripped.startswith((".", "?", ":", "&&", "||"))
        decorated = python and previous.startswith("@")
        if at_top and stripped[0] not in "})]," and not continues and not decorated:
            starts.append(number)
        for ch in line:
            depth = max(0, depth + OPENERS.get(ch, 0))
        if stripped:
            previous = stripped
    return starts or [1]


def classify(block: str, start: int, end: int, python: bool) -> Statement:
    if python:
        line = next((l for l in block.split("\n") if l.strip() and not l.startswith("@")), "")
        found = PY_DECL.match(line)
        if not found:
            return Statement(start, end, None, ())
        name = found.group("name") or found.group("const")
        return Statement(start, end, name, () if name.startswith("_") else (name,))
    text = block.strip()
    if JS_IMPORT_STATEMENT.match(text) or JS_EXPORT_LIST.match(text):
        return Statement(start, end, None, ())
    found = JS_DECL.match(text)
    if found:
        name = found.group("name")
        exported = (("default",) if found.group("default") else (name,)) if found.group("export") else ()
        type_only = found.group("kind").strip() in ("interface", "type")
        return Statement(start, end, name, exported, type_only)
    if JS_EXPORT_DEFAULT.match(text):
        return Statement(start, end, "default", ("default",))
    return Statement(start, end, None, ())


class Graph:
    def __init__(self, source: Source, layout: Layout):
        self.layout = layout
        self.pathset = source.pathset
        self.aliases = layout.aliases + tsconfig_aliases(source.repo, source.ref)
        self.url_index: dict[str, list[str]] = defaultdict(list)
        self.by_basename: dict[str, list[str]] = defaultdict(list)
        for path in source.paths:
            if layout.zone(path) is None:
                continue
            for url in layout.urls_of(path):
                self.url_index[url].append(path)
            if path.endswith(SCANNED_EXT):
                self.by_basename[posixpath.basename(path)].append(path)
        self.texts = source.read([p for p in source.paths if self._scannable(p)])
        self.cleaned = {p: clean_text(p, t) for p, t in self.texts.items()}
        self.incoming: dict[str, dict[str, Edge]] = defaultdict(dict)
        self.outgoing: dict[str, dict[str, Edge]] = defaultdict(dict)
        self._structures: dict[str, Structure | None] = {}
        self._uses: dict[tuple[str, frozenset | None], list[Edge]] = {}
        for path, text in self.texts.items():
            self._scan(path, text)
        self._scan_references()

    def _scannable(self, path: str) -> bool:
        if self.layout.zone(path) is None:
            return False
        extra = tuple(self.layout.raw.get("scanExtensions", []))
        return path.endswith(SCANNED_EXT + extra)

    def clashes(self) -> dict[str, list[str]]:
        return {u: sorted(set(p)) for u, p in self.url_index.items() if len(set(p)) > 1}

    def add(self, source: str, line: int, target: str, names: frozenset,
            pairs: frozenset = frozenset(), reexport: bool = False) -> None:
        if source == target:
            return
        old = self.incoming[target].get(source)
        if old:
            uses = tuple(sorted({*old.uses, (line, names)}, key=lambda u: u[0]))
            edge = Edge(source, target, uses, old.reexport and reexport, old.pairs | pairs)
        else:
            edge = Edge(source, target, ((line, names),), reexport, pairs)
        self.incoming[target][source] = edge
        self.outgoing[source][target] = edge

    def _scan(self, path: str, text: str) -> None:
        if path.endswith(PY_EXT):
            self._scan_python(path, self.cleaned[path])
            return
        literals: list[tuple[int, int]] = []
        if path.endswith(JS_EXT):
            text, literals = scan_js(text)
        else:
            text = self.cleaned[path]
        starts = [s for s, _ in literals]
        for found in JS_FROM.finditer(text):
            if inside(literals, starts, found.start("kw")):
                continue
            names, pairs = js_names(found.group("what"))
            self._link(path, text, found, names, pairs, found.group("kw") == "export")
        for rx in (JS_BARE, JS_CALL):
            for found in rx.finditer(text):
                if not inside(literals, starts, found.start("kw")):
                    self._link(path, text, found, frozenset({"*"}), frozenset(), False)
        if path.endswith(MARKUP_EXT):
            for found in SRC_ATTR.finditer(text):
                self._link(path, text, found, frozenset({"*"}), frozenset(), False)
        for found in TEMPLATE_NAME.finditer(text):
            line = line_of(text, found.start("name"))
            for target in self.resolve_template(path, found.group("name")):
                self.add(path, line, target, frozenset({"*"}))

    def _link(self, path: str, text: str, found: re.Match, names: frozenset,
              pairs: frozenset, reexport: bool) -> None:
        line = line_of(text, found.start("spec"))
        for target in self.resolve_js(path, found.group("spec")):
            self.add(path, line, target, names, pairs, reexport)

    def _scan_python(self, path: str, text: str) -> None:
        barrel = posixpath.basename(path) == "__init__.py" and self.layout.zone(path) == SHARED_ZONE
        for found in PY_FROM.finditer(text):
            line = line_of(text, found.start("mod"))
            names, pairs = py_names(found.group("names"))
            for target, used in self.resolve_python(path, found.group("mod"), names):
                kept = frozenset(p for p in pairs if p[0] in used)
                self.add(path, line, target, used, kept, barrel and PACKAGE not in used)
        for found in PY_IMPORT.finditer(text):
            line = line_of(text, found.start("mods"))
            for module in found.group("mods").split(","):
                name = module.strip().split()[0]
                for target, used in self.resolve_python(path, name, None):
                    self.add(path, line, target, used)

    def resolve_js(self, importer: str, spec: str) -> list[str]:
        spec = spec.split("?", 1)[0].split("#", 1)[0]
        if not spec or spec.startswith(("http:", "https:", "//", "data:")):
            return []
        if spec.startswith("/"):
            return self.resolve_url(posixpath.normpath(spec)) or self.by_name(spec)
        if not spec.startswith("."):
            return self.resolve_alias(spec)
        urls = self.layout.urls_of(importer)
        if urls:
            hits = self.resolve_url(posixpath.normpath(posixpath.join(posixpath.dirname(urls[0]), spec)))
            if hits:
                return hits
        target = posixpath.normpath(posixpath.join(posixpath.dirname(importer), spec))
        if target.startswith(".."):
            return []
        return self.try_files(target) or self.by_name(spec)

    def resolve_alias(self, spec: str) -> list[str]:
        for key, targets in self.aliases:
            if key.endswith("*"):
                if not spec.startswith(key[:-1]):
                    continue
                rest = spec[len(key) - 1:]
                candidates = [t.replace("*", rest) if "*" in t else posixpath.join(t, rest) for t in targets]
            elif spec == key or spec.startswith(key.rstrip("/") + "/"):
                rest = spec[len(key.rstrip("/")):].lstrip("/")
                candidates = [posixpath.join(t.rstrip("/"), rest) if rest else t for t in targets]
            else:
                continue
            for candidate in candidates:
                hits = self.try_files(candidate)
                if hits:
                    return hits
        return []

    def resolve_url(self, url: str) -> list[str]:
        for candidate in (url, *(url + ext for ext in RESOLVE_ORDER)):
            if candidate in self.url_index:
                return sorted(set(self.url_index[candidate]))
        return []

    def by_name(self, spec: str) -> list[str]:
        if not self.layout.basename_fallback:
            return []
        hits = self.by_basename.get(posixpath.basename(spec), [])
        return list(hits) if len(hits) == 1 else []

    def try_files(self, target: str) -> list[str]:
        target = posixpath.normpath(target)
        if target in self.pathset:
            return [target]
        stem, ext = posixpath.splitext(target)
        for alt in JS_SWAP.get(ext, ()):
            if stem + alt in self.pathset:
                return [stem + alt]
        for ext in RESOLVE_ORDER:
            if target + ext in self.pathset:
                return [target + ext]
        for ext in RESOLVE_ORDER:
            if f"{target}/index{ext}" in self.pathset:
                return [f"{target}/index{ext}"]
        return []

    def resolve_template(self, importer: str, name: str) -> list[str]:
        base = posixpath.basename(name)
        hits = [
            p for p in self.by_basename.get(base, [])
            if p.endswith(MARKUP_EXT) and (p == name or p.endswith("/" + name.lstrip("./")))
        ]
        if len(hits) <= 1:
            return hits
        own = self.layout.zone(importer)
        local = [h for h in hits if self.layout.zone(h) == own]
        return local or hits

    def resolve_python(self, importer: str, module: str, names: frozenset | None) -> list[tuple[str, frozenset]]:
        if module.startswith("."):
            dots = len(module) - len(module.lstrip("."))
            base = posixpath.dirname(importer)
            for _ in range(dots - 1):
                base = posixpath.dirname(base)
            rest = module.lstrip(".").replace(".", "/")
            prefixes = [posixpath.join(base, rest) if rest else base]
        else:
            dotted = module.replace(".", "/")
            prefixes = [posixpath.join(root, dotted) if root else dotted for root in self.layout.python_roots]
        for prefix in prefixes:
            found = self.python_targets(prefix, names)
            if found:
                return found
        return []

    def python_targets(self, prefix: str, names: frozenset | None) -> list[tuple[str, frozenset]]:
        module_file = self.python_module(prefix)
        if names is None:
            return [(module_file, frozenset({"*"}))] if module_file else []
        hits: list[tuple[str, frozenset]] = []
        leftover = set()
        for name in names:
            sub = self.python_module(posixpath.join(prefix, name)) if name != "*" else None
            if sub:
                hits.append((sub, frozenset({"*"})))
            else:
                leftover.add(name)
        if module_file and leftover:
            hits.append((module_file, frozenset(leftover)))
        elif module_file and module_file.endswith("__init__.py"):
            hits.append((module_file, frozenset({PACKAGE})))
        return hits

    def python_module(self, prefix: str) -> str | None:
        for candidate in (prefix + ".py", prefix + "/__init__.py"):
            if candidate in self.pathset:
                return candidate
        return None

    def _scan_references(self) -> None:
        for ref in self.layout.references:
            targets_rx = compile_glob(ref["targets"])
            within = compile_glob(ref["in"]) if ref.get("in") else None
            strip = re.compile(ref["strip"]) if ref.get("strip") else None
            for target in sorted(p for p in self.pathset if targets_rx.match(p)):
                name = posixpath.basename(target)
                stem = posixpath.splitext(name)[0]
                if strip:
                    stem = strip.sub("", stem)
                rx = re.compile(ref["pattern"].replace("{name}", re.escape(name)).replace("{stem}", re.escape(stem)))
                for path, text in self.texts.items():
                    if path == target or stem not in text or (within and not within.match(path)):
                        continue
                    for found in rx.finditer(self.cleaned[path]):
                        self.add(path, line_of(text, found.start()), target, frozenset({"*"}))

    def structure(self, path: str) -> Structure | None:
        if path not in self._structures:
            text = self.texts.get(path)
            usable = text is not None and path.endswith(JS_EXT + PY_EXT)
            self._structures[path] = Structure(path, text) if usable else None
        return self._structures[path]

    def exports(self, path: str) -> list[str]:
        structure = self.structure(path)
        return sorted(structure.exports) if structure else []

    def value_exports(self, path: str) -> list[str]:
        structure = self.structure(path)
        return structure.value_exports() if structure else []

    def uses(self, target: str, wanted: frozenset | None = None) -> list[Edge]:
        key = (target, wanted)
        if key not in self._uses:
            self._uses[key] = self._walk_uses(target, wanted, frozenset())
        return self._uses[key]

    def _walk_uses(self, target: str, wanted: frozenset | None, seen: frozenset) -> list[Edge]:
        if target in seen:
            return []
        seen = seen | {target}
        found: list[Edge] = []
        for edge in self.incoming.get(target, {}).values():
            if wanted is not None and "*" not in edge.names and not (edge.names & wanted):
                continue
            if not edge.reexport:
                found.append(edge.toward(wanted))
                continue
            namespace = [alias for name, alias in edge.pairs if name == "*"]
            if namespace:
                passed = frozenset(namespace)
            elif "*" in edge.names:
                passed = wanted if wanted is not None else (frozenset(self.exports(target)) or None)
            else:
                pairs = edge.pairs or frozenset((n, n) for n in edge.names)
                passed = frozenset(alias for name, alias in pairs if wanted is None or name in wanted)
            found.extend(self._walk_uses(edge.source, passed, seen))
        return found


def js_names(what: str) -> tuple[frozenset, frozenset]:
    what = re.sub(r"\btype\b", "", what).strip()
    if not what:
        return frozenset({"*"}), frozenset()
    star = re.match(r"\*\s*as\s+([\w$]+)", what)
    if star:
        return frozenset({"*"}), frozenset({("*", star.group(1))})
    if what.startswith("*"):
        return frozenset({"*"}), frozenset()
    names = set()
    pairs = set()
    brace = re.search(r"\{([^}]*)\}", what)
    if brace:
        for item in brace.group(1).split(","):
            parts = [p.strip() for p in re.split(r"\s+as\s+", item.strip())]
            if parts[0]:
                names.add(parts[0])
                pairs.add((parts[0], parts[-1]))
        what = what[: brace.start()] + what[brace.end():]
    rest = what.strip(" ,\n\t")
    if rest.startswith("*"):
        names.add("*")
    elif rest:
        names.add("default")
        pairs.add(("default", "default"))
    return (frozenset(names) or frozenset({"*"})), frozenset(pairs)


def py_names(raw: str) -> tuple[frozenset, frozenset]:
    raw = raw.strip().strip("()").replace("\n", " ")
    if raw.strip() == "*":
        return frozenset({"*"}), frozenset()
    pairs = set()
    for item in raw.split(","):
        parts = re.split(r"\s+as\s+", item.strip())
        if parts[0] and re.fullmatch(r"\w+", parts[0]):
            pairs.add((parts[0], parts[-1]))
    names = frozenset(p[0] for p in pairs)
    return (names or frozenset({"*"})), frozenset(pairs)


@dataclass
class Row:
    path: str
    status: str = "NONE"
    domains: dict[str, str] = field(default_factory=dict)
    via: dict[str, str] = field(default_factory=dict)
    direct: list[str] = field(default_factory=list)
    kept_by: list[str] = field(default_factory=list)
    travels_with: list[str] = field(default_factory=list)
    waits_for: list[str] = field(default_factory=list)
    roots: list[str] = field(default_factory=list)
    wiring: list[str] = field(default_factory=list)
    why: str = ""
    move_to: str = ""
    would_be: str = ""
    planned: dict = field(default_factory=dict)
    exports: dict[str, list[str]] = field(default_factory=dict)

    def as_json(self) -> dict:
        data = {"path": self.path, "status": self.status, "domains": self.domains}
        keys = ("via", "direct", "kept_by", "travels_with", "waits_for", "roots", "wiring", "why", "move_to", "would_be", "planned", "exports")
        for key in keys:
            value = getattr(self, key)
            if value:
                data[key] = value
        return data


@dataclass
class Facts:
    direct: dict[str, str] = field(default_factory=dict)
    shared: list[Edge] = field(default_factory=list)
    roots: list[str] = field(default_factory=list)
    wiring: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)


@dataclass
class Reach:
    domains: dict[str, str] = field(default_factory=dict)
    via: dict[str, str] = field(default_factory=dict)
    kept: set[str] = field(default_factory=set)
    wiring: set[str] = field(default_factory=set)
    travels: set[str] = field(default_factory=set)
    waits: set[str] = field(default_factory=set)

    def take(self, domains: dict[str, str], hop: str | None) -> None:
        for domain, evidence in domains.items():
            if domain not in self.domains:
                self.domains[domain] = evidence
                if hop:
                    self.via[domain] = hop


class Census:
    def __init__(self, graph: Graph):
        self.graph = graph
        self.layout = graph.layout
        targets = [compile_glob(r["targets"]) for r in self.layout.references]
        shared_files = [p for p in graph.pathset if self.layout.is_shared(p)]
        self.paths = sorted(
            p for p in shared_files
            if self.layout.zone(p) == SHARED_ZONE and (p.endswith(SCANNED_EXT) or any_match(targets, p))
        )
        counted = set(self.paths)
        self.uncounted = Counter(
            "composition roots" if self.layout.zone(p) == WIRING_ZONE
            else "entry points" if self.layout.zone(p) == ROOT_ZONE
            else "ignored" if self.layout.zone(p) is None
            else "other file types"
            for p in shared_files if p not in counted
        )
        self.warnings = [
            f"shared folder {folder} is ignored by a default pattern; add it to include"
            for folder in self.layout.shared
            if any(p.startswith(folder + "/") for p in shared_files)
            and all(self.layout.zone(p) is None for p in shared_files if p.startswith(folder + "/"))
        ]
        unparsed = Counter(posixpath.splitext(p)[1] for p in graph.pathset if p.endswith(UNPARSED_EXT) and not self.layout.ignored(p))
        if unparsed:
            self.warnings.append("not parsed: " + ", ".join(f"{n} {ext} files" for ext, n in sorted(unparsed.items())))
        self.facts = {p: self._facts(p) for p in self.paths}
        self.anchored = {p: self._anchored(p) for p in self.paths}
        self.reaches = self._reach_all()
        self.rows = {p: self._row(p) for p in self.paths}
        self._attach_exports()

    def _facts(self, path: str) -> Facts:
        facts = Facts()
        for edge in self.graph.uses(path):
            zone = self.layout.zone(edge.source)
            if zone is None:
                continue
            facts.evidence.append(edge.evidence)
            if zone == WIRING_ZONE:
                facts.wiring.append(edge.evidence)
            elif zone == SHARED_ZONE:
                facts.shared.append(edge)
            elif zone in (ROOT_ZONE, OTHER_ZONE):
                facts.roots.append(edge.evidence)
            else:
                facts.direct.setdefault(zone, edge.evidence)
        return facts

    def _anchored(self, path: str) -> bool:
        facts = self.facts[path]
        return bool(self.layout.justification(path) or len(facts.direct) >= 2 or facts.roots)

    def _hub_users(self, hub: str, edge: Edge) -> tuple[set[str], dict[str, str]] | None:
        structure = self.graph.structure(hub)
        if structure is None:
            return None
        names: set[str] = set()
        for line in edge.lines:
            owners = structure.owners(line)
            if owners is None:
                return None
            names |= owners
        users: dict[str, str] = {}
        for use in self.graph.uses(hub, frozenset(names)):
            zone = self.layout.zone(use.source)
            if zone is None:
                continue
            if zone.startswith("@"):
                return None
            users.setdefault(zone, use.evidence)
        return names, users

    def _components(self) -> list[list[str]]:
        edges = {
            p: [e.source for e in self.facts[p].shared if e.source in self.facts and not self.anchored[e.source]]
            for p in self.paths
        }
        index: dict[str, int] = {}
        low: dict[str, int] = {}
        stack: list[str] = []
        on_stack: set[str] = set()
        components: list[list[str]] = []
        for root in self.paths:
            if root in index:
                continue
            work = [(root, iter(edges[root]))]
            index[root] = low[root] = len(index)
            stack.append(root)
            on_stack.add(root)
            while work:
                node, children = work[-1]
                child = next(children, None)
                if child is not None:
                    if child not in index:
                        index[child] = low[child] = len(index)
                        stack.append(child)
                        on_stack.add(child)
                        work.append((child, iter(edges[child])))
                    elif child in on_stack:
                        low[node] = min(low[node], index[child])
                    continue
                work.pop()
                if work:
                    low[work[-1][0]] = min(low[work[-1][0]], low[node])
                if low[node] == index[node]:
                    component = []
                    while True:
                        member = stack.pop()
                        on_stack.discard(member)
                        component.append(member)
                        if member == node:
                            break
                    components.append(component)
        return components

    def _reach_all(self) -> dict[str, Reach]:
        group: dict[str, int] = {}
        outer: list[Reach] = []
        result: dict[str, Reach] = {}
        for number, component in enumerate(self._components()):
            members = set(component)
            for member in component:
                group[member] = number
            shared_reach = Reach()
            for member in component:
                self._collect(member, members, group, outer, shared_reach)
            outer.append(shared_reach)
            for member in component:
                own = Reach(wiring=set(shared_reach.wiring), kept=set(shared_reach.kept),
                            travels=set(shared_reach.travels), waits=set(shared_reach.waits))
                own.take(self.facts[member].direct, None)
                for other in sorted(members - {member}):
                    own.take(self.facts[other].direct, other)
                    if shared_reach.domains:
                        own.travels.add(other)
                    else:
                        own.waits.add(other)
                for domain, evidence in shared_reach.domains.items():
                    if domain not in own.domains:
                        own.domains[domain] = evidence
                        own.via[domain] = shared_reach.via.get(domain, "")
                result[member] = own
        return result

    def _collect(self, member: str, members: set[str], group: dict[str, int], outer: list[Reach], into: Reach) -> None:
        facts = self.facts[member]
        into.wiring |= set(facts.wiring)
        for domain, evidence in facts.direct.items():
            if domain not in into.domains:
                into.domains[domain] = evidence
                into.via[domain] = member
        for edge in facts.shared:
            importer = edge.source
            if importer in members:
                continue
            if importer not in self.facts:
                into.kept.add(importer)
            elif self.anchored[importer]:
                found = self._hub_users(importer, edge)
                if found is None:
                    into.kept.add(importer)
                    continue
                names, users = found
                hop = f"{importer}:{','.join(sorted(names))}"
                into.take(users, hop)
                if len(users) == 1:
                    into.travels.add(hop)
            else:
                sub = outer[group[importer]]
                into.take(sub.domains, importer)
                into.wiring |= sub.wiring
                if sub.kept:
                    into.kept.add(importer)
                elif sub.domains:
                    into.travels.add(importer)
                else:
                    into.waits.add(importer)

    def _row(self, path: str) -> Row:
        facts = self.facts[path]
        reach = self.reaches[path]
        via = {d: h for d, h in reach.via.items() if h and h != path}
        row = Row(
            path, domains=reach.domains, via=via, direct=sorted(set(facts.evidence))[:5],
            kept_by=sorted(reach.kept), travels_with=sorted(reach.travels - {path}),
            waits_for=sorted(reach.waits - {path}), roots=sorted(set(facts.roots))[:3],
            wiring=sorted(reach.wiring)[:3],
        )
        if len(reach.domains) >= 2:
            row.status = "SHARED"
        elif reach.kept:
            row.status, row.why = "KEEP", "needed by " + ", ".join(sorted(reach.kept)[:3])
        elif facts.roots:
            row.status = "ROOT"
        elif len(reach.domains) == 1:
            row.status = "SINGLE"
            row.move_to = self._home(*next(iter(reach.domains.items())), facts)
        why = self.layout.justification(path)
        if why:
            row.would_be, row.status, row.why = row.status, "JUSTIFIED", why
        row.planned = {k: v for k, v in self.layout.plan(path).items() if k != "path"}
        return row

    def _home(self, domain: str, evidence: str, facts: Facts) -> str:
        users = [e.rsplit(":", 1)[0] for e in facts.evidence]
        served = [u for u in users if self.layout.zone(u) == domain and self.layout.urls_of(u)]
        if served:
            return posixpath.dirname(served[0]) + "/"
        return self.layout.home_of(domain, evidence.rsplit(":", 1)[0])

    def _attach_exports(self) -> None:
        if self.layout.unit != "export" and not self.layout.ask_exports:
            return
        for row in self.rows.values():
            if row.status not in ("SHARED", "KEEP"):
                continue
            for name in self.graph.value_exports(row.path):
                users = set()
                for edge in self.graph.uses(row.path, frozenset({name})):
                    zone = self.layout.zone(edge.source)
                    if zone in (ROOT_ZONE, OTHER_ZONE):
                        users.add("root")
                    elif zone:
                        users.add("shared" if zone.startswith("@") else zone)
                row.exports[name] = sorted(users)

    def lonely_exports(self, row: Row) -> dict[str, list[str]]:
        return {n: d for n, d in row.exports.items() if not {"shared", "root"} & set(d) and len(d) == 1}


def load(repo: Path, ref: str, config_arg: str | None, layout: Layout | None = None) -> tuple[Graph, Source]:
    source = Source(repo, ref)
    if layout is None:
        config, origin = read_config(repo, ref, config_arg)
        layout = make_layout(config, origin, source.paths)
    return Graph(source, layout), source


def evidence_text(row: Row) -> str:
    parts = []
    for domain in sorted(row.domains):
        hop = f" via {row.via[domain]}" if row.via.get(domain) else ""
        parts.append(f"{domain} ({row.domains[domain]}{hop})")
    return ", ".join(parts) or "none"


def action_text(row: Row) -> str:
    if row.planned:
        return planned_text(row)
    if row.status == "JUSTIFIED" and row.would_be:
        return f"{row.why} (without this line: {row.would_be})"
    if row.status == "SINGLE":
        text = f"move to {row.move_to}"
        if row.travels_with:
            text += f", together with {', '.join(row.travels_with)}"
        if row.waits_for:
            text += f"; first decide where {', '.join(row.waits_for)} goes (no domain uses it)"
        return text
    if row.status in ("KEEP", "JUSTIFIED"):
        return row.why
    if row.status == "ROOT":
        return f"only the entry point reaches it ({', '.join(row.roots)}): list it as platform or move it"
    if row.status == "NONE" and row.wiring:
        return f"only a composition root wires it ({row.wiring[0]}): which domain owns it?"
    if row.status == "NONE":
        return "nothing outside tests uses it: dead code?"
    return ""


def planned_text(row: Row) -> str:
    ticket = row.planned.get("ticket", "a plan")
    target = row.planned.get("to", "")
    text = f"planned in {ticket}" + (f": {target}" if target else "")
    if row.status == "SINGLE" and target and not target.startswith(row.move_to.rstrip("/")):
        text += f" (census says {row.move_to})"
    if row.status in ("SHARED", "KEEP", "JUSTIFIED"):
        text += f" (today: {row.status})"
    return text


def render_row(row: Row, census: Census) -> str:
    text = f"{row.status} {row.path} — consumers: {evidence_text(row)}"
    action = action_text(row)
    if action:
        text += f" — {action}"
    lonely = census.lonely_exports(row) if census.layout.unit == "export" else {}
    if lonely:
        text += " — exports one domain uses: " + ", ".join(f"{n}({','.join(d) or 'none'})" for n, d in lonely.items())
    return text


def cmd_census(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    graph, source = load(repo, args.ref, args.config)
    if args.unit:
        graph.layout.unit = args.unit
    census = Census(graph)
    scope = (args.scope or "").strip("/")
    scope_rx = compile_glob(scope) if any(ch in scope for ch in "*?[") else None
    rows = {
        p: r for p, r in census.rows.items()
        if not scope or (scope_rx.match(p) if scope_rx else p == scope or p.startswith(scope + "/"))
    }
    if args.ticket:
        rows = {p: r for p, r in rows.items() if r.planned.get("ticket") == args.ticket}
    census.warnings += [
        f"planned entry matches no shared file, done? remove it: {entry['path']} ({entry.get('ticket', '')})"
        for rx, entry in graph.layout.planned if not any(rx.match(p) for p in census.rows)
    ]
    violations = sum(r.status in VIOLATIONS for r in rows.values())
    counts = Counter(r.status for r in rows.values())
    ordered = sorted(rows.values(), key=lambda r: (ORDER[r.status], ",".join(sorted(r.domains)), r.path))
    if args.json:
        print(json.dumps({
            "ref": source.label(),
            "scope": scope or "all",
            "config": graph.layout.origin,
            "unit": graph.layout.unit,
            "shared": graph.layout.shared,
            "summary": dict(counts),
            "not_counted": dict(census.uncounted),
            "warnings": census.warnings,
            "violations": violations,
            "rows": [r.as_json() for r in ordered],
        }, indent=1))
        return 1 if args.strict and violations else 0
    tally = " · ".join(f"{s} {counts.get(s, 0)}" for s in ("SINGLE", "NONE", "ROOT", "KEEP", "SHARED", "JUSTIFIED"))
    where = scope or "all of " + ",".join(graph.layout.shared)
    print(f"AUDIT: {source.label()} {where} — {len(rows)} shared files · {tally} — config {graph.layout.origin}")
    if census.uncounted and not scope:
        print("not counted: " + ", ".join(f"{n} {k}" for k, n in sorted(census.uncounted.items())))
    for warning in census.warnings:
        print(f"WARNING: {warning}")
    if graph.layout.inferred:
        print("WARNING: layout guessed; write .claude/domain-placement.json before trusting these lines")
    for row in ordered:
        loud = graph.layout.unit == "export" and census.lonely_exports(row)
        if args.all or args.ticket or row.status not in ("SHARED", "JUSTIFIED") or loud:
            print(render_row(row, census))
    if args.strict:
        print(f"STRICT: {violations} violation(s) (SINGLE, NONE or ROOT)")
    return 1 if args.strict and violations else 0


def changed_files(repo: Path, base: str, head: str) -> tuple[dict[str, str], set[str], set[str]]:
    if head == ".":
        raw = git(repo, "diff", "--name-status", "-M", "-z", base)
        untracked = git(repo, "ls-files", "-z", "--others", "--exclude-standard").decode().split("\0")
    else:
        raw = git(repo, "diff", "--name-status", "-M", "-z", base, head)
        untracked = []
    tokens = [t for t in raw.decode().split("\0") if t != ""]
    renames: dict[str, str] = {}
    changed: set[str] = {u for u in untracked if u}
    deleted: set[str] = set()
    i = 0
    while i < len(tokens):
        status = tokens[i]
        if status[0] in "RC":
            renames[tokens[i + 2]] = tokens[i + 1]
            changed.update((tokens[i + 1], tokens[i + 2]))
            i += 3
            continue
        if status[0] == "D":
            deleted.add(tokens[i + 1])
        changed.add(tokens[i + 1])
        i += 2
    return renames, changed, deleted


def compare_base(repo: Path, base: str, head: str) -> tuple[str, list[str]]:
    if head == ".":
        found = git(repo, "merge-base", base, "HEAD", check=False).decode().strip()
        return found or base, []
    if git(repo, "rev-parse", f"{head}^{{tree}}") == git(repo, "rev-parse", f"{base}^{{tree}}"):
        return base, ["head has the same tree as base: nothing to compare (local changes need --head .)"]
    if not succeeds(repo, "cat-file", "-e", f"{head}^{{commit}}"):
        return base, []
    if succeeds(repo, "merge-base", "--is-ancestor", head, base):
        return base, ["head is already part of base: for a merged change use --base <commit>^ --head <commit>"]
    found = git(repo, "merge-base", base, head, check=False).decode().strip()
    return found or base, []


@dataclass
class Finding:
    kind: str
    path: str
    detail: str
    soft: bool = False

    @property
    def blocking(self) -> bool:
        return self.kind in BLOCKING and not self.soft

    @property
    def verdict(self) -> str:
        return "MISPLACED" if self.blocking else "NEEDS-ANSWER"

    def render(self) -> str:
        return f"{self.kind} {self.path} — {self.verdict} — {self.detail}"


def placement_findings(layout: Layout, before: Census, after: Census, renames: dict[str, str],
                       changed: set[str]) -> list[Finding]:
    findings = []
    for path, row in sorted(after.rows.items()):
        prior = before.rows.get(renames.get(path, path))
        consumers = evidence_text(row)
        if prior is None:
            kind = {"SINGLE": "NEW_SINGLE", "NONE": "NEW_UNUSED", "ROOT": "NEW_ROOT"}.get(row.status)
            if kind:
                findings.append(Finding(kind, path, f"consumers: {consumers} — {action_text(row)}"))
        elif row.status in ("SINGLE", "NONE") and prior.status in STAYS:
            lost = sorted(set(prior.domains) - set(row.domains))
            if not lost:
                findings.append(Finding(
                    "REVEALED", path,
                    f"was {prior.status}, now {row.status} ({consumers}) with no consumer dropped: the change "
                    f"reshaped the code that needed it — {action_text(row)}",
                ))
                continue
            culprits = sorted(c for c in changed if layout.zone(c) in lost)
            findings.append(Finding(
                "LOST_SECOND", path,
                f"was {prior.status} ({evidence_text(prior)}), now {consumers}; dropped: {','.join(lost)}; "
                f"changed there: {', '.join(culprits[:5]) or '-'} — {action_text(row)}",
            ))
        elif row.status == "ROOT" and prior.status in ("SHARED", "KEEP"):
            findings.append(Finding("NOW_ROOT", path, f"was {prior.status} — {action_text(row)}"))
        elif row.status in ("SINGLE", "NONE") and path in changed and not row.planned:
            users = f"only {consumers} uses" if row.domains else "no domain uses"
            findings.append(Finding("TOUCHED_DEBT", path, f"edits a shared file {users} — {action_text(row)}"))
        elif row.status == "JUSTIFIED" and row.would_be in ("SINGLE", "NONE") and prior.status == "JUSTIFIED" and prior.would_be in ("SHARED", "KEEP"):
            findings.append(Finding(
                "JUSTIFIED_LOST", path,
                f"listed as justified ({row.why}); without the line it went from {prior.would_be} to {row.would_be} ({consumers}): does the reason still hold?",
            ))
    return findings


def edge_findings(before: Graph, after: Graph, renames: dict[str, str]) -> list[Finding]:
    layout = after.layout
    old = {(e.source, e.target) for edges in before.outgoing.values() for e in edges.values()}
    findings = []
    for source in sorted(after.outgoing):
        source_zone = layout.zone(source)
        if source_zone is None or source_zone in (WIRING_ZONE, ROOT_ZONE, OTHER_ZONE):
            continue
        old_source = renames.get(source, source)
        for edge in after.outgoing[source].values():
            target_zone = layout.zone(edge.target)
            if not target_zone or target_zone.startswith("@") or target_zone == source_zone:
                continue
            old_target = renames.get(edge.target, edge.target)
            unchanged = layout.zone(old_target) == target_zone and layout.zone(old_source) == source_zone
            if (old_source, old_target) in old and unchanged:
                continue
            if source_zone == SHARED_ZONE:
                findings.append(Finding("UPWARD", edge.evidence, f"shared code imports the {target_zone} domain ({edge.target})"))
            else:
                findings.append(Finding("CROSS", edge.evidence, f"{source_zone} -> {target_zone} ({edge.target})"))
    return findings


def clash_findings(before: Graph, after: Graph) -> list[Finding]:
    old = before.clashes()
    return [
        Finding("CLASH", url, "one URL, several files: " + ", ".join(paths))
        for url, paths in sorted(after.clashes().items()) if url not in old
    ]


def export_findings(before: Census, after: Census, renames: dict[str, str], changed: set[str]) -> list[Finding]:
    kind = "EXPORT" if after.layout.unit == "export" else "EXPORT_ASK"
    findings = []
    for path, row in sorted(after.rows.items()):
        if path not in changed:
            continue
        old_path = renames.get(path, path)
        prior = before.rows.get(old_path)
        existed = set(before.graph.value_exports(old_path))
        lines = []
        for name, domains in after.lonely_exports(row).items():
            was = prior.exports.get(name) if prior else None
            if was is not None:
                if len(was) < 2 and not {"shared", "root"} & set(was):
                    continue
                lines.append(f"{name} (was {','.join(was)}, now {domains[0]})")
            elif name not in existed:
                lines.append(f"{name} (new, {domains[0]})")
        if lines:
            findings.append(Finding(kind, path, "exports only one domain uses: " + "; ".join(lines)))
    return findings


def head_justified(repo: Path, layout: Layout, head: str, config_arg: str | None) -> dict[str, str]:
    if layout.inferred or (config_arg and Path(config_arg).is_file()):
        return {}
    text = read_at(repo, head, config_arg or CONFIG_PATH)
    if not text:
        return {}
    before = {e["path"] for e in layout.raw.get("justified", [])}
    return {e["path"]: e.get("why", "") for e in json.loads(text).get("justified", []) if e["path"] not in before}


def settle_justified(findings: list[Finding], added: dict[str, str]) -> list[Finding]:
    patterns = [(compile_glob(p), p, why) for p, why in added.items()]
    settled = []
    covered = set()
    for finding in findings:
        path = finding.path.split(":", 1)[0]
        movable = finding.kind in ("NEW_SINGLE", "NEW_UNUSED", "LOST_SECOND", "NEW_ROOT", "REVEALED")
        why = justification(patterns, path) if movable else None
        if why is None:
            settled.append(finding)
            continue
        covered.add(next(p for rx, p, _ in patterns if rx.match(path)))
        settled.append(Finding("NEW_JUSTIFIED", path, f"{finding.kind} turned into a decision by this change: {why or 'no reason given'}"))
    settled += [Finding("NEW_JUSTIFIED", p, why or "no reason given") for p, why in added.items() if p not in covered]
    return settled


def suggested(findings: list[Finding], touched: bool) -> str:
    if any(f.blocking for f in findings):
        return "REQUEST CHANGES"
    if findings:
        return "PASS WITH QUESTIONS"
    return "PASS" if touched else "PASS — no placement changes"


def cmd_diff(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    base, warnings = compare_base(repo, args.base, args.head)
    before_graph, before_source = load(repo, base, args.config)
    layout = before_graph.layout
    after_graph, after_source = load(repo, args.head, args.config, layout=layout)
    before = Census(before_graph)
    after = Census(after_graph)
    renames, changed, deleted = changed_files(repo, base, args.head)
    findings = placement_findings(layout, before, after, renames, changed)
    findings += edge_findings(before_graph, after_graph, renames)
    findings += clash_findings(before_graph, after_graph)
    if layout.unit == "export" or layout.ask_exports:
        findings += export_findings(before, after, renames, changed)
    findings += [
        Finding("RULES_EDITED", path, "edits the placement rules; they apply from the next PR. Do they match what the team decided?")
        for path in sorted(changed & layout.rule_files())
    ]
    findings = settle_justified(findings, head_justified(repo, layout, args.head, args.config))
    if layout.inferred:
        warnings.append("layout guessed: no finding blocks until .claude/domain-placement.json exists")
        for finding in findings:
            finding.soft = True
    warnings += after.warnings
    touched_planned = sorted(
        f"{p} ({after.rows[p].planned.get('ticket', 'planned')})"
        for p in changed if p in after.rows and after.rows[p].planned and after.rows[p].status in VIOLATIONS
    )
    moved_out = sorted((old, new) for new, old in renames.items() if layout.is_shared(old) and not layout.is_shared(new))
    removed = sorted(p for p in deleted if layout.is_shared(p))
    touched = any(layout.is_shared(p) for p in changed) or any(f.kind in ("CROSS", "UPWARD") for f in findings)
    verdict = suggested(findings, touched)
    blocking = sum(f.blocking for f in findings)
    if args.json:
        print(json.dumps({
            "base": before_source.label(),
            "head": after_source.label(),
            "config": layout.origin,
            "unit": layout.unit,
            "warnings": warnings,
            "suggested_verdict": verdict,
            "findings": [{**{k: v for k, v in f.__dict__.items() if k != "soft"}, "blocking": f.blocking, "verdict": f.verdict} for f in findings],
            "touches_planned_debt": touched_planned,
            "moved_out_of_shared": [{"from": o, "to": n} for o, n in moved_out],
            "removed_from_shared": removed,
            "changed_shared": [
                {k: v for k, v in after.rows[p].as_json().items() if k in ("path", "status", "domains", "move_to", "planned")}
                for p in sorted(changed) if p in after.rows
            ],
        }, indent=1))
    else:
        print(f"DIFF: base {before_source.label()} head {after_source.label()} — config {layout.origin} — unit {layout.unit}")
        for warning in warnings:
            print(f"WARNING: {warning}")
        print(f"suggested verdict: {verdict} — {blocking} blocking, {len(findings) - blocking} questions")
        for finding in findings:
            print(finding.render())
        if touched_planned:
            print("touches planned debt (not a finding): " + ", ".join(touched_planned))
        for old, new in moved_out:
            print(f"moved out of shared: {old} -> {new}")
        for path in removed:
            print(f"removed from shared: {path}")
    return 1 if blocking else 0


def cmd_layout(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    graph, source = load(repo, args.ref, args.config)
    layout = graph.layout
    zones: Counter = Counter()
    for path in source.paths:
        zone = layout.zone(path)
        if zone and path.endswith(SCANNED_EXT):
            zones[zone] += 1
    print(json.dumps({
        "config": layout.origin,
        "effective": layout.raw,
        "aliases": graph.aliases,
        "code_files_by_zone": dict(sorted(zones.items(), key=lambda kv: (-kv[1], kv[0]))),
        "url_clashes": graph.clashes(),
        "warnings": Census(graph).warnings,
    }, indent=1))
    return 0


def main(argv: list[str] | None = None) -> int:
    sys.setrecursionlimit(10000)
    parser = argparse.ArgumentParser(prog="consumers.py")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("census", "layout"):
        p = sub.add_parser(name)
        p.add_argument("--repo", default=".")
        p.add_argument("--ref", default="HEAD")
        p.add_argument("--config")
        if name == "census":
            p.add_argument("--scope")
            p.add_argument("--all", action="store_true")
            p.add_argument("--json", action="store_true")
            p.add_argument("--unit", choices=("file", "export"))
            p.add_argument("--strict", action="store_true")
            p.add_argument("--ticket")
    p = sub.add_parser("diff")
    p.add_argument("--repo", default=".")
    p.add_argument("--base", required=True)
    p.add_argument("--head", default="HEAD")
    p.add_argument("--config")
    p.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    handlers = {"census": cmd_census, "diff": cmd_diff, "layout": cmd_layout}
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
