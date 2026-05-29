from fastapi import APIRouter, Request, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
from ..database import get_db
from .. import models
from ..services.upload_tracking import create_statement_upload
from ..services.categories import (
    assign_category_to_matching_upi_transactions,
    assign_transaction_category,
    create_custom_category,
    seed_default_categories,
    get_upi_id_summary,
    assign_category_by_upi_id,
)
from ..services.dashboard_state import get_dashboard_state, upsert_dashboard_state, sync_dashboard_metrics
from ..services.app_settings import get_setting, upsert_setting
from ..services.stock_analyzer import StockAnalyzer
from ..services.llm_analysis import generate_swing_trade_setup
import shutil
import os
from uuid import uuid4

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/")
async def home(request: Request, db: Session = Depends(get_db)):
    transactions = db.query(models.Transaction).order_by(models.Transaction.date.desc()).limit(10).all()
    sync_dashboard_metrics(db)
    total_balance = get_dashboard_state(db, "total_balance", "0")
    theme = get_dashboard_state(db, "theme", "dark")
    
    # Fetch top US stock signals
    stock_signals = (
        db.query(models.StockSignal)
        .filter(models.StockSignal.signal_type.in_(["Strong Buy", "Buy"]))
        .order_by(models.StockSignal.score.desc())
        .limit(7)
        .all()
    )
    
    # Build a consolidated list for the UI with indicators
    enriched_signals = []
    for signal in stock_signals:
        indicator = db.query(models.TechnicalIndicator).filter(models.TechnicalIndicator.ticker == signal.ticker).order_by(models.TechnicalIndicator.calculated_at.desc()).first()
        sr = db.query(models.SupportResistanceLevel).filter(models.SupportResistanceLevel.ticker == signal.ticker).order_by(models.SupportResistanceLevel.detected_at.desc()).first()
        enriched_signals.append({
            "signal": signal,
            "indicator": indicator,
            "sr": sr
        })

    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={
            "transactions": transactions,
            "total_balance": total_balance,
            "theme": theme,
            "stock_signals": enriched_signals,
        }
    )

@router.get("/accounts")
async def accounts_page(request: Request, db: Session = Depends(get_db)):
    accounts = db.query(models.Account).all()
    return templates.TemplateResponse(
        request=request, 
        name="accounts.html", 
        context={"accounts": accounts}
    )

@router.post("/accounts")
async def create_account(
    request: Request,
    name: str = Form(...),
    account_type: str = Form(...),
    currency: str = Form("INR"),
    db: Session = Depends(get_db)
):
    account = models.Account(name=name, account_type=account_type, currency=currency)
    db.add(account)
    db.commit()
    accounts = db.query(models.Account).all()
    return templates.TemplateResponse(
        request=request, 
        name="accounts.html", 
        context={"accounts": accounts, "message": f"Account '{name}' created successfully!"}
    )

@router.get("/reconcile")
async def reconcile_page(request: Request, db: Session = Depends(get_db)):
    unreconciled_debits = db.query(models.Transaction).filter(
        models.Transaction.transaction_type == "Debit",
        models.Transaction.internal_transfer_id == None
    ).order_by(models.Transaction.date.desc()).all()
    
    unreconciled_credits = db.query(models.Transaction).filter(
        models.Transaction.transaction_type == "Credit",
        models.Transaction.internal_transfer_id == None
    ).order_by(models.Transaction.date.desc()).all()
    
    # Fetch reconciled pairs (this is a bit complex in SQL, 
    # but we can do it by finding all debits with an internal_transfer_id)
    reconciled_debits = db.query(models.Transaction).filter(
        models.Transaction.transaction_type == "Debit",
        models.Transaction.internal_transfer_id != None
    ).all()
    
    reconciled_pairs = []
    for d in reconciled_debits:
        c = db.query(models.Transaction).filter(models.Transaction.id == d.internal_transfer_id).first()
        if c:
            reconciled_pairs.append({"debit": d, "credit": c})
            
    return templates.TemplateResponse(
        request=request, 
        name="reconcile.html", 
        context={
            "unreconciled_debits": unreconciled_debits,
            "unreconciled_credits": unreconciled_credits,
            "reconciled_pairs": reconciled_pairs
        }
    )

