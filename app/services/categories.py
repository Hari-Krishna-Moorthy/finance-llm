from sqlalchemy.orm import Session

from ..models import Category, Transaction


DEFAULT_CATEGORIES = [
    ("Groceries", "Supermarkets, food delivery, and daily essentials"),
    ("Dining", "Restaurants, cafes, and takeaway"),
    ("Transport", "Fuel, rides, public transit, and tolls"),
    ("Utilities", "Electricity, water, gas, internet, and mobile"),
    ("Rent", "House rent and lease payments"),
    ("Shopping", "Retail, e-commerce, and personal purchases"),
    ("Entertainment", "Movies, subscriptions, games, and leisure"),
    ("Health", "Doctor visits, pharmacy, and medical expenses"),
    ("Travel", "Flights, hotels, and travel-related spend"),
    ("Education", "Courses, tuition, and learning expenses"),
    ("Salary", "Salary credits and compensation"),
    ("Transfer", "Internal transfers between owned accounts"),
    ("Fees", "Bank fees, charges, and penalties"),
    ("Taxes", "Tax payments and tax-related deductions"),
    ("Investment", "Mutual funds, stocks, SIPs, and brokerage"),
]


def seed_default_categories(db: Session) -> None:
    existing = {row[0] for row in db.query(Category.name).all()}
    for name, description in DEFAULT_CATEGORIES:
        if name not in existing:
            db.add(Category(name=name, description=description, is_custom=False))
    db.commit()


def create_custom_category(db: Session, name: str, description: str | None = None) -> Category:
    category = db.query(Category).filter(Category.name == name).first()
    if category:
        return category

    category = Category(name=name, description=description, is_custom=True)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def assign_transaction_category(db: Session, transaction_id: int, category_id: int) -> Transaction | None:
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    category = db.query(Category).filter(Category.id == category_id).first()
    if not transaction or not category:
        return None

    transaction.category_id = category.id
    db.commit()
    db.refresh(transaction)
    return transaction
