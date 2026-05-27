#!/bin/bash

# Run migrations first
./scripts/migrate.sh

# Start both processes
echo "Starting all processes..."

# Use traps to ensure both are killed on Ctrl+C
trap "kill 0" EXIT

./scripts/start_app.sh &
./scripts/start_worker.sh &

wait
