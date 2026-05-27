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
- Support CSV, XLSX, PDF, and **Markdown Text**.
- Use `pdfplumber` for PDF extraction, including **password-protected** files.
- Detect bank-specific layouts from the selected account name; HDFC uses its own XLS template, SBI uses its own encrypted Excel template, and Federal Bank PDFs use line-based PDF parsing.
- Manual ingestion via Markdown tables is supported through a dedicated text area.
- Standardize all transaction data into the `Transaction` model before database insertion.
- Handle varied amount formats (e.g., "1,234.56 Dr", "500.00 Cr") and date formats.
- Track every statement upload in `statement_uploads` with file path, password flag, timestamps, and processing status before background ingestion starts.
- Support category assignment on the All Transactions page and keep a seeded category catalog plus custom categories.
- Detect bank-specific statement layouts from the selected account name; use the HDFC and SBI templates for matching files, and unlock SBI statements with the configured password when needed.
- Persist parsed payment metadata in `transactions.extra_details` as JSON, including reference IDs, UPI IDs, descriptions, and exchange rates.
- When a transaction category changes, offer propagation to other transactions sharing the same UPI ID.

### Reconciliation Engine
- Internal transfers are identified by matching amounts and dates (±3 days) across different accounts.
- Always check for existing `internal_transfer_id` before attempting to reconcile.

### ML & Categorization
- Use `MultinomialNB` for transaction categorization.
- Categorization should be triggered as a background task after ingestion.

### Upload Tracking
- Create a `StatementUpload` record immediately when a file is received.
- Mark uploads as processed only after the ingestion task succeeds.
- Persist processing failures on the upload record for auditability.

### Settings & Workbench
- Use the `/settings` page as the central workspace for manual transactions, adding accounts, adding categories, and balance adjustments.
- Persist dashboard state and app settings in dedicated tables so theme, balance adjustments, and related preferences survive restarts.
- Exclude transactions tagged as `Self transfer` from balance calculations when the setting is enabled.
- Auto-reconcile interbank transfers using amount, date window, and extracted account numbers where available.

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
