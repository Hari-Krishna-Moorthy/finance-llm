import pandas as pd
import pdfplumber
import os
import re
import io
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from ..models import Transaction, Account
from ..database import SessionLocal

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
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
        if not lines: return

        # Handle both Markdown Pipe format and Tab/Space separated format
        if "|" in lines[0]:
            # Markdown table
            table_lines = [line for line in lines if line.startswith("|")]
            if len(table_lines) < 3: return
            headers = [h.strip() for h in table_lines[0].split("|") if h.strip()]
            data = []
            for line in table_lines[2:]:
                row = [cell.strip() for cell in line.split("|") if cell.strip()]
                if len(row) >= len(headers):
                    data.append(row[:len(headers)])
            df = pd.DataFrame(data, columns=headers)
        else:
            # Assume Tab or multi-space separated text
            # Convert multi-space to tab for easier reading
            processed_text = "\n".join([re.sub(r'\s{2,}', '\t', l) for l in lines])
            df = pd.read_csv(io.StringIO(processed_text), sep='\t')

        # Robust Column Mapping
        mapping = {
            "Date": ["date", "transaction date"],
            "Description": ["description", "transaction details", "particulars", "details"],
            "Amount": ["amount", "amount (rs.)", "value"],
            "Category": ["category", "merchant category"]
        }
        
        final_map = {}
        for target, aliases in mapping.items():
            for col in df.columns:
                if col.lower() in aliases:
                    final_map[col] = target
                    break
        
        df = df.rename(columns=final_map)
        _save_dataframe_to_db(df, account_id, db)
        db.commit()
    except Exception as e:
        print(f"Ingestion Error: {e}")
    finally:
        db.close()

def _save_dataframe_to_db(df: pd.DataFrame, account_id: int, db: Session):
    for _, row in df.iterrows():
        # Clean up amount string and identify Dr/Cr
        raw_amount = str(row.get("Amount", "0")).strip().replace(",", "")
        
        # Check for Dr/Cr suffix or sign
        is_credit = False
        if "Cr" in raw_amount:
            is_credit = True
        elif "Dr" in raw_amount:
            is_credit = False
        else:
            try:
                if float(raw_amount) > 0:
                    is_credit = True
            except:
                pass

        # Extract numeric value
        amount_val = Decimal("0")
        try:
            clean_amount = "".join(c for c in raw_amount if c.isdigit() or c == ".")
            if clean_amount:
                amount_val = Decimal(clean_amount)
        except:
            pass
            
        trans_type = "Credit" if is_credit else "Debit"
        
        # Extract Description and Reference ID
        raw_desc = str(row.get("Description", row.get("Transaction Details", "")))
        
        # Extract Reference ID / UPI ID / Ref No using Regex
        ref_id = str(row.get("Reference", ""))
        if not ref_id or ref_id.lower() == "nan":
            # Search in description if not explicitly provided
            ref_match = re.search(r"(?:Ref No:|UPI Ref:|Ref:)\s*([A-Z0-9]+)", raw_desc, re.IGNORECASE)
            if ref_match:
                ref_id = ref_match.group(1)
            else:
                # Catch-all for long numeric strings often used as references
                long_num = re.search(r"(\d{10,})", raw_desc)
                if long_num:
                    ref_id = long_num.group(1)

        # Multi-currency logic (Default to INR)
        currency = row.get("Currency", "INR")
        rate = Decimal(str(row.get("ExchangeRate", 1.0)))
        base_amount = amount_val * rate if currency != "INR" else amount_val
        
        transaction = Transaction(
            date=pd.to_datetime(row.get("Date"), dayfirst=True).date(),
            description=raw_desc,
            amount=amount_val,
            transaction_type=trans_type,
            original_currency=currency,
            exchange_rate=rate,
            base_amount_inr=base_amount,
            account_id=account_id,
            reference_id=ref_id
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