@router.post("/reconcile")
async def manual_reconcile(
    request: Request,
    debit_id: int = Form(...),
    credit_id: int = Form(...),
    db: Session = Depends(get_db)
):
    debit = db.query(models.Transaction).filter(models.Transaction.id == debit_id).first()
    credit = db.query(models.Transaction).filter(models.Transaction.id == credit_id).first()
    
    if debit and credit:
        debit.internal_transfer_id = credit.id
        credit.internal_transfer_id = debit.id
        db.commit()
        message = "Transactions linked successfully!"
    else:
        message = "Error: Transactions not found."
        
    return await reconcile_page(request, db)

@router.post("/reconcile/unlink")
async def manual_unlink(
    request: Request,
    debit_id: int = Form(...),
    credit_id: int = Form(...),
    db: Session = Depends(get_db)
):
    debit = db.query(models.Transaction).filter(models.Transaction.id == debit_id).first()
    credit = db.query(models.Transaction).filter(models.Transaction.id == credit_id).first()
    
    if debit: debit.internal_transfer_id = None
    if credit: credit.internal_transfer_id = None
    db.commit()
    
    return await reconcile_page(request, db)

@router.get("/upload")
async def upload_page(request: Request, db: Session = Depends(get_db)):
    accounts = db.query(models.Account).all()
    uploads = (
        db.query(models.StatementUpload)
        .order_by(models.StatementUpload.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        request=request, 
        name="upload.html", 
        context={"accounts": accounts, "uploads": uploads}
    )

@router.get("/transactions")
async def transactions_page(
    request: Request,
    db: Session = Depends(get_db),
    range: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    account_type: Optional[str] = None,
):
    seed_default_categories(db)
    query = db.query(models.Transaction).join(models.Account, models.Transaction.account_id == models.Account.id)

    today = date.today()
    start_date = None
    end_date = None

    range_map = {
        "1d": 1,
        "7d": 7,
        "30d": 30,
        "60d": 60,
        "90d": 90,
        "6m": 183,
        "1y": 365,
    }

    if range in range_map:
        start_date = today - timedelta(days=range_map[range] - 1)
        end_date = today
    else:
        start_date = today - timedelta(days=90)
        end_date = today

    if from_date:
        try:
            start_date = datetime.strptime(from_date, "%Y-%m-%d").date()
        except ValueError:
            pass

    if to_date:
        try:
            end_date = datetime.strptime(to_date, "%Y-%m-%d").date()
        except ValueError:
            pass

    if start_date:
        query = query.filter(models.Transaction.date >= start_date)
    if end_date:
        query = query.filter(models.Transaction.date <= end_date)
    if account_type:
        query = query.filter(models.Account.account_type == account_type)

    transactions = query.order_by(models.Transaction.date.desc()).all()
    categories = db.query(models.Category).order_by(models.Category.is_custom.asc(), models.Category.name.asc()).all()
    account_types = [row[0] for row in db.query(models.Account.account_type).distinct().order_by(models.Account.account_type).all()]
    return templates.TemplateResponse(
        request=request, 
        name="transactions.html", 
        context={
            "transactions": transactions,
            "categories": categories,
            "account_types": account_types,
            "selected_range": range or "90d",
            "from_date": from_date or "",
            "to_date": to_date or "",
            "selected_account_type": account_type or "",
        }
    )


@router.get("/settings")
async def settings_page(
    request: Request, 
    db: Session = Depends(get_db),
    only_untagged: bool = False
):
    seed_default_categories(db)
    accounts = db.query(models.Account).order_by(models.Account.name.asc()).all()
    categories = db.query(models.Category).order_by(models.Category.is_custom.asc(), models.Category.name.asc()).all()
    upi_summaries = get_upi_id_summary(db, only_untagged=only_untagged)
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "accounts": accounts,
            "categories": categories,
            "upi_summaries": upi_summaries,
            "only_untagged": only_untagged,
            "settings": {
                "balance_adjustment": get_setting(db, "balance_adjustment", "0"),
                "theme": get_dashboard_state(db, "theme", "dark"),
                "exclude_self_transfer_from_balance": get_setting(db, "exclude_self_transfer_from_balance", "true"),
            },
        },
    )


