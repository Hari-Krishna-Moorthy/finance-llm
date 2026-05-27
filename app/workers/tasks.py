from .celery_app import celery_app
from ..database import SessionLocal
from ..services.ingestion import process_file, process_markdown_text
from ..services.upload_tracking import mark_statement_upload_processed

@celery_app.task(name="process_statement_task")
def process_statement_task(file_path: str, account_id: int, upload_id: int, password: str = None):
    db = SessionLocal()
    try:
        process_file(file_path, account_id, password=password)
        mark_statement_upload_processed(db, upload_id, True, None)
        return {"status": "success", "file": file_path}
    except Exception as e:
        mark_statement_upload_processed(db, upload_id, False, str(e))
        return {"status": "error", "message": str(e), "file": file_path}
    finally:
        db.close()

@celery_app.task(name="process_markdown_task")
def process_markdown_task(text: str, account_id: int):
    try:
        process_markdown_text(text, account_id)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
