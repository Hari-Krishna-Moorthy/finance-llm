import io
import os
import re
from decimal import Decimal

import pandas as pd
import pdfplumber
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Account, Transaction
from ..services.dashboard_state import sync_dashboard_metrics

SBI_STATEMENT_PASSWORD = "HARI30082001"


def process_file(file_path: str, account_id: int, password: str = None):
    db = SessionLocal()
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise ValueError(f"Account {account_id} not found")

        df = parse_statement(file_path, account.name, password=password)
        _save_dataframe_to_db(df, account_id, db)
        db.commit()
        sync_dashboard_metrics(db)
    finally:
        db.close()


def parse_statement(file_path: str, account_name: str, password: str | None = None) -> pd.DataFrame:
    ext = os.path.splitext(file_path)[1].lower()
    normalized_account = account_name.strip().lower()

    if ext == ".pdf":
        if _is_federal_bank_pdf(file_path, password=password):
            return parse_federal_bank_pdf(file_path, password=password)
        return parse_pdf(file_path, password=password)

    if "hdfc" in normalized_account:
        return parse_hdfc_statement(file_path)

    if "sbi" in normalized_account:
        return parse_sbi_statement(file_path, password=password or SBI_STATEMENT_PASSWORD)

    if ext in {".xlsx", ".xls"}:
        return parse_generic_excel(file_path, password=password)

    if ext == ".csv":
        return pd.read_csv(file_path)

    raise ValueError(f"Unsupported file format: {ext}")


def parse_hdfc_statement(file_path: str) -> pd.DataFrame:
    df = _read_excel(file_path, engine="xlrd", header=None)

    header_row = None
    for index, row in df.iterrows():
        values = [str(value).strip().lower() for value in row.tolist() if pd.notna(value)]
        if values and "date" in values and "narration" in values and "withdrawal amt." in values:
            header_row = index
            break

    if header_row is None:
        raise ValueError("Unable to locate HDFC transaction header")

    data = _read_excel(file_path, engine="xlrd", header=header_row)
    data = data.dropna(how="all")
    data = data[data["Date"].apply(lambda value: pd.notna(pd.to_datetime(value, dayfirst=True, errors="coerce")))]

    rename_map = {
        "Date": "Date",
        "Narration": "Description",
        "Chq./Ref.No.": "Reference",
        "Value Dt": "ValueDate",
        "Withdrawal Amt.": "Withdrawal",
        "Deposit Amt.": "Deposit",
        "Closing Balance": "ClosingBalance",
    }
    data = data.rename(columns=rename_map)
    return data[[column for column in ["Date", "Description", "Reference", "ValueDate", "Withdrawal", "Deposit", "ClosingBalance"] if column in data.columns]]


def parse_sbi_statement(file_path: str, password: str) -> pd.DataFrame:
    try:
        import msoffcrypto
    except ImportError as exc:
        raise ImportError(
            "msoffcrypto-tool is required to read encrypted SBI statements. Install dependencies from requirements.txt."
        ) from exc

    with open(file_path, "rb") as fh:
        office = msoffcrypto.OfficeFile(fh)
        if office.is_encrypted():
            decrypted = io.BytesIO()
            office.load_key(password=password)
            office.decrypt(decrypted)
            excel_source = io.BytesIO(decrypted.getvalue())
        else:
            excel_source = io.BytesIO(fh.read())

    excel_source.seek(0)
    df = pd.read_excel(excel_source, sheet_name=0, header=None)

    header_row = None
    for index, row in df.iterrows():
        values = [str(value).strip().lower() for value in row.tolist() if pd.notna(value)]
        if values and "date" in values and "details" in values and "balance" in values:
            header_row = index
            break

    if header_row is None:
        raise ValueError("Unable to locate SBI transaction header")

    excel_source.seek(0)
    data = pd.read_excel(excel_source, sheet_name=0, header=header_row)
    data = data.dropna(how="all")
    data = data[data["Date"].apply(lambda value: pd.notna(pd.to_datetime(value, dayfirst=True, errors="coerce")))]
    data = data.rename(
        columns={
            "Date": "Date",
            "Details": "Description",
            "Ref No/Cheque No": "Reference",
            "Debit": "Debit",
            "Credit": "Credit",
            "Balance": "Balance",
        }
    )
    return data[[column for column in ["Date", "Description", "Reference", "Debit", "Credit", "Balance"] if column in data.columns]]


