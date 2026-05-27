#!/bin/bash
set -e

echo "Running database migrations..."
./venv/bin/python3 -m alembic upgrade head
echo "Migrations complete."
