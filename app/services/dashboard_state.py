from decimal import Decimal

from sqlalchemy.orm import Session

from ..models import DashboardState, Transaction, Category
from .app_settings import get_setting


def upsert_dashboard_state(db: Session, key: str, value: str) -> DashboardState:
    state = db.query(DashboardState).filter(DashboardState.key == key).first()
    if state:
        state.value = value
    else:
        state = DashboardState(key=key, value=value)
        db.add(state)
    db.commit()
    db.refresh(state)
    return state


def get_dashboard_state(db: Session, key: str, default: str = "") -> str:
    state = db.query(DashboardState).filter(DashboardState.key == key).first()
    return state.value if state else default


def sync_dashboard_metrics(db: Session) -> None:
    transactions = (
        db.query(Transaction.transaction_type, Transaction.base_amount_inr, Category.name)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .all()
    )
    computed_balance = Decimal("0")
    exclude_self_transfer = get_setting(db, "exclude_self_transfer_from_balance", "true").lower() == "true"
    for transaction_type, amount, category_name in transactions:
        value = Decimal(str(amount or 0))
        if exclude_self_transfer and (category_name or "").lower() == "self transfer":
            continue
        if transaction_type == "Credit":
            computed_balance += value
        elif transaction_type == "Debit":
            computed_balance -= value
    adjustment = Decimal(get_setting(db, "balance_adjustment", "0"))
    computed_balance += adjustment
    upsert_dashboard_state(db, "total_balance", str(computed_balance))