@router.post("/settings/upi-categorize")
async def upi_categorize(
    request: Request,
    upi_id: str = Form(...),
    category_id: int = Form(...),
    only_untagged_current: bool = Form(False),
    db: Session = Depends(get_db),
):
    updated_count = assign_category_by_upi_id(db, upi_id, category_id)
    sync_dashboard_metrics(db)
    
    # Render settings page with a message and same filter
    seed_default_categories(db)
    accounts = db.query(models.Account).order_by(models.Account.name.asc()).all()
    categories = db.query(models.Category).order_by(models.Category.is_custom.asc(), models.Category.name.asc()).all()
    upi_summaries = get_upi_id_summary(db, only_untagged=only_untagged_current)
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "accounts": accounts,
            "categories": categories,
            "upi_summaries": upi_summaries,
            "only_untagged": only_untagged_current,
            "message": f"Updated {updated_count} transaction(s) for UPI ID: {upi_id}",
            "settings": {
                "balance_adjustment": get_setting(db, "balance_adjustment", "0"),
                "theme": get_dashboard_state(db, "theme", "dark"),
                "exclude_self_transfer_from_balance": get_setting(db, "exclude_self_transfer_from_balance", "true"),
            },
        },
    )


@router.post("/settings/scan-markets")
async def trigger_market_scan(
    request: Request,
    db: Session = Depends(get_db),
    only_untagged: bool = False
):
    scan_us_markets_task.delay()
    
    seed_default_categories(db)
    accounts = db.query(models.Account).order_by(models.Account.name.asc()).all()
    categories = db.query(models.Category).order_by(models.Category.is_custom.asc(), models.Category.name.asc()).all()
    upi_summaries = get_upi_id_summary(db, only_untagged=only_untagged)
    
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "accounts": accounts,
            "categories": categories,
            "upi_summaries": upi_summaries,
            "only_untagged": only_untagged,
            "message": "Market scan started in the background. Results will appear on the dashboard soon.",
            "settings": {
                "balance_adjustment": get_setting(db, "balance_adjustment", "0"),
                "theme": get_dashboard_state(db, "theme", "dark"),
                "exclude_self_transfer_from_balance": get_setting(db, "exclude_self_transfer_from_balance", "true"),
            },
        },
    )

@router.post("/settings/balance")
async def update_balance_adjustment(
    request: Request,
    balance_adjustment: str = Form("0"),
    db: Session = Depends(get_db),
):
    upsert_setting(db, "balance_adjustment", balance_adjustment)
    sync_dashboard_metrics(db)
    return await settings_page(request, db)


