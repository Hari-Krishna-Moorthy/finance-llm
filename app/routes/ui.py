from fastapi import APIRouter, Request, Depends, UploadFile, File, Form
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
import shutil
import os

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
    transactions = db.query(models.Transaction).order_by(models.Transaction.date.desc()).all()
    return templates.TemplateResponse(
        request=request, 
        name="transactions.html", 
        context={"transactions": transactions}
    )

from ..workers.tasks import process_statement_task, process_markdown_task
from typing import Optional

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
        file_path = os.path.abspath(f"uploads/{file.filename}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        process_statement_task.delay(file_path, account_id, password=password)
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
