from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, SessionLocal
from app.models import Account, Transaction
from app.services.ingestion import process_markdown_text
import unittest.mock as mock

def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()

@mock.patch("app.services.ingestion.SessionLocal")
def test_process_markdown_text_table(mock_session_local):
    db = _make_session()
    mock_session_local.return_value = db
    
    acc = Account(name="HDFC", account_type="Checking")
    db.add(acc)
    db.commit()
    acc_id = acc.id
    
    markdown = """
| Date | Description | Amount |
|------|-------------|--------|
| 27/05/2026 | Groceries | 500.00 |
| 28/05/2026 | Internet | 1200.00 |
"""
    
    process_markdown_text(markdown, acc_id)
    
    transactions = db.query(Transaction).filter(Transaction.account_id == acc_id).all()
    assert len(transactions) == 2
    assert transactions[0].description == "Groceries"
    assert transactions[0].amount == Decimal("500.00")
    assert transactions[1].description == "Internet"
    assert transactions[1].amount == Decimal("1200.00")

@mock.patch("app.services.ingestion.SessionLocal")
def test_process_markdown_text_csv_style(mock_session_local):
    db = _make_session()
    mock_session_local.return_value = db
    
    acc = Account(name="SBI", account_type="Savings")
    db.add(acc)
    db.commit()
    acc_id = acc.id
    
    csv_style = """
Date\tDescription\tAmount
27/05/2026\tSalary\t50000.00
28/05/2026\tRent\t15000.00
"""
    
    process_markdown_text(csv_style, acc_id)
    
    transactions = db.query(Transaction).filter(Transaction.account_id == acc_id).all()
    assert len(transactions) == 2
    assert any(t.description == "Salary" for t in transactions)
    assert any(t.description == "Rent" for t in transactions)
