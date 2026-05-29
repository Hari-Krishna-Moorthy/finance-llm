#!/bin/bash

# Handle flags
if [[ "$1" == "--scan" ]]; then
    echo "Starting manual US stock market scan..."
    ./scripts/migrate.sh
    ./venv/bin/python3 scripts/manual_scan.py
    exit 0
fi

echo "Creating initial database backup on startup..."
./scripts/backup_db.sh

# Run migrations first
./scripts/migrate.sh

# Start both processes
echo "Starting all processes..."

# Use traps to ensure both are killed on Ctrl+C and backup is taken
cleanup() {
    echo "Shutting down applications..."
    echo "Creating final database backup..."
    ./scripts/backup_db.sh
    kill 0
}
trap cleanup EXIT

./scripts/start_app.sh &
./scripts/start_worker.sh &

wait
