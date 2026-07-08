---
name: github-cli
description: Create, update, and manage GitHub repos, issues, PRs, and Projects via the gh CLI. Use whenever the user says "create this github repo", "make a repo", "open a PR", "create an issue", "set up a github project", or otherwise wants to manage GitHub from the terminal. Assumes the already-logged-in gh user.
model: opus

---

# GitHub via gh CLI

Manage GitHub using the `gh` CLI as the already-authenticated user. Do **not** ask for credentials, tokens, or which account — use the logged-in user. If a command fails with an auth error, tell the user to run `gh auth login` (suggest `! gh auth login`) and stop.

## First step

Confirm gh is available and authed (cheap, safe):

```bash
gh auth status
```

Use the returned login as the repo owner unless the user names an org/owner.

## Creating a repo

When the user says "create this github repo" (or similar), default to creating a repo for the **current directory** and pushing existing code.

```bash
# from inside the project dir — creates remote, sets origin, pushes
gh repo create <name> --source=. --remote=origin --push --private
```

Defaults & rules:
- **Private by default.** Only use `--public` if the user says public/open-source.
- `<name>` defaults to the current directory name unless the user gives one.
- If no commits yet, `git init`, stage, and make an initial commit first, then create.
- For a brand-new empty repo (no local dir): `gh repo create <owner>/<name> --private --clone`.
- Add `--description "..."` when the user gives one.

After creating, print the repo URL (`gh repo view --web --json url -q .url` or just `gh repo view`).

## Common operations

```bash
# Repos
gh repo view [<owner>/<name>]              # details
gh repo list [<owner>] --limit 50          # list
gh repo edit --description "..." --visibility private --accept-visibility-change-consequences
gh repo delete <owner>/<name> --yes        # DESTRUCTIVE — confirm with user first

# Issues
gh issue create --title "..." --body "..." [--label bug --assignee @me]
gh issue list [--state open --label bug]
gh issue view <n>  /  gh issue close <n>  /  gh issue comment <n> --body "..."

# Pull requests
gh pr create --title "..." --body "..." [--base main --draft]
gh pr list  /  gh pr view <n>  /  gh pr checkout <n>
gh pr merge <n> --squash --delete-branch   # confirm merge strategy if unclear
gh pr comment <n> --body "..."

# Releases
gh release create <tag> --title "..." --notes "..."
```

## GitHub Projects (v2)

Projects v2 uses the `gh project` subcommands and needs the `project` scope. If a command errors about scope, tell the user to run `! gh auth refresh -s project,read:project`.

```bash
gh project list --owner <owner>                       # --owner @me for personal
gh project create --owner <owner> --title "..."
gh project view <number> --owner <owner>
gh project item-add <number> --owner <owner> --url <issue-or-pr-url>
gh project item-list <number> --owner <owner>
gh project field-list <number> --owner <owner>
gh project item-edit --id <item-id> --field-id <id> --project-id <id> --text "..."
```

Project numbers are per-owner; resolve with `gh project list` first when the user names a project by title.

## Conventions

- **Destructive actions** (`repo delete`, `pr merge`, `release delete`, force-push): confirm with the user first, even though gh has `--yes`.
- Prefer `--json <fields> -q <jq>` for machine-readable output when chaining commands.
- When the user is vague ("make a repo"), pick sensible defaults (private, current dir name, push existing code) and state what you chose rather than asking — but confirm before anything destructive or public.
- For scriptable bulk work or anything `gh` lacks a command for, use `gh api` against the REST/GraphQL endpoints.
