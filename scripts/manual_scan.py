import os
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.workers.tasks import scan_us_markets_task

def run_manual_scan():
    print("Starting manual US stock market scan...")
    # Trigger the task logic directly (or via delay if celery is running)
    # Since we want immediate results for verification, we run it synchronously.
    result = scan_us_markets_task()
    print(f"Scan complete. Result: {result}")

if __name__ == "__main__":
    run_manual_scan()
