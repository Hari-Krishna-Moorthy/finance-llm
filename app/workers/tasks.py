from .celery_app import celery_app
from ..services.ingestion import process_file, process_markdown_text
import os

@celery_app.task(name="process_statement_task")
def process_statement_task(file_path: str, account_id: int, password: str = None):
    try:
        process_file(file_path, account_id, password=password)
        return {"status": "success", "file": file_path}
    except Exception as e:
        return {"status": "error", "message": str(e), "file": file_path}

@celery_app.task(name="process_markdown_task")
def process_markdown_task(text: str, account_id: int):
    try:
        process_markdown_text(text, account_id)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