@router.post("/settings/self-transfer")
async def update_self_transfer_setting(
    request: Request,
    exclude_self_transfer_from_balance: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    upsert_setting(db, "exclude_self_transfer_from_balance", "true" if exclude_self_transfer_from_balance else "false")
    sync_dashboard_metrics(db)
    return await settings_page(request, db)


@router.post("/settings/manual-transaction")
async def create_manual_transaction(
    request: Request,
    account_id: int = Form(...),
    date_value: str = Form(...),
    description: str = Form(...),
    amount: str = Form(...),
    transaction_type: str = Form(...),
    category_id: Optional[int] = Form(None),
    currency: str = Form("INR"),
    db: Session = Depends(get_db),
):
    amount_value = Decimal(amount.replace(",", "").strip())
    transaction = models.Transaction(
        date=datetime.strptime(date_value, "%Y-%m-%d").date(),
        description=description.strip(),
        amount=amount_value,
        transaction_type=transaction_type,
        original_currency=currency,
        exchange_rate=Decimal("1"),
        base_amount_inr=amount_value,
        account_id=account_id,
        category_id=category_id,
    )
    db.add(transaction)
    db.commit()
    sync_dashboard_metrics(db)
    return await settings_page(request, db)


@router.post("/transactions/{transaction_id}/category")
async def update_transaction_category(
    request: Request,
    transaction_id: int,
    category_id: int = Form(...),
    apply_same_upi: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    if apply_same_upi:
        updated_count = assign_category_to_matching_upi_transactions(db, transaction_id, category_id)
        message = f"Category applied to {updated_count} transaction(s) with the same UPI ID."
    else:
        assign_transaction_category(db, transaction_id, category_id)
        message = "Category updated successfully."

    sync_dashboard_metrics(db)
    transactions = db.query(models.Transaction).order_by(models.Transaction.date.desc()).all()
    categories = db.query(models.Category).order_by(models.Category.is_custom.asc(), models.Category.name.asc()).all()
    return templates.TemplateResponse(
        request=request,
        name="transactions.html",
        context={"transactions": transactions, "categories": categories, "message": message},
    )


@router.post("/categories")
async def add_category(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    create_custom_category(db, name.strip(), description.strip() if description else None)
    return await transactions_page(request, db)


@router.post("/theme")
async def update_theme(
    request: Request,
    theme: str = Form(...),
    db: Session = Depends(get_db),
):
    upsert_dashboard_state(db, "theme", theme)
    return JSONResponse({"status": "ok", "theme": theme})

from ..workers.tasks import process_statement_task, process_markdown_task, generate_ai_analysis_task

@router.post("/upload")
async def handle_upload(
    request: Request,
    account_id: int = Form(...),
    file: Optional[UploadFile] = File(None),
    password: Optional[str] = Form(None),
    markdown_text: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    message = ""
    
    # Process File
    if file and file.filename:
        os.makedirs("uploads", exist_ok=True)
        safe_filename = os.path.basename(file.filename)
        file_path = os.path.abspath(f"uploads/{uuid4().hex}_{safe_filename}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        upload_record = create_statement_upload(
            db=db,
            file_path=file_path,
            account_id=account_id,
            has_password=bool(password and password.strip()),
        )

        process_statement_task.delay(file_path, account_id, upload_record.id, password=password)
        message += f"Successfully uploaded {file.filename}. "

    # Process Markdown Text
    if markdown_text and markdown_text.strip():
        process_markdown_task.delay(markdown_text, account_id)
        message += "Markdown text submitted for processing. "
    
    if not message:
        message = "No data provided."

    return templates.TemplateResponse(
        request=request, 
        name="upload.html", 
        context={
            "accounts": db.query(models.Account).all(),
            "message": f"{message} Processing in background..."
        }
    )


@router.post("/upload/{upload_id}/reprocess")
async def reprocess_upload(
    request: Request,
    upload_id: int,
    db: Session = Depends(get_db),
):
    upload = db.query(models.StatementUpload).filter(models.StatementUpload.id == upload_id).first()
    if not upload:
        accounts = db.query(models.Account).all()
        uploads = db.query(models.StatementUpload).order_by(models.StatementUpload.created_at.desc()).all()
        return templates.TemplateResponse(
            request=request,
            name="upload.html",
            context={"accounts": accounts, "uploads": uploads, "message": "Upload record not found."},
        )

    upload.processed = False
    upload.processing_error = None
    db.commit()

    process_statement_task.delay(upload.file_path, upload.account_id, upload.id, password=None)

    accounts = db.query(models.Account).all()
    uploads = db.query(models.StatementUpload).order_by(models.StatementUpload.created_at.desc()).all()
    return templates.TemplateResponse(
        request=request,
        name="upload.html",
        context={
            "accounts": accounts,
            "uploads": uploads,
            "message": f"Reprocessing started for {upload.file_path.split('/')[-1]}",
        },
    )

from datetime import date
import markdown

@router.get("/stocks/{ticker}/data")
async def get_stock_chart_data(ticker: str, db: Session = Depends(get_db)):
    analyzer = StockAnalyzer(db)
    data = analyzer.get_historical_indicators(ticker)
    if not data:
        return JSONResponse({"status": "error", "message": "Ticker not found"}, status_code=404)
    return data

@router.get("/stocks/{ticker}/ai-analysis")
async def get_stock_ai_analysis(ticker: str, check_cache_only: bool = False, db: Session = Depends(get_db)):
    today = date.today()
    
    # Check if analysis was already generated today
    existing = db.query(models.AIAnalysisResult).filter(
        models.AIAnalysisResult.ticker == ticker,
        models.AIAnalysisResult.generated_date == today
    ).first()
    
    if existing:
        analysis_text = existing.analysis_text
        # Convert markdown to HTML with table support
        html_output = markdown.markdown(analysis_text, extensions=['tables', 'fenced_code', 'nl2br'])
        
        # Inject Bootstrap classes into the table
        html_output = html_output.replace('<table>', '<table class="table table-bordered table-striped table-hover mt-3">')
        html_output = html_output.replace('<thead>', '<thead class="table-dark">')
        
        return JSONResponse({"status": "success", "analysis_html": html_output})
    else:
        # If we are just checking cache or polling, return not_found
        return JSONResponse({"status": "not_found"})

@router.post("/stocks/{ticker}/ai-analysis")
async def post_stock_ai_analysis(ticker: str, db: Session = Depends(get_db)):
    today = date.today()
    
    # Check if analysis was already generated today
    existing = db.query(models.AIAnalysisResult).filter(
        models.AIAnalysisResult.ticker == ticker,
        models.AIAnalysisResult.generated_date == today
    ).first()
    
    if existing:
        return JSONResponse({"status": "success", "message": "Analysis already exists."})
    
    # Trigger background task
    generate_ai_analysis_task.delay(ticker)
    
    return JSONResponse({"status": "processing", "message": "Analysis started in background."})
