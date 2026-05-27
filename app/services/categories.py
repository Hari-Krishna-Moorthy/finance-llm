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


def assign_category_to_matching_upi_transactions(
    db: Session,
    transaction_id: int,
    category_id: int,
) -> int:
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    category = db.query(Category).filter(Category.id == category_id).first()
    if not transaction or not category:
        return 0

    upi_id = (transaction.extra_details or {}).get("upi_id")
    if not upi_id:
        transaction.category_id = category.id
        db.commit()
        return 1

    matched_transactions = (
        db.query(Transaction)
        .filter(Transaction.id != transaction.id)
        .all()
    )

    updated_count = 0
    for candidate in matched_transactions:
        candidate_upi = (candidate.extra_details or {}).get("upi_id")
        if candidate_upi and candidate_upi == upi_id:
            candidate.category_id = category.id
            updated_count += 1

    transaction.category_id = category.id
    updated_count += 1
    db.commit()
    return updated_count


def assign_category_by_upi_id(db: Session, upi_id: str, category_id: int) -> int:
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        return 0

    transactions = (
        db.query(Transaction)
        .filter(Transaction.extra_details["upi_id"].as_string() == upi_id)
        .all()
    )

    updated_count = 0
    for transaction in transactions:
        transaction.category_id = category.id
        updated_count += 1

    db.commit()
    return updated_count


def get_upi_id_summary(db: Session, only_untagged: bool = False):
    from sqlalchemy import func
    # We want distinct upi_id, count, and the most common category_id if any
    # For simplicity, we'll start with upi_id and count
    query = (
        db.query(
            Transaction.extra_details["upi_id"].as_string().label("upi_id"),
            func.count(Transaction.id).label("count"),
        )
        .filter(Transaction.extra_details["upi_id"].as_string() != None)
    )
    
    if only_untagged:
        query = query.filter(Transaction.category_id == None)
        
    results = (
        query.group_by(Transaction.extra_details["upi_id"].as_string())
        .order_by(func.count(Transaction.id).desc())
        .all()
    )
    
    # Also fetch the current category name for each upi_id if it's consistent
    upi_summaries = []
    for upi_id, count in results:
        # Find the most common category_id for this UPI ID
        most_common_cat = (
            db.query(Transaction.category_id, func.count(Transaction.id))
            .filter(Transaction.extra_details["upi_id"].as_string() == upi_id)
            .filter(Transaction.category_id != None)
            .group_by(Transaction.category_id)
            .order_by(func.count(Transaction.id).desc())
            .first()
        )
        
        current_category_id = most_common_cat[0] if most_common_cat else None
        
        # If filtering for untagged, and we found a common category, skip if requested
        if only_untagged and current_category_id is not None:
            continue

        upi_summaries.append({
            "upi_id": upi_id,
            "count": count,
            "category_id": current_category_id
        })
        
    return upi_summaries
