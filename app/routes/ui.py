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
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "transactions": transactions,
        "total_balance": total_balance
    })

@router.get("/upload")
async def upload_page(request: Request, db: Session = Depends(get_db)):
    accounts = db.query(models.Account).all()
    return templates.TemplateResponse("upload.html", {"request": request, "accounts": accounts})

@router.post("/upload")
async def handle_upload(
    request: Request,
    account_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Save the file temporarily
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Trigger background task (Phase 3)
    # For now, just a placeholder
    print(f"File {file.filename} uploaded for account {account_id}")
    
    return templates.TemplateResponse("upload.html", {
        "request": request, 
        "accounts": db.query(models.Account).all(),
        "message": f"Successfully uploaded {file.filename}. Processing in background..."
    })
