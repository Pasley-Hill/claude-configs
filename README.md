# claude-configs

My personal [Claude Code](https://claude.com/claude-code) configuration: reusable skills, subagents, slash commands, and coding standards I share across projects.

## Layout

| Dir | What's in it |
|-----|--------------|
| `CLAUDE.md` | Machine-global Claude Code instructions (concise communication) |
| `skills/` | Skills (each a `SKILL.md`): `commit`, `create-admin-view`, `github-cli`, `grill-me` |
| `agents/` | Subagents: `flutter-master`, `frontend-master`, `grammar-master`, `python-master` |
| `commands/` | Slash commands: `aws`, `build-apk`, `changelog`, `commit`, `create-migration`, `create-mockup`, `deploy-app`, `trello-task`, `update-readme`, `upload-mockups` |
| `standards/` | Coding standards (e.g. `never-nester`) |
| `designs/` | Reusable design docs / stack templates (e.g. `vite-vanilla-fastapi`) |
| `opencode/` | Machine-global [opencode](https://opencode.ai) config (`COMMUNICATION.md` + `opencode.jsonc`) |

## Usage

Symlink or copy entries into a project's `.claude/` (or `~/.claude/`):

```bash
ln -s "$PWD/CLAUDE.md" ~/.claude/CLAUDE.md
ln -s "$PWD/skills/commit" ~/.claude/skills/commit
ln -s "$PWD/agents/python-master.md" ~/.claude/agents/python-master.md
ln -s "$PWD/commands/aws.md" ~/.claude/commands/aws.md
```

opencode (machine-global):

```bash
mkdir -p ~/.config/opencode
ln -s "$PWD/opencode/COMMUNICATION.md" ~/.config/opencode/COMMUNICATION.md
ln -s "$PWD/opencode/opencode.jsonc" ~/.config/opencode/opencode.jsonc
# restart opencode after changing config
```
