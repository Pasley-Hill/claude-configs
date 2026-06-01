---
name: commit
description: Collect changes, write a well-formed git commit, then push or open a PR. Use when the user says "commit", "commit this", "commit and push", "commit and open a PR", or otherwise wants their working changes committed.
---

# Commit Changes

Collect changes, create a commit, then push or open a PR.

## 1. Gather changes

Run in parallel:
- `git status` — modified/untracked files
- `git diff --stat` — summary
- `git diff` — full diff for context
- `git log -3 --oneline` — recent commits (match their style)

## 2. Stage changes

If there are untracked files, ask the user which to include. Stage relevant files with `git add`. Don't blindly `git add -A`.

## 3. Create commit

Write a commit message with subject and body.

**Subject line:**
- ~50 chars, lowercase, no trailing period
- What changed (e.g. "add user photo upload endpoint")

**Body (after blank line):**
- Why this change was made
- Key implementation details worth noting
- Any tradeoffs or decisions
- Related issues/context if relevant

**Example:**
```
add user photo upload endpoint

Users needed to attach photos directly from mobile. Uses presigned
S3 URLs for direct browser upload, avoiding the server as middleman.
Multipart upload for files >5MB to handle spotty connections.
```

Commit using a heredoc for proper formatting:
```bash
git commit -m "$(cat <<'EOF'
subject line here

Body paragraph explaining why and any notable details.
EOF
)"
```

Match the existing repo's commit conventions if `git log` shows a clear pattern (e.g. Conventional Commits, trailers). Only add a Co-Authored-By / tool trailer if the repo already uses one or the user asks.

## 4. Branch safety

If on the default branch (`main`/`master`) and about to open a PR, create a topic branch first (`git checkout -b <descriptive-name>`). A direct push to the current branch is fine when the user explicitly wants it.

## 5. Ask destination

Use AskUserQuestion:
- **Push to current branch** — direct push to remote
- **Create PR** — push branch, open PR against the default branch

Skip the question if the user already said which they want.

## 6. Execute

**Push:**
```bash
git push origin HEAD
```

**PR:**
```bash
git push -u origin HEAD
gh pr create --fill   # or --title/--body; target the default branch
```

## 7. Report

Show: commit hash, files changed, and the push/PR URL.
