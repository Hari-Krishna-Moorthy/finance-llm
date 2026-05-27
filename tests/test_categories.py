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
