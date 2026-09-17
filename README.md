# claude-configs

My personal [Claude Code](https://claude.com/claude-code) configuration: reusable skills, subagents, slash commands, and coding standards I share across projects.

## Layout

| Dir | What's in it |
|-----|--------------|
| `CLAUDE.md` | Machine-global Claude Code instructions (concise communication) |
| `AGENTS.md` | Same communication style for Pi (`~/.pi/agent/AGENTS.md`) |
| `skills/` | Skills (each a `SKILL.md`): `commit`, `frontend-design`, `github-cli`, `grill-me`, `mac-tailscale`, `tailwind-plus-app-ui` |
| `agents/` | Subagents: `flutter-master`, `frontend-master`, `grammar-master`, `python-master` |
| `commands/` | Slash commands: `aws`, `build-apk`, `changelog`, `commit`, `create-migration`, `create-mockup`, `deploy-app`, `trello-task`, `update-readme`, `upload-mockups` |
| `standards/` | Coding standards (e.g. `never-nester`) |
| `designs/` | Reusable design docs / stack templates (e.g. `vite-vanilla-fastapi`) |
| `opencode/` | Machine-global [opencode](https://opencode.ai) config (`COMMUNICATION.md` + `opencode.jsonc`) |

## Usage

Symlink or copy entries into a project's `.claude/` (or `~/.claude/`):

```bash
ln -sfn "$PWD/CLAUDE.md" ~/.claude/CLAUDE.md
ln -sfn "$PWD/skills/commit" ~/.claude/skills/commit
ln -sfn "$PWD/agents/python-master.md" ~/.claude/agents/python-master.md
ln -sfn "$PWD/commands/aws.md" ~/.claude/commands/aws.md
```

Pi (machine-global):

```bash
ln -sfn "$PWD/AGENTS.md" ~/.pi/agent/AGENTS.md
ln -sfn "$PWD/skills/commit" ~/.pi/agent/skills/commit
```

opencode (machine-global):

```bash
mkdir -p ~/.config/opencode/agents ~/.config/opencode/commands
ln -sfn "$PWD/opencode/COMMUNICATION.md" ~/.config/opencode/COMMUNICATION.md
# merge `"instructions": ["COMMUNICATION.md"]` into existing opencode.json; do not clobber it
ln -sfn "$PWD/agents/python-master.md" ~/.config/opencode/agents/python-master.md
ln -sfn "$PWD/commands/aws.md" ~/.config/opencode/commands/aws.md
# skills also auto-load from ~/.claude/skills and ~/.agents/skills
# restart opencode after changing config
```

## Skills with prerequisites

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
