import pandas as pd
import pdfplumber
import os
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from ..models import Transaction, Account
from ..database import SessionLocal

import io

def process_file(file_path: str, account_id: int, password: str = None):
    db = SessionLocal()
    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".csv":
            df = pd.read_csv(file_path)
        elif ext == ".xlsx":
            df = pd.read_excel(file_path)
        elif ext == ".pdf":
            df = parse_pdf(file_path, password=password)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        _save_dataframe_to_db(df, account_id, db)
        db.commit()
    finally:
        db.close()

def process_markdown_text(text: str, account_id: int):
    db = SessionLocal()
    try:
        lines = text.strip().split("\n")
        # Filter for markdown table lines
        table_lines = [line for line in lines if line.strip().startswith("|")]
        
        if len(table_lines) < 3:
            return
        
        # Extract headers and data, skipping the separator line
        headers = [h.strip() for h in table_lines[0].split("|") if h.strip()]
        data = []
        for line in table_lines[2:]:
            row = [cell.strip() for cell in line.split("|") if cell.strip()]
            if len(row) == len(headers):
                data.append(row)
        
        df = pd.DataFrame(data, columns=headers)
        
        # Map columns based on common names
        column_map = {}
        for col in df.columns:
            lower_col = col.lower()
            if "date" in lower_col:
                column_map[col] = "Date"
            elif "detail" in lower_col or "description" in lower_col:
                column_map[col] = "Description"
            elif "amount" in lower_col:
                column_map[col] = "Amount"
        
        df = df.rename(columns=column_map)
        _save_dataframe_to_db(df, account_id, db)
        db.commit()
    finally:
        db.close()

def _save_dataframe_to_db(df: pd.DataFrame, account_id: int, db: Session):
    for _, row in df.iterrows():
        # Basic normalization for Amount
        raw_amount = str(row.get("Amount", "0")).replace(",", "")
        
        # Handle "1,234.56 Dr" or "1,234.56 Cr" format
        trans_type = "Debit"
        if "Cr" in raw_amount:
            trans_type = "Credit"
        elif "Dr" in raw_amount:
            trans_type = "Debit"
        else:
            # Fallback to sign
            try:
                if float(raw_amount) > 0:
                    trans_type = "Credit"
            except:
                pass

        amount_val = Decimal("0")
        try:
            # Strip non-numeric chars except .
            clean_amount = "".join(c for c in raw_amount if c.isdigit() or c == ".")
            amount_val = Decimal(clean_amount)
        except:
            pass
            
        # Multi-currency logic (Default to INR)
        currency = row.get("Currency", "INR")
        rate = Decimal(str(row.get("ExchangeRate", 1.0)))
        base_amount = amount_val * rate if currency != "INR" else amount_val
        
        transaction = Transaction(
            date=pd.to_datetime(row.get("Date"), dayfirst=True).date(),
            description=row.get("Description", row.get("Transaction Details", "")),
            amount=amount_val,
            transaction_type=trans_type,
            original_currency=currency,
            exchange_rate=rate,
            base_amount_inr=base_amount,
            account_id=account_id,
            reference_id=row.get("Reference", "")
        )
        db.add(transaction)

def parse_pdf(file_path: str, password: str = None):
    data = []
    with pdfplumber.open(file_path, password=password) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                df = pd.DataFrame(table[1:], columns=table[0])
                data.append(df)
    
    if not data:
        return pd.DataFrame()
    return pd.concat(data)
