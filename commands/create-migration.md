# Create Migration

Create a new database migration file with timestamp-based naming.

> **PROJECT-SPECIFIC: replace `{MIGRATIONS_DIR}` with the project's actual migrations directory and adjust the filename convention/SQL idioms to match the migration tool (Flyway, Alembic, Knex, Rails, etc.).**

## Arguments

- `$ARGUMENTS` - Description of what the migration does (e.g., "create users table")

## Naming Convention

Example (Flyway):

```
V{YYYYMMDD}_{HHMM}__{description}.sql
```

Examples:
- `V20260113_1430__create_users.sql`
- `V20260113_1445__add_email_to_users.sql`

Adapt to the project's own convention if different.

## Instructions

### 1. Generate Migration File

Create the migration file with current timestamp:

```bash
TIMESTAMP=$(date +%Y%m%d_%H%M)
MIGRATIONS_DIR="{MIGRATIONS_DIR}"
```

Convert the user's description to snake_case for the filename.

### 2. Create the File

Write the migration file to `$MIGRATIONS_DIR/V${TIMESTAMP}__${description}.sql`

### 3. Required Structure

Every migration MUST include (project convention — adjust per project):

```sql
-- Table comment
COMMENT ON TABLE table_name IS 'Description of the table purpose';

-- Column comments (for each column)
COMMENT ON COLUMN table_name.column_name IS 'Description of the column';
```

### 4. Standard Columns

Most tables should include these audit columns (project convention — adjust per project):

```sql
is_active BOOLEAN DEFAULT TRUE,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

### 5. Indexes

Add indexes for:
- Foreign key columns (`idx_{table}_{fk_column}`)
- Columns used in WHERE clauses
- Unique constraints that need fast lookups

### 6. Report Results

1. Show the full path of the created migration
2. List any foreign key dependencies
3. Remind user how to apply migrations locally (e.g. `docker compose down -v && docker compose up -d`, `alembic upgrade head`, etc. — fill in the project's command)
