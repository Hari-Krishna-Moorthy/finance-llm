#!/bin/bash
echo "Starting Celery worker..."
./venv/bin/celery -A app.workers.celery_app.celery_app worker --loglevel=info
