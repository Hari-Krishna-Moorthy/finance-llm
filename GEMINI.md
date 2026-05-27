# Project Skill: Finance LLM Architect

This file contains the foundational mandates, architectural patterns, and workflows for the `finance-llm` project. Adhere to these instructions for all modifications.

## Core Mandates
- **Privacy First:** Ensure all data ingestion and processing logic respects user privacy. Do not log sensitive financial data.
- **Technical Integrity:** Maintain strict type safety in FastAPI and SQLAlchemy. Use migrations (Alembic) for all schema changes.
- **Auto-Update:** Whenever a new module, service, or architectural pattern is introduced, update this `GEMINI.md` file to reflect the changes.

## Tech Stack & Conventions
- **Backend:** FastAPI (Python 3.14+). Use dependency injection for database sessions.
- **Database:** PostgreSQL with SQLAlchemy 2.0+ ORM. Follow the multi-currency pattern (`original_currency`, `exchange_rate`, `base_amount_inr`).
- **Asynchronous Tasks:** Celery + Redis for all long-running tasks (parsing, ML, reconciliation).
- **Styling:** Server-side rendering with Jinja2 and Bootstrap 5.

## Specialized Workflows

### Data Ingestion
- Support CSV, XLSX, and PDF.
- Use `pdfplumber` for PDF extraction.
- Standardize all transaction data into the `Transaction` model before database insertion.

### Reconciliation Engine
- Internal transfers are identified by matching amounts and dates (±3 days) across different accounts.
- Always check for existing `internal_transfer_id` before attempting to reconcile.

### ML & Categorization
- Use `MultinomialNB` for transaction categorization.
- Categorization should be triggered as a background task after ingestion.

### Analytics & Anomaly Detection
- Use Z-score (threshold > 3) for identifying spending anomalies.
- Group by description and amount for recurring payment prediction.

## Testing Standards
- **Reproduction:** Before fixing a bug, create a reproduction script or test case.
- **Coverage:** Add unit tests for all new services in the `tests/` directory.
- **Validation:** Run `pytest` to verify changes.

## Implementation Lifecycle
1. **Research:** Map dependencies and validate assumptions using `grep_search` and `read_file`.
2. **Strategy:** Formulate a plan and share a concise summary.
3. **Execution:** Plan -> Act -> Validate. Include tests in the same turn as the implementation.
