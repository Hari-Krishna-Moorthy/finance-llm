from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Account
from app.services.upload_tracking import create_statement_upload, mark_statement_upload_processed


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def test_create_statement_upload_persists_expected_fields():
    db = _make_session()
    account = Account(name="Primary", account_type="Checking", currency="INR")
    db.add(account)
    db.commit()
    db.refresh(account)

    upload = create_statement_upload(
        db=db,
        file_path="/tmp/statement.pdf",
        account_id=account.id,
        has_password=True,
    )

    assert upload.id is not None
    assert upload.file_path == "/tmp/statement.pdf"
    assert upload.has_password is True
    assert upload.processed is False
    assert upload.account_id == account.id


def test_mark_statement_upload_processed_updates_status():
    db = _make_session()
    account = Account(name="Primary", account_type="Checking", currency="INR")
    db.add(account)
    db.commit()
    db.refresh(account)

    upload = create_statement_upload(
        db=db,
        file_path="/tmp/statement.pdf",
        account_id=account.id,
        has_password=False,
    )

    updated = mark_statement_upload_processed(db=db, upload_id=upload.id, processed=True)

    assert updated is not None
    assert updated.processed is True
    assert updated.processing_error is None
    assert updated.processed_at is not None
