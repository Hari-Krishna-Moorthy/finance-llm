from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Account, Transaction
from app.services.analytics import detect_anomalies, predict_future_payments

def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()

def test_detect_anomalies():
    db = _make_session()
    acc = Account(name="Test", account_type="Checking")
    db.add(acc)
    db.commit()
    
    # Add many normal transactions
    for i in range(20):
        t = Transaction(
            date=date(2026, 5, 1),
            amount=Decimal("100"),
            transaction_type="Debit",
            account_id=acc.id,
            description=f"Normal {i}"
        )
        db.add(t)
    
    # Add one anomaly
    anomaly = Transaction(
        date=date(2026, 5, 10),
        amount=Decimal("5000"),
        transaction_type="Debit",
        account_id=acc.id,
        description="Big Spend"
    )
    db.add(anomaly)
    db.commit()
    
    anomalies = detect_anomalies(db, acc.id)
    assert len(anomalies) == 1
    assert anomalies[0]["description"] == "Big Spend"

def test_predict_future_payments():
    db = _make_session()
    acc = Account(name="Test", account_type="Checking")
    db.add(acc)
    db.commit()
    
    # Add 3 identical transactions (enough for prediction)
    for i in range(3):
        t = Transaction(
            date=date(2026, i+1, 1),
            amount=Decimal("1500"),
            transaction_type="Debit",
            account_id=acc.id,
            description="Netflix"
        )
        db.add(t)
    
    # Add 7 more random transactions to reach minimum 10
    for i in range(7):
        t = Transaction(
            date=date(2026, 5, i+1),
            amount=Decimal(str(100 + i)),
            transaction_type="Debit",
            account_id=acc.id,
            description=f"Misc {i}"
        )
        db.add(t)
    
    db.commit()
    
    predictions = predict_future_payments(db, acc.id)
    assert len(predictions) == 1
    assert predictions[0]["description"] == "Netflix"
    assert predictions[0]["amount"] == 1500.0
