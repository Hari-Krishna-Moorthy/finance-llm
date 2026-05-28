import os
# Fix for macOS fork crash in Celery (+[NSCharacterSet initialize] may have been in progress in another thread when fork() was called)
os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
# Fix for gRPC/Generative AI segfaults during process fork
os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "1"
os.environ["GRPC_POLL_STRATEGY"] = "epoll1"

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "finance_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.workers.tasks"]
)

from celery.schedules import crontab

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "hourly-market-scan": {
            "task": "scan_us_markets_task",
            "schedule": crontab(minute=0), # Every hour
        },
    },
)