def parse_generic_excel(file_path: str, password: str | None = None) -> pd.DataFrame:
    if password:
        try:
            import msoffcrypto
        except ImportError as exc:
            raise ImportError(
                "msoffcrypto-tool is required to open encrypted Excel statements. Install dependencies from requirements.txt."
            ) from exc

        with open(file_path, "rb") as fh:
            office = msoffcrypto.OfficeFile(fh)
            if office.is_encrypted():
                decrypted = io.BytesIO()
                office.load_key(password=password)
                office.decrypt(decrypted)
                return pd.read_excel(io.BytesIO(decrypted.getvalue()))

    return _read_excel(file_path)


def _is_federal_bank_pdf(file_path: str, password: str | None = None) -> bool:
    try:
        with pdfplumber.open(file_path, password=password) as pdf:
            sample_text = "\n".join((page.extract_text() or "") for page in pdf.pages[:2])
            return "federal bank" in sample_text.lower() and "statement of account period" in sample_text.lower()
    except Exception:
        return False


def parse_federal_bank_pdf(file_path: str, password: str | None = None) -> pd.DataFrame:
    rows = []
    with pdfplumber.open(file_path, password=password) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.splitlines():
                parsed = _parse_federal_bank_line(line)
                if parsed:
                    rows.append(parsed)

    return pd.DataFrame(rows)


def _parse_federal_bank_line(line: str) -> dict | None:
    line = re.sub(r"\s+", " ", line).strip()
    match = re.match(r"^(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(.*?)\s+TFR\s+(.*)$", line)
    if not match:
        return None

    date_value, value_date, description, tail = match.groups()
    tail_tokens = tail.split()
    if not tail_tokens:
        return None

    dr_cr = tail_tokens[-1].upper() if tail_tokens[-1].upper() in {"DR", "CR"} else ""
    amount_tokens = tail_tokens[:-1] if dr_cr else tail_tokens
    numeric_tokens = [token for token in amount_tokens if _looks_like_amount(token)]
    amount = Decimal(numeric_tokens[0].replace(",", "")) if numeric_tokens else Decimal("0")

    transaction_type = "Credit" if dr_cr == "CR" else "Debit"
    if dr_cr not in {"CR", "DR"}:
        transaction_type = "Credit" if "UPI IN/" in description or "CREDITED" in description.upper() else "Debit"

    reference_id = _extract_reference_id({"Reference": ""}, description)
    upi_id = _extract_upi_id(description)

    return {
        "Date": date_value,
        "Description": description,
        "Reference": reference_id,
        "ValueDate": value_date,
        "Amount": amount,
        "TransactionType": transaction_type,
        "extra_details": {
            "reference_id": reference_id or None,
            "upi_id": upi_id or None,
            "description": description,
            "currency_exchange_rate": 1.0,
            "account_number": _extract_account_number(description) or None,
            "bank": "Federal Bank",
        },
    }


def _read_excel(file_path: str, engine: str | None = None, header=None) -> pd.DataFrame:
    if engine == "xlrd":
        try:
            import xlrd  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "xlrd is required to read .xls bank statements. Install dependencies from requirements.txt."
            ) from exc

    return pd.read_excel(file_path, sheet_name=0, header=header, engine=engine)


