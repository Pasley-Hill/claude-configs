# Create Mockup

Create or update HTML mockups in today's versioned folder.

> **PROJECT-SPECIFIC: replace `{MOCKUPS_DIR}` with the project's actual mockups directory.**

## Arguments

- `$ARGUMENTS` - Description of the mockup to create or modify

## Folder Structure

```
{MOCKUPS_DIR}/
├── images/              # Shared images (do not duplicate)
├── 2026-01-12-v1/       # HTML files only
└── 2026-01-13-v1/       # HTML files only
```

**Important**: Images live in `images/` and are referenced via `../images/filename.png`. Never copy images into version folders.

## Instructions

### 1. Setup Today's Folder

First, determine today's date and check if a folder exists:

```bash
TODAY=$(date +%Y-%m-%d)
MOCKUPS_DIR="{MOCKUPS_DIR}"
TODAY_FOLDER=$(ls -d $MOCKUPS_DIR/${TODAY}-v* 2>/dev/null | sort -V | tail -1)
```

If no folder exists for today:

1. Find the most recent previous folder:
```bash
PREV_FOLDER=$(ls -d $MOCKUPS_DIR/????-??-??-v* 2>/dev/null | sort -V | tail -1)
```

2. Create today's folder with version 1:
```bash
mkdir -p $MOCKUPS_DIR/${TODAY}-v1
```

3. Copy all HTML files from the previous folder to today's folder:
```bash
cp $PREV_FOLDER/*.html $MOCKUPS_DIR/${TODAY}-v1/
```

4. Report which files were copied.

### 2. Create or Modify the Mockup

Based on the user's request in `$ARGUMENTS`:

1. Read the existing HTML mockups in today's folder to understand the design patterns
2. If modifying an existing mockup, read that file first
3. Create or update the HTML file following the established patterns:
   - Match existing styling conventions
   - Use consistent navigation and layout
   - Maintain responsive design patterns

### 3. Report Results

1. Confirm which folder is being used (created new or using existing)
2. List the mockup file(s) created or modified
3. Ask if the user wants to run `/upload-mockups` to sync to remote hosting
