#!/usr/bin/env python3
"""tpui - find, read, and scaffold Tailwind Plus Application UI v4 components.

The component library is a folder of licensed Tailwind Plus HTML files. This
script keeps you from grepping 364 files by hand and from retyping markup you
should be copying verbatim.

Library root resolution order:
  1. --root
  2. $TAILWIND_PLUS_UI
  3. ~/repos/application-ui-v4
The root is the folder that contains html/ (and possibly react/, vue/).

Commands:
  list [prefix]            list categories, or files under a category prefix
  search TERM [TERM ...]   rank components by path + content match
  show PATH                print a component, advisory header stripped
  requires PATH            print the <html>/<body> classes a component needs
  new SHELL --out FILE     scaffold a complete page around an application shell
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ELEMENTS_SCRIPT = (
    '<script src="https://cdn.jsdelivr.net/npm/@tailwindplus/elements@1" type="module"></script>'
)
CDN_SCRIPT = '<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>'

ADVISORY_RE = re.compile(
    r"\A(?:\s*<!--(?:(?!-->).)*-->\s*)+", re.DOTALL
)
HTML_TAG_RE = re.compile(r"^\s*(<html[^>]*>)\s*$", re.MULTILINE)
BODY_TAG_RE = re.compile(r"^\s*(<body[^>]*>)\s*$", re.MULTILINE)


def resolve_root(explicit: str | None) -> Path:
    candidates = [
        ("--root", explicit),
        ("$TAILWIND_PLUS_UI", os.environ.get("TAILWIND_PLUS_UI")),
        ("default", "~/repos/application-ui-v4"),
    ]
    for label, c in candidates:
        if not c:
            continue
        p = Path(c).expanduser()
        if (p / "html").is_dir():
            return p
        if p.name == "html" and p.is_dir():
            return p.parent
        # An explicitly named root that isn't there is a mistake worth reporting.
        # Falling through to another library would silently use the wrong one.
        if label != "default":
            sys.exit(f"{label} points at {p}, which has no html/ folder.")
    sys.exit(
        "Could not find the Tailwind Plus Application UI v4 library.\n"
        "It is licensed and is not bundled with this skill, so it has to be on the\n"
        "machine already. Point at it with either:\n"
        "  tpui.py --root /path/to/application-ui-v4 ...\n"
        "  export TAILWIND_PLUS_UI=/path/to/application-ui-v4\n"
        "The root is the folder that contains html/."
    )


def html_dir(root: Path) -> Path:
    return root / "html"


def all_components(root: Path) -> list[Path]:
    return sorted(html_dir(root).rglob("*.html"))


def rel(root: Path, p: Path) -> str:
    return str(p.relative_to(html_dir(root)))


def strip_advisory(text: str) -> str:
    """Drop the leading Tailwind Plus instruction comments, keep the markup."""
    return ADVISORY_RE.sub("", text, count=1).lstrip("\n")


def advisory(text: str) -> str:
    m = ADVISORY_RE.match(text)
    return m.group(0) if m else ""


def required_tags(text: str) -> tuple[str, str]:
    """Return the (<html ...>, <body ...>) the component's own note asks for."""
    head = advisory(text)
    html_m = HTML_TAG_RE.search(head)
    body_m = BODY_TAG_RE.search(head)
    return (
        html_m.group(1) if html_m else '<html lang="en" class="h-full">',
        body_m.group(1) if body_m else '<body class="h-full">',
    )


def needs_elements(text: str) -> bool:
    return "@tailwindplus/elements" in advisory(text) or re.search(r"<el-[a-z-]", text) is not None


# ---------------------------------------------------------------- commands


def cmd_list(args, root: Path) -> None:
    prefix = (args.prefix or "").strip("/")
    files = all_components(root)
    if not prefix:
        cats: dict[str, int] = {}
        for f in files:
            cat = "/".join(rel(root, f).split("/")[:2])
            cats[cat] = cats.get(cat, 0) + 1
        for cat, n in sorted(cats.items()):
            print(f"{cat}  ({n})")
        return
    hits = [rel(root, f) for f in files if rel(root, f).startswith(prefix)]
    if not hits:
        print(f"No components under '{prefix}'. Run `tpui.py list` for categories.")
        return
    for h in hits:
        print(h)


