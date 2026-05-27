# Finance LLM - Personal Finance & Reconciliation

Privacy-focused Personal Finance application built with FastAPI, PostgreSQL, and Celery.

## Features
- **Data Ingestion:** Upload `.csv`, `.xlsx`, and `.pdf` bank statements.
- **Categorization Engine:** Auto-categorize transactions using Naive Bayes.
- **Multi-Bank Reconciliation:** Automatically link transfers across accounts.
- **Multi-Currency Support:** Default to INR, accurate tracking of foreign expenditures.
- **Tax Tagging:** Flag transactions as tax-deductible.
- **Analytics:** Anomaly detection and recurring payment predictions.

## Tech Stack
- **Backend:** FastAPI
- **Database:** PostgreSQL (SQLAlchemy + Alembic)
- **Workers:** Celery + Redis
- **ML/Analytics:** Scikit-learn, Pandas, PDFPlumber

## Setup Instructions

1. **Clone and Setup Venv:**
   ```bash
   git clone <repo-url>
   cd finance-llm
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Environment Variables:**
   Create a `.env` file:
   ```env
   DATABASE_URL=postgresql://user:pass@localhost:5432/finance_db
   REDIS_URL=redis://localhost:6379/0
   ```

3. **Migrations:**
   ```bash
   alembic revision --autogenerate -m "Initial migration"
   alembic upgrade head
   ```

4. **Run Application:**
   ```bash
   # Start FastAPI
   uvicorn app.main:app --reload

   # Start Celery Worker
   celery -A app.workers.celery_app worker --loglevel=info
   ```

## Project Structure
- `app/models.py`: Database schema.
- `app/services/`: Core logic (Ingestion, ML, Reconciliation, Analytics).
- `app/workers/`: Celery task definitions.
- `app/routes/`: FastAPI routes.
- `app/templates/`: Jinja2 UI templates.
