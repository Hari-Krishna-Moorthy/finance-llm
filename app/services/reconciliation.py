from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from ..models import Transaction
from datetime import timedelta

def reconcile_transfers(db: Session):
    """
    Identify internal transfers across accounts.
    Logic: A debit in Account A matching a credit in Account B (same amount)
    within a 3-day window.
    """
    # Fetch all debits that are not yet linked
    debits = db.query(Transaction).filter(
        Transaction.transaction_type == "Debit",
        Transaction.internal_transfer_id == None
    ).all()

    for debit in debits:
        # Look for matching credits in other accounts within +/- 3 days
        matching_credit = db.query(Transaction).filter(
            Transaction.transaction_type == "Credit",
            Transaction.account_id != debit.account_id,
            Transaction.amount == debit.amount,
            Transaction.internal_transfer_id == None,
            Transaction.date >= debit.date - timedelta(days=3),
            Transaction.date <= debit.date + timedelta(days=3)
        ).first()

        if matching_credit:
            # Link them
            debit.internal_transfer_id = matching_credit.id
            matching_credit.internal_transfer_id = debit.id
            
            # Auto-tag as Internal Transfer if category exists
            # (Assuming an 'Internal Transfer' category exists)
            # category = db.query(Category).filter(Category.name == "Internal Transfer").first()
            # if category:
            #     debit.category_id = category.id
            #     matching_credit.category_id = category.id

    db.commit()
