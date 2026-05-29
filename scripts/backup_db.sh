#!/bin/bash

# Load .env file
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

DB_URL=${DATABASE_URL:-"postgresql://postgres:postgres@localhost/finance_db"}

# Find pg_dump
if command -v pg_dump >/dev/null 2>&1; then
    PG_DUMP_CMD="pg_dump"
elif [ -x "/opt/homebrew/opt/postgresql@14/bin/pg_dump" ]; then
    PG_DUMP_CMD="/opt/homebrew/opt/postgresql@14/bin/pg_dump"
elif [ -x "/opt/homebrew/bin/pg_dump" ]; then
    PG_DUMP_CMD="/opt/homebrew/bin/pg_dump"
elif [ -x "/usr/local/bin/pg_dump" ]; then
    PG_DUMP_CMD="/usr/local/bin/pg_dump"
else
    echo "pg_dump not found! Cannot create backup."
    exit 1
fi

BACKUP_FILE="database_backup.sql"

echo "Creating database backup..."
$PG_DUMP_CMD "$DB_URL" > "$BACKUP_FILE"

echo "Committing backup to GitHub..."
git add "$BACKUP_FILE"

# Only commit if there are changes
if git diff --staged --quiet; then
    echo "No changes in database backup to commit."
else
    git commit -m "chore: automated database backup [skip ci]"
    git push
    echo "Backup pushed to GitHub."
fi
