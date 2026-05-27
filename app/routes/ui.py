from fastapi import APIRouter, Request, Depends, UploadFile, File, Form
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from ..database import get_db
from .. import models
from ..services.upload_tracking import create_statement_upload
from ..services.categories import (
    assign_transaction_category,
    create_custom_category,
    seed_default_categories,
)
import shutil
import os
from uuid import uuid4

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/")
async def home(request: Request, db: Session = Depends(get_db)):
    transactions = db.query(models.Transaction).order_by(models.Transaction.date.desc()).limit(10).all()
    # Basic balance calculation (simplified)
    total_balance = 0 # To be calculated
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={
            "transactions": transactions,
            "total_balance": total_balance
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
    return templates.TemplateResponse(
        request=request, 
        name="upload.html", 
        context={"accounts": accounts}
    )

@router.get("/transactions")
async def transactions_page(request: Request, db: Session = Depends(get_db)):
    seed_default_categories(db)
    transactions = db.query(models.Transaction).order_by(models.Transaction.date.desc()).all()
    categories = db.query(models.Category).order_by(models.Category.is_custom.asc(), models.Category.name.asc()).all()
    return templates.TemplateResponse(
        request=request, 
        name="transactions.html", 
        context={"transactions": transactions, "categories": categories}
    )


@router.post("/transactions/{transaction_id}/category")
async def update_transaction_category(
    request: Request,
    transaction_id: int,
    category_id: int = Form(...),
    db: Session = Depends(get_db),
):
    assign_transaction_category(db, transaction_id, category_id)
    return await transactions_page(request, db)


@router.post("/categories")
async def add_category(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    create_custom_category(db, name.strip(), description.strip() if description else None)
    return await transactions_page(request, db)

from ..workers.tasks import process_statement_task, process_markdown_task

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
