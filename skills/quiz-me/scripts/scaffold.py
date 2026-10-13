#!/usr/bin/env python3
"""Set up (or refresh) a .quiz-me study folder.

Copies the template app into <project root>/.quiz-me, makes the folder ignore
itself in git, and writes a Vite config with a port fixed for this project.
Existing decks are never touched.

usage: scaffold.py [path]    (default: current folder)
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "template"
APP_FILES = ("index.html", "app.js", "styles.css")
FOLDER = ".quiz-me"
VITE = "vite@8"
PORT_BASE = 5300
PORT_RANGE = 600

VITE_CONFIG = """// Written by the quiz-me skill. Port is fixed per project so progress
// (saved in the browser per address) survives restarts.
export default {{
	server: {{ port: {port}, strictPort: true }},
	preview: {{ port: {port}, strictPort: true }},
	// Inline PostCSS config stops Vite picking up the project's own.
	css: {{ postcss: {{}} }},
	clearScreen: false,
}};
"""

GITIGNORE = "# Temporary study folder made by the quiz-me skill.\n*\n"


def project_root(start: Path) -> tuple[Path, bool]:
    """Return the git root containing start, or start itself if not in a repo."""
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return start, False
    return Path(result.stdout.strip()), True


def port_for(root: Path) -> int:
    """Pick a stable port from the project path, so each project gets its own address."""
    digest = hashlib.sha1(str(root).encode()).hexdigest()
    return PORT_BASE + int(digest, 16) % PORT_RANGE


def install(target: Path, port: int) -> None:
    """Copy the app files in and write the per-project config."""
    (target / "decks").mkdir(parents=True, exist_ok=True)
    for name in APP_FILES:
        shutil.copy2(TEMPLATE / name, target / name)
    (target / "vite.config.mjs").write_text(VITE_CONFIG.format(port=port))
    (target / ".gitignore").write_text(GITIGNORE)


def main() -> int:
    parser = argparse.ArgumentParser(description="Set up a .quiz-me study folder.")
    parser.add_argument("path", nargs="?", default=".", help="folder to study (default: current folder)")
    args = parser.parse_args()

    start = Path(args.path).expanduser().resolve()
    if not start.is_dir():
        print(f"error: {start} is not a folder", file=sys.stderr)
        return 1

    root, in_git = project_root(start)
    target = root / FOLDER
    port = port_for(root)
    install(target, port)

    decks = sorted(path.name for path in (target / "decks").glob("*.json"))
    print(f"folder:  {target}")
    print(f"git:     {'ignored (folder has its own .gitignore)' if in_git else 'not a git repo'}")
    print(f"decks:   {', '.join(decks) if decks else 'none yet'}")
    print(f"url:     http://localhost:{port}/")
    print(f"serve:   npx --yes {VITE} {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
