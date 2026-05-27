from .celery_app import celery_app
from ..services.ingestion import process_file
import os

@celery_app.task(name="process_statement_task")
def process_statement_task(file_path: str, account_id: int):
    try:
        process_file(file_path, account_id)
        # Optionally delete the file after processing
        # os.remove(file_path)
        return {"status": "success", "file": file_path}
    except Exception as e:
        return {"status": "error", "message": str(e), "file": file_path}
