from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Account, Category, Transaction
from app.services.categories import (
    DEFAULT_CATEGORIES,
    assign_transaction_category,
    create_custom_category,
    seed_default_categories,
    get_upi_id_summary,
    assign_category_by_upi_id,
)


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def test_seed_default_categories_inserts_expected_catalog():
    db = _make_session()

    seed_default_categories(db)

    names = {row[0] for row in db.query(Category.name).all()}
    assert len(DEFAULT_CATEGORIES) == len(names)
    assert {"Groceries", "Dining", "Transport"}.issubset(names)


def test_create_custom_category_marks_row_as_custom():
    db = _make_session()

    category = create_custom_category(db, "Weekend Trip", "Travel for short breaks")

    assert category.name == "Weekend Trip"
    assert category.is_custom is True
    assert category.description == "Travel for short breaks"


def test_assign_transaction_category_updates_transaction():
    db = _make_session()
    account = Account(name="Primary", account_type="Checking", currency="INR")
    transaction = Transaction(
        date=date(2026, 5, 27),
        description="Metro ride",
        amount=100,
        transaction_type="Debit",
        original_currency="INR",
        exchange_rate=1,
        base_amount_inr=100,
        account=account,
    )
    category = Category(name="Transport", description="Transit", is_custom=False)
    db.add_all([account, transaction, category])
    db.commit()
    db.refresh(transaction)
    db.refresh(category)

    updated = assign_transaction_category(db, transaction.id, category.id)

    assert updated is not None
    assert updated.category_id == category.id


def test_upi_categorization_workflow():
    db = _make_session()
    account = Account(name="Primary", account_type="Checking", currency="INR")
    
    # 2 transactions with same UPI ID
    t1 = Transaction(
        date=date(2026, 5, 27),
        description="Payment to Vendor A",
        amount=500,
        transaction_type="Debit",
        original_currency="INR",
        exchange_rate=1,
        base_amount_inr=500,
        account=account,
        extra_details={"upi_id": "vendor.a@upi"}
    )
    t2 = Transaction(
        date=date(2026, 5, 28),
        description="Another payment to Vendor A",
        amount=1000,
        transaction_type="Debit",
        original_currency="INR",
        exchange_rate=1,
        base_amount_inr=1000,
        account=account,
        extra_details={"upi_id": "vendor.a@upi"}
    )
    
    # 1 transaction with different UPI ID
    t3 = Transaction(
        date=date(2026, 5, 28),
        description="Payment to Vendor B",
        amount=200,
        transaction_type="Debit",
        original_currency="INR",
        exchange_rate=1,
        base_amount_inr=200,
        account=account,
        extra_details={"upi_id": "vendor.b@upi"}
    )
    
    cat = Category(name="Shopping", description="Retail", is_custom=False)
    db.add_all([account, t1, t2, t3, cat])
    db.commit()
    
    # Test summary
    summary = get_upi_id_summary(db)
    assert len(summary) == 2
    # Find vendor.a in summary
    vendor_a_summary = next(s for s in summary if s["upi_id"] == "vendor.a@upi")
    assert vendor_a_summary["count"] == 2
    assert vendor_a_summary["category_id"] is None
    
    # Test bulk categorization
    updated_count = assign_category_by_upi_id(db, "vendor.a@upi", cat.id)
    assert updated_count == 2
    
    db.refresh(t1)
    db.refresh(t2)
    db.refresh(t3)
    assert t1.category_id == cat.id
    assert t2.category_id == cat.id
    assert t3.category_id is None
    
    # Verify summary now includes category
    summary = get_upi_id_summary(db)
    vendor_a_summary = next(s for s in summary if s["upi_id"] == "vendor.a@upi")
    assert vendor_a_summary["category_id"] == cat.id
