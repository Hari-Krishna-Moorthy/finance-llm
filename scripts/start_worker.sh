#!/bin/bash
echo "Starting Celery worker..."
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
./venv/bin/celery -A app.workers.celery_app.celery_app worker --loglevel=info
