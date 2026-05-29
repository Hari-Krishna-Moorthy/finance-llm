#!/bin/bash

# Load .env file
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

DB_URL=${DATABASE_URL:-"postgresql://postgres:postgres@localhost/finance_db"}

# Find pg_dump (Local or Docker)
USE_DOCKER=false
DOCKER_CONTAINER=""

if command -v pg_dump >/dev/null 2>&1; then
    PG_DUMP_CMD="pg_dump"
elif [ -x "/opt/homebrew/opt/postgresql@14/bin/pg_dump" ]; then
    PG_DUMP_CMD="/opt/homebrew/opt/postgresql@14/bin/pg_dump"
elif [ -x "/opt/homebrew/bin/pg_dump" ]; then
    PG_DUMP_CMD="/opt/homebrew/bin/pg_dump"
elif [ -x "/usr/local/bin/pg_dump" ]; then
    PG_DUMP_CMD="/usr/local/bin/pg_dump"
else
    # Check if a postgres docker container is running
    if command -v docker >/dev/null 2>&1; then
        DOCKER_CONTAINER=$(docker ps --filter "ancestor=timescale/timescaledb-postgis:latest-pg11" --filter "ancestor=postgres" --format "{{.Names}}" --format "{{.Names}}" | head -n 1)
        if [ -n "$DOCKER_CONTAINER" ]; then
            USE_DOCKER=true
            echo "Local pg_dump not found. Falling back to Docker container: $DOCKER_CONTAINER"
        else
            echo "pg_dump not found locally and no postgres Docker container is running! Cannot create backup."
            exit 1
        fi
    else
        echo "pg_dump and docker not found! Cannot create backup."
        exit 1
    fi
fi

BACKUP_FILE="database_backup.sql"

echo "Creating database backup..."
if [ "$USE_DOCKER" = true ]; then
    docker exec "$DOCKER_CONTAINER" pg_dump "$DB_URL" > "$BACKUP_FILE"
else
    $PG_DUMP_CMD "$DB_URL" > "$BACKUP_FILE"
fi

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
