# Update Changelog

Generate a changelog entry from commits in `{DEV_BRANCH}` that aren't in `{RELEASE_BRANCH}` and append to a JSON changelog file.

> **PROJECT-SPECIFIC: replace `{DEV_BRANCH}`, `{RELEASE_BRANCH}`, and `{CHANGELOG_PATH}` with project values.**

## Instructions

### 1. Get New Commits

```bash
git log {RELEASE_BRANCH}..{DEV_BRANCH} --oneline --no-merges
```

If no commits found, inform user and stop.

### 2. Get Commit Details

```bash
git log {RELEASE_BRANCH}..{DEV_BRANCH} --no-merges --format="%s%n%b"
```

### 3. Read Current Changelog

Read `{CHANGELOG_PATH}` to get the latest version.

### 4. Determine New Version

Parse the latest version (e.g., "0.10.0"). Bump minor version by default:
- 0.10.0 → 0.11.0
- 0.9.9 → 0.10.0

Ask the user if they'd prefer a patch or major bump.

Use today's date in YYYY-MM-DD format.

### 5. Generate Changes

Write 3-8 changelog entries for **non-technical users** (the project's actual customers).

**Audience:** People who don't know what APIs, endpoints, schemas, or databases are. Write like you're explaining to a customer what's new.

**Format:** `Feature name: What you can now do`

**Rules:**
- Describe the benefit, not the implementation
- Use plain English a customer would understand
- Start with the feature name, then explain what it does
- Combine related commits into single entries
- Skip pure code refactors, dependency updates, internal fixes
- One line per entry

**Good examples:**
- "Video playback: Watch walkthrough videos right on the detail page"
- "Swipe to delete: Remove drafts by swiping left on your phone"
- "Faster photo uploads: Photos now upload in the background while you keep working"
- "Inline editing: Change pricing directly from the list view"

**Bad examples:**
- "Refactored photo upload service" (technical jargon)
- "Added PUT endpoint for pricing" (users don't know what endpoints are)
- "Fixed null pointer in match metadata" (meaningless to users)
- "Schema validation improvements" (what does this enable?)

### 6. Update Changelog

Prepend new entry to the array in `{CHANGELOG_PATH}`:

```json
{
  "version": "0.11.0",
  "date": "YYYY-MM-DD",
  "changes": [
    "Feature: Description of change"
  ]
}
```

### 7. Show Results

Display:
- New version number
- Number of commits summarized
- Generated changelog entries
- Remind user to review before committing
