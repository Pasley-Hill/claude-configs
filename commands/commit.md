# Commit Changes

Collect changes, create a commit, then push or open PR.

## Instructions

### 1. Gather Changes

Run these in parallel:
- `git status` - see modified/untracked files
- `git diff --stat` - summary of changes
- `git diff` - full diff for context
- `git log -3 --oneline` - recent commits for context

### 2. Stage Changes

If there are untracked files, ask user which to include. Stage relevant files with `git add`.

### 3. Create Commit

Write a comprehensive commit message with subject and body:

**Subject line:**
- ~50 chars, lowercase, no period
- What changed (e.g., "add file upload endpoint")

**Body (after blank line):**
- Why this change was made
- Key implementation details worth noting
- Any tradeoffs or decisions made
- Related issues/context if relevant

**Example:**
```
add file upload endpoint

Users needed a way to attach files directly from mobile. Uses S3
presigned URLs for direct browser upload, avoiding server as
middleman. Chose multipart upload for files >5MB to handle spotty
cellular connections gracefully.
```

Commit using heredoc for proper formatting:
```bash
git commit -m "$(cat <<'EOF'
subject line here

Body paragraph explaining why and any notable details.
EOF
)"
```

### 4. Ask Destination

Use AskUserQuestion to ask:
- **Push to current branch** - direct push to remote
- **Create PR** - push to branch, open PR against `{MAIN_BRANCH}`

### 5. Execute

**If push:**
```bash
git push origin HEAD
```

**If PR:**
1. Push branch: `git push -u origin HEAD`
2. Create PR with `gh pr create`:
   - Title = commit message
   - Body = brief summary of changes
   - Target = `{MAIN_BRANCH}`

### 6. Report

Show:
- Commit hash
- Files changed
- Push/PR URL
