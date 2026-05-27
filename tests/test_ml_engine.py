from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Category, Transaction
from app.services.ml_engine import auto_categorize_transactions

def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()

def test_auto_categorize_transactions():
    db = _make_session()
    
    # Setup categories
    cat_dining = Category(name="Dining")
    cat_shopping = Category(name="Shopping")
    db.add_all([cat_dining, cat_shopping])
    db.commit()
    
    # Add training data (categorized transactions)
    training_data = [
        ("KFC RESTAURANT FOOD", cat_dining.id),
        ("BURGER KING MEAL", cat_dining.id),
        ("MC DONALDS BREAKFAST", cat_dining.id),
        ("PIZZA HUT DINNER", cat_dining.id),
        ("AMAZON MARKETPLACE SHOP", cat_shopping.id),
        ("FLIPKART ONLINE SHOPPING", cat_shopping.id),
        ("MYNTRA FASHION CLOTHES", cat_shopping.id),
        ("ZARA RETAIL STORE", cat_shopping.id),
    ]
    for desc, cat_id in training_data:
        t = Transaction(
            date=date(2026, 1, 1),
            description=desc,
            amount=Decimal("500"),
            transaction_type="Debit",
            category_id=cat_id
        )
        db.add(t)
    
    # Add uncategorized transactions to predict
    t1 = Transaction(date=date(2026, 5, 1), description="KFC FOOD", amount=Decimal("300"), transaction_type="Debit")
    t2 = Transaction(date=date(2026, 5, 2), description="AMAZON SHOP", amount=Decimal("2000"), transaction_type="Debit")
    db.add_all([t1, t2])
    db.commit()
    
    auto_categorize_transactions(db)
    
    db.refresh(t1)
    db.refresh(t2)
    
    assert t1.category_id == cat_dining.id
    assert t2.category_id == cat_shopping.id
