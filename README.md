# claude-configs

My personal [Claude Code](https://claude.com/claude-code) configuration: reusable skills, subagents, slash commands, and coding standards I share across projects.

## Layout

| Dir | What's in it |
|-----|--------------|
| `skills/` | Skills (each a `SKILL.md`): `commit`, `frontend-design`, `github-cli`, `grill-me`, `mac-tailscale`, `quiz-me`, `tailwind-plus-app-ui`, `trello`, `trello-task` |
| `plugins/` | Vendored Claude Code plugins: `frontend-design` (from anthropics/claude-plugins-official) |
| `agents/` | Subagents: `flutter-master`, `vanilla-frontend-master`, `grammar-master`, `python-master`, plus a five-stage build pipeline (Uncle Bob style) run in order: `pipeline-specifier` → `pipeline-coder` → `pipeline-cleaner` → `pipeline-hardener` → `pipeline-qa`. Stages hand off through `.pipeline/<slug>/handoff.md` |
| `commands/` | Slash commands: `aws`, `build-apk`, `changelog`, `commit`, `create-migration`, `create-mockup`, `deploy-app`, `update-readme`, `upload-mockups` |
| `standards/` | Coding standards (e.g. `never-nester`) |
| `designs/` | Reusable design docs / stack templates (e.g. `vite-vanilla-fastapi`) |
| `opencode/` | Machine-global [opencode](https://opencode.ai) config (`opencode.jsonc`), plus `agents/`: opencode copies of the pipeline agents (model written as `anthropic/<id>`). Keep them in step with `agents/` |

## Usage

Symlink or copy entries into a project's `.claude/` (or `~/.claude/`):

```bash
ln -sfn "$PWD/skills/commit" ~/.claude/skills/commit
ln -sfn "$PWD/agents/python-master.md" ~/.claude/agents/python-master.md
ln -sfn "$PWD/commands/aws.md" ~/.claude/commands/aws.md
```

Pi (machine-global):

```bash
ln -sfn "$PWD/skills/commit" ~/.pi/agent/skills/commit
```

opencode (machine-global):

```bash
mkdir -p ~/.config/opencode/agents ~/.config/opencode/commands
ln -sfn "$PWD/agents/python-master.md" ~/.config/opencode/agents/python-master.md
ln -sfn "$PWD/opencode/agents/pipeline-coder.md" ~/.config/opencode/agents/pipeline-coder.md
ln -sfn "$PWD/commands/aws.md" ~/.config/opencode/commands/aws.md
# skills also auto-load from ~/.claude/skills and ~/.agents/skills
# restart opencode after changing config
```

## Skills with prerequisites

`quiz-me` builds a local flashcard and quiz app for learning a repo or topic.
Run `/quiz-me` with a topic, or with nothing to cover the whole project. It
needs Python 3.9+ and Node with `npx` (it serves the app with Vite 8, fetched on
first run). It writes to a `.quiz-me/` folder that git ignores, and saves
progress in the browser.

```bash
ln -sfn "$PWD/skills/quiz-me" ~/.claude/skills/quiz-me
```

`tailwind-plus-app-ui` drives the [Tailwind Plus](https://tailwindcss.com/plus)
Application UI v4 HTML components. Those are licensed, so only the tooling and
the component index live here — the download itself does not. Install it
separately and point the skill at it:

```bash
export TAILWIND_PLUS_UI=/path/to/application-ui-v4   # the folder containing html/
python3 skills/tailwind-plus-app-ui/scripts/tpui.py list   # verify
```

Without `$TAILWIND_PLUS_UI` it falls back to `~/repos/application-ui-v4`, and
tells you what to fix if neither is there.

`trello` (update an existing card) and `trello-task` (write and push a new one)
drive Trello boards through one standard-library CLI,
`skills/trello/scripts/trello_update.py`, so there is no venv. Each person uses
their **own** Trello key and token, since every write lands under that person's name:

```bash
ln -sfn "$PWD/skills/trello" ~/.claude/skills/trello
ln -sfn "$PWD/skills/trello-task" ~/.claude/skills/trello-task
python3 ~/.claude/skills/trello/scripts/trello_update.py setup
```

`setup` walks through whatever is missing. It gives the exact clicks on
trello.com to get a key and token, the commands that save them to
`~/.config/trello/credentials` (outside every repo, `chmod 600`), and then the
command that sets your default board. `... trello_update.py boards` lists every
board you can reach. To use another board for one command, add
`TRELLO_BOARD=<short id or part of its name>`. Offline tests:
`python3 -m unittest discover -s skills/trello/scripts`.
