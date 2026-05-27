from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Account, Category, Transaction
from app.services.reconciliation import reconcile_transfers

def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()

def test_reconcile_transfers():
    db = _make_session()
    
    # Setup accounts
    acc1 = Account(name="HDFC", account_type="Checking")
    acc2 = Account(name="SBI", account_type="Savings")
    db.add_all([acc1, acc2])
    db.commit()
    
    # Setup "Self transfer" category
    cat = Category(name="Self transfer")
    db.add(cat)
    db.commit()
    
    # Create matching transactions
    t1 = Transaction(
        date=date(2026, 5, 20),
        amount=Decimal("5000"),
        transaction_type="Debit",
        account_id=acc1.id,
        extra_details={"account_number": "123456"}
    )
    t2 = Transaction(
        date=date(2026, 5, 21), # Within 3 days
        amount=Decimal("5000"),
        transaction_type="Credit",
        account_id=acc2.id,
        extra_details={"account_number": "789012"}
    )
    
    db.add_all([t1, t2])
    db.commit()
    
    reconcile_transfers(db)
    
    db.refresh(t1)
    db.refresh(t2)
    
    assert t1.internal_transfer_id == t2.id
    assert t2.internal_transfer_id == t1.id
    assert t1.category_id == cat.id
    assert t2.category_id == cat.id

def test_reconcile_transfers_no_match_date():
    db = _make_session()
    acc1 = Account(name="HDFC", account_type="Checking")
    acc2 = Account(name="SBI", account_type="Savings")
    db.add_all([acc1, acc2])
    db.commit()
    
    t1 = Transaction(date=date(2026, 5, 10), amount=Decimal("5000"), transaction_type="Debit", account_id=acc1.id)
    t2 = Transaction(date=date(2026, 5, 20), amount=Decimal("5000"), transaction_type="Credit", account_id=acc2.id)
    
    db.add_all([t1, t2])
    db.commit()
    
    reconcile_transfers(db)
    
    db.refresh(t1)
    assert t1.internal_transfer_id is None

def test_reconcile_transfers_different_account_number_match():
    db = _make_session()
    acc1 = Account(name="HDFC", account_type="Checking")
    acc2 = Account(name="SBI", account_type="Savings")
    db.add_all([acc1, acc2])
    db.commit()
    
    # We relaxed the logic so different account numbers (or source/target mentioned) still match
    t1 = Transaction(
        date=date(2026, 5, 20), 
        amount=Decimal("5000"), 
        transaction_type="Debit", 
        account_id=acc1.id,
        extra_details={"account_number": "111"}
    )
    t2 = Transaction(
        date=date(2026, 5, 20), 
        amount=Decimal("5000"), 
        transaction_type="Credit", 
        account_id=acc2.id,
        extra_details={"account_number": "222"}
    )
    db.add_all([t1, t2])
    db.commit()
    
    reconcile_transfers(db)
    db.refresh(t1)
    assert t1.internal_transfer_id == t2.id
