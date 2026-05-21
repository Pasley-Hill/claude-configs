# Update README

Review the project and update README.md with missing folder patterns, agents, and slash commands.

## Instructions

### 1. Scan Project Structure

Inventory the current state:

```bash
# List top-level directories
ls -d */ 2>/dev/null | grep -v node_modules | grep -v __pycache__ | grep -v .git

# List Claude Code agents
ls .claude/agents/*.md 2>/dev/null

# List Claude Code slash commands
ls .claude/commands/*.md 2>/dev/null
```

### 2. Read Current README

Read `README.md` and extract:
- Documented folder descriptions
- Listed agents in the Agents table
- Listed commands in the Slash Commands table

### 3. Identify Gaps

Compare what exists vs what's documented:

**Folders:**
- Check each top-level directory has a description or is mentioned
- Ignore standard folders like `.git`, `node_modules`, `__pycache__`

**Agents:**
- Compare `.claude/agents/*.md` files against the Agents table
- For each agent file, read its `name` and `description` from frontmatter

**Slash Commands:**
- Compare `.claude/commands/*.md` files against the Slash Commands table
- For each command file, read its title and purpose

### 4. Update README.md

Add any missing items:

**For missing folders:** Add to an appropriate section (create "Project Structure" section if needed)

**For missing agents:** Add row to the Agents table:
```markdown
| `agent-name` | Brief description from the agent's frontmatter |
```

**For missing slash commands:** Add row to the Slash Commands table:
```markdown
| `/command-name` | Brief description from the command file |
```

### 5. Report Results

Summarize:
- What folders were added/updated
- What agents were added to the table
- What slash commands were added to the table
- If nothing was missing, confirm README is up to date
