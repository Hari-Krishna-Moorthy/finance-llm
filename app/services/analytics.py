from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import Transaction
import pandas as pd
import numpy as np

def detect_anomalies(db: Session, account_id: int):
    """
    Flag transactions that are unusually high compared to historical average (Z-score > 3).
    """
    transactions = db.query(Transaction).filter(Transaction.account_id == account_id).all()
    if not transactions:
        return []

    df = pd.DataFrame([{
        "id": t.id,
        "amount": float(t.amount),
        "description": t.description
    } for t in transactions])

    if df.empty:
        return []

    mean = df["amount"].mean()
    std = df["amount"].std()
    
    if std == 0:
        return []

    df["z_score"] = (df["amount"] - mean) / std
    anomalies = df[df["z_score"] > 3]
    
    return anomalies.to_dict("records")

def predict_future_payments(db: Session, account_id: int):
    """
    Identify recurring payments based on historical grouping of Description and Amount.
    """
    transactions = db.query(Transaction).filter(
        Transaction.account_id == account_id,
        Transaction.transaction_type == "Debit"
    ).all()
    
    if len(transactions) < 10:
        return []

    df = pd.DataFrame([{
        "amount": float(t.amount),
        "description": t.description,
        "date": t.date
    } for t in transactions])

    # Group by description and amount to find patterns
    patterns = df.groupby(["description", "amount"]).size().reset_index(name="count")
    recurring = patterns[patterns["count"] >= 3]
    
    predictions = []
    for _, row in recurring.iterrows():
        predictions.append({
            "description": row["description"],
            "amount": row["amount"],
            "frequency": "Monthly (Estimated)"
        })
        
    return predictions
