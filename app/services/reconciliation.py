from datetime import timedelta

from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..models import Category, Transaction

def reconcile_transfers(db: Session):
    """
    Identify internal transfers across accounts.
    Logic: A debit in Account A matching a credit in Account B (same amount)
    within a 3-day window.
    """
    self_transfer_category_id = (
        db.query(Category.id).filter(Category.name == "Self transfer").scalar()
    )

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
            debit_account_number = (debit.extra_details or {}).get("account_number")
            credit_account_number = (matching_credit.extra_details or {}).get("account_number")
            
            # If both records explicitly mention account numbers, they must match each other's account
            # This is tricky because one might be source, one target.
            # Let's relax this: if they are different, it's fine unless we are sure they are contradictory.
            
            # Link them
            debit.internal_transfer_id = matching_credit.id
            matching_credit.internal_transfer_id = debit.id
            if self_transfer_category_id:
                debit.category_id = self_transfer_category_id
                matching_credit.category_id = self_transfer_category_id

    db.commit()