def cmd_search(args, root: Path) -> None:
    terms = [t.lower() for t in args.terms]
    scored = []
    for f in all_components(root):
        path = rel(root, f).lower()
        body = f.read_text(encoding="utf-8", errors="replace").lower()
        score = 0
        for t in terms:
            if t in path:
                score += 10
            score += min(body.count(t), 5)
        if score:
            scored.append((score, rel(root, f)))
    scored.sort(key=lambda x: (-x[0], x[1]))
    if not scored:
        print("No matches. Try `tpui.py list` to browse categories.")
        return
    for score, path in scored[: args.limit]:
        print(f"{score:4d}  {path}")


def cmd_show(args, root: Path) -> None:
    f = html_dir(root) / args.path
    if not f.is_file():
        sys.exit(f"No such component: {args.path}. Run `tpui.py search` to find it.")
    text = f.read_text(encoding="utf-8", errors="replace")
    print(strip_advisory(text) if not args.raw else text)


def cmd_requires(args, root: Path) -> None:
    f = html_dir(root) / args.path
    if not f.is_file():
        sys.exit(f"No such component: {args.path}")
    text = f.read_text(encoding="utf-8", errors="replace")
    h, b = required_tags(text)
    print(f"html: {h}")
    print(f"body: {b}")
    print(f"elements script needed: {'yes' if needs_elements(text) else 'no'}")


def cmd_new(args, root: Path) -> None:
    f = html_dir(root) / args.shell
    if not f.is_file():
        sys.exit(
            f"No such shell: {args.shell}\n"
            f"Run `tpui.py list application-shells` to see the options."
        )
    text = f.read_text(encoding="utf-8", errors="replace")
    html_tag, body_tag = required_tags(text)
    if 'lang=' not in html_tag:
        html_tag = html_tag.replace("<html", '<html lang="en"', 1)
    shell = strip_advisory(text).rstrip()

    head_lines = [
        '\t\t<meta charset="utf-8" />',
        '\t\t<meta name="viewport" content="width=device-width, initial-scale=1" />',
        f"\t\t<title>{args.title}</title>",
    ]
    if args.cdn:
        head_lines.append(f"\t\t{CDN_SCRIPT}")
    else:
        head_lines.append(f'\t\t<link rel="stylesheet" href="{args.css}" />')
    if needs_elements(text):
        head_lines.append(f"\t\t{ELEMENTS_SCRIPT}")

    doc = "\n".join(
        [
            "<!doctype html>",
            html_tag,
            "\t<head>",
            *head_lines,
            "\t</head>",
            body_tag,
            shell,
            "\t</body>",
            "</html>",
            "",
        ]
    )

    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    print(f"Wrote {out}")
    print(f"Shell: {args.shell}")
    print("Next: replace the nav items, logo, avatar and the `<!-- Your content -->` slot.")
    if not args.cdn:
        print(f"Stylesheet: {args.css} must be a Tailwind v4 build that @source-scans this file.")


def main() -> None:
    ap = argparse.ArgumentParser(prog="tpui.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", help="path to the application-ui-v4 folder")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="list categories or components")
    p.add_argument("prefix", nargs="?")
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("search", help="rank components by keyword")
    p.add_argument("terms", nargs="+")
    p.add_argument("--limit", type=int, default=15)
    p.set_defaults(fn=cmd_search)

    p = sub.add_parser("show", help="print a component")
    p.add_argument("path")
    p.add_argument("--raw", action="store_true", help="keep the advisory header comments")
    p.set_defaults(fn=cmd_show)

    p = sub.add_parser("requires", help="print the html/body classes a component needs")
    p.add_argument("path")
    p.set_defaults(fn=cmd_requires)

    p = sub.add_parser("new", help="scaffold a full page around an application shell")
    p.add_argument("shell", help="e.g. application-shells/sidebar/03-sidebar-with-header.html")
    p.add_argument("--out", required=True)
    p.add_argument("--title", default="Dashboard")
    p.add_argument("--css", default="/css/app.css", help="href of the compiled Tailwind v4 stylesheet")
    p.add_argument("--cdn", action="store_true", help="use the Tailwind v4 browser build instead")
    p.set_defaults(fn=cmd_new)

    args = ap.parse_args()
    args.fn(args, resolve_root(args.root))


if __name__ == "__main__":
    main()
