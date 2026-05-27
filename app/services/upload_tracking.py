from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models import StatementUpload


def create_statement_upload(
    db: Session,
    file_path: str,
    account_id: int,
    has_password: bool,
) -> StatementUpload:
    upload = StatementUpload(
        file_path=file_path,
        account_id=account_id,
        has_password=has_password,
        processed=False,
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return upload


def mark_statement_upload_processed(
    db: Session,
    upload_id: int,
    processed: bool,
    processing_error: str | None = None,
) -> StatementUpload | None:
    upload = db.query(StatementUpload).filter(StatementUpload.id == upload_id).first()
    if not upload:
        return None

    upload.processed = processed
    upload.processed_at = datetime.now(timezone.utc) if processed else None
    upload.processing_error = processing_error
    db.commit()
    db.refresh(upload)
    return upload
