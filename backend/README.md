# Finora Backend — Phase 1 & 2: Invoices, Customers & Payment Management

Backend REST service for **Finora — AI Financial Co-Pilot for International Trade**.

Phase 1 established the database foundation and read-only APIs.
Phase 2 introduces the dedicated `payments` table, Alembic migrations, historical payment backfill, invoice CRUD, customer management, and atomic payment processing with idempotency and balance enforcement.

---

## 1. Technology Stack

- **Python**: 3.11+ (verified on 3.14)
- **FastAPI**: 0.162.0 (REST API framework)
- **Database**: SQLite with strict `PRAGMA foreign_keys = ON`
- **ORM**: SQLAlchemy 2.x (declarative models, Decimal types for currency)
- **Migrations**: Alembic 1.20+
- **Validation**: Pydantic v2 & Pydantic-Settings
- **Server**: Uvicorn (ASGI)
- **Testing**: Pytest & HTTPX TestClient

---

## 2. Directory Structure

```text
backend/
├── alembic/                   # Alembic database migration environment
│   ├── versions/
│   │   └── 001_create_payments_table.py # Phase 2 migration
│   ├── env.py
│   └── script.py.mako
├── alembic.ini                # Migration configuration
├── app/
│   ├── __init__.py
│   ├── config.py              # Centralized environment settings
│   ├── database.py            # SQLite engine, sessions & FK enforcement
│   ├── main.py                # FastAPI entrypoint, CORS, error handling
│   ├── models/                # SQLAlchemy 2.x declarative models
│   │   ├── __init__.py
│   │   ├── company.py         # Company model
│   │   ├── customer.py        # Customer model
│   │   ├── invoice.py         # Invoice model
│   │   ├── expense.py         # Expense model
│   │   ├── cash_transaction.py# Cash transaction model
│   │   ├── monthly_cashflow.py# Monthly aggregated cash flow model
│   │   └── payment.py         # Phase 2 dedicated payments model
│   ├── schemas/               # Pydantic v2 validation models
│   │   ├── __init__.py
│   │   ├── common.py          # PaginatedResponse, Health, SeedStatus
│   │   ├── customer.py        # CustomerCreate, Update, Response
│   │   ├── invoice.py         # InvoiceCreate, Update, Response, Detail
│   │   ├── expense.py         # Expense schemas
│   │   ├── cashflow.py        # Cash flow & Transaction schemas
│   │   └── payment.py         # PaymentCreate, Response, Detail, History
│   ├── routers/               # FastAPI routers (/api/v1)
│   │   ├── __init__.py
│   │   ├── health.py          # Health check
│   │   ├── metadata.py        # Seed status & data summary
│   │   ├── customers.py       # Customer CRUD endpoints
│   │   ├── invoices.py        # Invoice CRUD & payment processing
│   │   ├── expenses.py        # Expenses with category filtering
│   │   ├── transactions.py    # Cash transactions with type & date filters
│   │   ├── cashflow.py        # 36-month chronological cash flow
│   │   └── payments.py        # Payment listing & details
│   └── services/
│       ├── __init__.py
│       ├── data_import_service.py    # Seed data import & validation
│       ├── payment_backfill_service.py # Historical payment backfill
│       └── invoice_status_service.py # Centralized financial status calculations
├── data/
│   ├── raw/
│   │   └── finora_synthetic_data/    # Raw synthetic CSV datasets
│   └── database/
│       └── finora.db                 # Development SQLite database
├── scripts/
│   ├── import_seed_data.py           # Seed data importer
│   ├── validate_seed_data.py         # Data validation auditor
│   ├── backfill_payments.py          # Historical payment backfill CLI
│   └── audit_phase2_integrity.py     # Phase 2 data integrity auditor
├── tests/
│   ├── conftest.py                   # Isolated test DB fixtures & TestClient
│   ├── test_health.py                # Health & root tests
│   ├── test_database.py              # Schema, FK & constraint tests
│   ├── test_data_import.py           # Ingestion integrity & rollback tests
│   ├── test_read_apis.py             # Read API tests
│   ├── test_migration.py             # Alembic migration tests
│   ├── test_backfill.py              # Historical backfill tests
│   ├── test_customer_apis.py         # Customer CRUD tests
│   ├── test_invoice_apis.py          # Invoice CRUD & cancellation tests
│   └── test_payment_apis.py          # Full, partial, atomic, and idempotency tests
├── .env.example
├── .gitignore
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## 3. Local Setup & Execution

### Step 1: Virtual Environment
```powershell
cd c:\Users\Svayam\PROJECTTTT\Finora\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Database Migration
```powershell
alembic upgrade head
```

### Step 3: Historical Payment Backfill
```powershell
python scripts/backfill_payments.py
```

### Step 4: Data Integrity Audit
```powershell
python scripts/audit_phase2_integrity.py
```

### Step 5: Start API Server
```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- Interactive Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health Check: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

---

## 4. Automated Tests

Run the complete test suite (35 tests):
```powershell
pytest -v tests
```
