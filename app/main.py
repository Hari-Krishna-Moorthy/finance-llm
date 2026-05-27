from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from .database import get_db, engine
from . import models

# Create database tables (if not using migrations for local development)
# In production, we should use Alembic
# models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Finance LLM")

# Static files and Templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/")
async def home(request: Request, db: Session = Depends(get_db)):
    # Simple dashboard summary (to be implemented)
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
