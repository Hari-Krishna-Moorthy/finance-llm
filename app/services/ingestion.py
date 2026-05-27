import pandas as pd
import pdfplumber
import os
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from ..models import Transaction, Account
from ..database import SessionLocal

def process_file(file_path: str, account_id: int):
    db = SessionLocal()
    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".csv":
            df = pd.read_csv(file_path)
        elif ext == ".xlsx":
            df = pd.read_excel(file_path)
        elif ext == ".pdf":
            df = parse_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        # Standardize columns (this is a simplified example, 
        # in reality we'd need mapping for different banks)
        # Expected columns: Date, Description, Amount, Type
        
        for _, row in df.iterrows():
            # Basic normalization
            amount = Decimal(str(row.get("Amount", 0)))
            trans_type = row.get("Type", "Debit" if amount < 0 else "Credit")
            
            # Multi-currency logic (Default to INR)
            currency = row.get("Currency", "INR")
            rate = Decimal(str(row.get("ExchangeRate", 1.0)))
            base_amount = amount * rate if currency != "INR" else amount
            
            transaction = Transaction(
                date=pd.to_datetime(row.get("Date")).date(),
                description=row.get("Description", ""),
                amount=abs(amount),
                transaction_type=trans_type,
                original_currency=currency,
                exchange_rate=rate,
                base_amount_inr=abs(base_amount),
                account_id=account_id,
                reference_id=row.get("Reference", "")
            )
            db.add(transaction)
        
        db.commit()
    finally:
        db.close()

def parse_pdf(file_path: str):
    # Extremely simplified PDF parsing logic
    data = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                # Assume first row is header
                df = pd.DataFrame(table[1:], columns=table[0])
                data.append(df)
    
    if not data:
        return pd.DataFrame()
    return pd.concat(data)