def process_markdown_text(text: str, account_id: int):
    db = SessionLocal()
    try:
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
        if not lines:
            return

        if "|" in lines[0]:
            table_lines = [line for line in lines if line.startswith("|")]
            if len(table_lines) < 3:
                return
            headers = [h.strip() for h in table_lines[0].split("|") if h.strip()]
            data = []
            for line in table_lines[2:]:
                row = [cell.strip() for cell in line.split("|") if cell.strip()]
                if len(row) >= len(headers):
                    data.append(row[:len(headers)])
            df = pd.DataFrame(data, columns=headers)
        else:
            processed_text = "\n".join([re.sub(r"\s{2,}", "\t", l) for l in lines])
            df = pd.read_csv(io.StringIO(processed_text), sep="\t")

        mapping = {
            "Date": ["date", "transaction date"],
            "Description": ["description", "transaction details", "particulars", "details"],
            "Amount": ["amount", "amount (rs.)", "value"],
            "Category": ["category", "merchant category"],
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
        sync_dashboard_metrics(db)
    except Exception as e:
        print(f"Ingestion Error: {e}")
    finally:
        db.close()


def _save_dataframe_to_db(df: pd.DataFrame, account_id: int, db: Session):
    for _, row in df.iterrows():
        transaction = _row_to_transaction(row, account_id)
        if transaction:
            db.add(transaction)


def _row_to_transaction(row, account_id: int) -> Transaction | None:
    raw_description = str(row.get("Description", row.get("Narration", row.get("Details", "")))).strip()
    if not raw_description or raw_description.lower() == "nan":
        return None

    date_value = row.get("Date")
    if pd.isna(date_value):
        return None

    amount_value, transaction_type = _extract_amount_and_type(row)
    reference_id = _extract_reference_id(row, raw_description)
    upi_id = _extract_upi_id(raw_description)
    account_number = _extract_account_number(raw_description)
    currency = row.get("Currency", "INR")
    exchange_rate = Decimal(str(row.get("ExchangeRate", 1.0)))
    base_amount = amount_value * exchange_rate if currency != "INR" else amount_value
    extra_details = {
        "reference_id": reference_id or None,
        "upi_id": upi_id or None,
        "description": raw_description,
        "currency_exchange_rate": float(exchange_rate),
        "account_number": account_number or None,
    }
    provided_extra = row.get("extra_details")
    if isinstance(provided_extra, dict):
        extra_details.update({k: v for k, v in provided_extra.items() if v is not None})

    return Transaction(
        date=pd.to_datetime(date_value, dayfirst=True).date(),
        description=raw_description,
        amount=amount_value,
        transaction_type=transaction_type,
        original_currency=currency,
        exchange_rate=exchange_rate,
        base_amount_inr=base_amount,
        account_id=account_id,
        reference_id=reference_id,
        extra_details=extra_details,
    )


def _extract_amount_and_type(row) -> tuple[Decimal, str]:
    explicit_amount = row.get("Amount")
    explicit_type = row.get("TransactionType")
    if explicit_amount is not None and not pd.isna(explicit_amount):
        amount = _to_decimal(explicit_amount)
        if explicit_type in {"Credit", "Debit"}:
            return amount, explicit_type

    withdrawal = row.get("Withdrawal", row.get("Debit", row.get("Amount", 0)))
    deposit = row.get("Deposit", row.get("Credit", 0))

    deposit_amount = _to_decimal(deposit)
    withdrawal_amount = _to_decimal(withdrawal)
    if deposit_amount > 0:
        return deposit_amount, "Credit"
    if withdrawal_amount > 0:
        return withdrawal_amount, "Debit"

    raw_amount = str(row.get("Amount", "0")).strip().replace(",", "")
    is_credit = "Cr" in raw_amount
    if not is_credit and "Dr" not in raw_amount:
        try:
            if float(raw_amount) > 0:
                is_credit = True
        except Exception:
            pass

    clean_amount = "".join(c for c in raw_amount if c.isdigit() or c == ".")
    amount = Decimal(clean_amount or "0")
    return amount, "Credit" if is_credit else "Debit"


def _to_decimal(value) -> Decimal:
    if pd.isna(value):
        return Decimal("0")
    cleaned = str(value).replace(",", "").strip()
    if cleaned in {"", "nan", "None"}:
        return Decimal("0")
    try:
        return Decimal(cleaned)
    except Exception:
        return Decimal("0")


def _extract_reference_id(row, raw_description: str) -> str:
    ref_id = str(row.get("Reference", row.get("Chq./Ref.No.", ""))).strip()
    if ref_id and ref_id.lower() != "nan":
        return ref_id

    ref_match = re.search(r"(?:Ref No:|UPI Ref:|Ref:)\s*([A-Z0-9]+)", raw_description, re.IGNORECASE)
    if ref_match:
        return ref_match.group(1)

    long_num = re.search(r"(\d{10,})", raw_description)
    if long_num:
        return long_num.group(1)

    return ""


def _looks_like_amount(token: str) -> bool:
    return bool(re.fullmatch(r"[\d,]+(?:\.\d+)?", str(token).strip()))


def _extract_upi_id(raw_description: str) -> str:
    patterns = [
        r"([a-zA-Z0-9.\-_]{2,})@(?:oksbi|okhdfcbank|okaxis|okicici|okaxis|ybl|paytm|pthdfc|ptybl|apl|upi|airtel|axis|barodampay|idbi|indus|pingpay|ibl|unionbank|ubin|ibl|jppl|fbl|hdfcbank|axisbank|sbi|yesbank|kotak|fino|omni|boi|pnb|canara|idfc|hsbc|rbl|indianbk|idbi|jupi|jupiter|payu|bharatpe|phonepe|supermone|amazonpay|freecharge|mobikwik)",
        r"([a-zA-Z0-9.\-_]{2,}@[\w.]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw_description, re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


def _extract_account_number(raw_description: str) -> str:
    patterns = [
        r"\b(?:A\/c|A/c|Acc(?:ount)?(?: Number)?|Acct(?: Number)?|Account No\.?|Account Number)\s*[:\-]?\s*([0-9]{6,20})\b",
        r"\b([0-9]{12,20})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw_description, re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


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
