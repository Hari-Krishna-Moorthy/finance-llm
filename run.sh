#!/bin/bash

# Handle flags
if [[ "$1" == "--scan" ]]; then
    echo "Starting manual US stock market scan..."
    ./scripts/migrate.sh
    ./venv/bin/python3 scripts/manual_scan.py
    exit 0
fi

# Run migrations first
./scripts/migrate.sh

# Start both processes
echo "Starting all processes..."

# Use traps to ensure both are killed on Ctrl+C
trap "kill 0" EXIT

./scripts/start_app.sh &
./scripts/start_worker.sh &

wait
