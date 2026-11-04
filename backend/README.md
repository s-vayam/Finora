# Finora Backend — Phase 1: Foundation & Database Setup

This is the backend service for **Finora — AI Financial Co-Pilot for International Trade**.

Phase 1 establishes the database schema, data validation & ingestion engine for the 36-month synthetic dataset (`FINORA_DEMO`), and read-only REST APIs verified with automated tests.

---

## 1. Technology Stack

- **Python**: 3.11+ (verified on 3.14)
- **Framework**: FastAPI (REST API framework)
- **Database**: SQLite with strict `PRAGMA foreign_keys = ON`
- **ORM**: SQLAlchemy 2.x (declarative models, Decimal types for currency)
- **Validation**: Pydantic v2 & Pydantic-Settings
- **Server**: Uvicorn (ASGI)
- **Testing**: Pytest & HTTPX TestClient

---

## 2. Directory Structure

```text
backend/
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
│   │   └── monthly_cashflow.py# Monthly aggregated cash flow model
│   ├── schemas/               # Pydantic v2 schemas
│   │   ├── __init__.py
│   │   ├── common.py          # PaginatedResponse, Health, SeedStatus
│   │   ├── customer.py        # Customer schemas
│   │   ├── invoice.py         # Invoice schemas
│   │   ├── expense.py         # Expense schemas
│   │   └── cashflow.py        # Cash flow & Transaction schemas
│   ├── routers/               # FastAPI routers (/api/v1)
│   │   ├── __init__.py
│   │   ├── health.py          # Health check
│   │   ├── metadata.py        # Seed status & data summary
│   │   ├── customers.py       # Customer endpoints
│   │   ├── invoices.py        # Invoices with filtering & pagination
│   │   ├── expenses.py        # Expenses with category filtering
│   │   ├── transactions.py    # Cash transactions with type & date filters
│   │   └── cashflow.py        # 36-month chronological cash flow
│   └── services/
│       ├── __init__.py
│       └── data_import_service.py # Atomic data import & validation logic
├── data/
│   ├── raw/
│   │   └── finora_synthetic_data/ # Raw synthetic CSV datasets
│   └── database/
│       └── finora.db          # Development SQLite database
├── scripts/
│   ├── import_seed_data.py    # CLI to import seed data (supports --dry-run, --force)
│   └── validate_seed_data.py  # CLI to perform accounting & FK validation
├── tests/
│   ├── conftest.py            # Pytest fixtures & isolated temporary test DB
│   ├── test_health.py         # Health & root endpoint tests
│   ├── test_database.py       # Schema, foreign key & constraint tests
│   ├── test_data_import.py    # Import integrity, dry-run, & rollback tests
│   └── test_read_apis.py      # Read API endpoint, pagination & filter tests
├── .env.example
├── .gitignore
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## 3. Local Setup Instructions

### Step 1: Create Virtual Environment
From the `backend/` directory:
```powershell
python -m venv .venv
```

### Step 2: Activate Virtual Environment
On Windows PowerShell:
```powershell
.venv\Scripts\activate
```

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Environment Variables (Optional)
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```

---

## 4. Seed Data Import & Validation

The raw synthetic dataset is located at `backend/data/raw/finora_synthetic_data/`.

### Run Validation Checks
Validates row counts, primary key uniqueness, foreign key validity, and monthly cash flow reconciliation against underlying transactions:
```powershell
python scripts/validate_seed_data.py
```

### Import Seed Data (Dry Run)
Validates all records without altering the database:
```powershell
python scripts/import_seed_data.py --dry-run
```

### Import Seed Data to SQLite Database
Populates `data/database/finora.db`:
```powershell
python scripts/import_seed_data.py
```

*Note: The import script is idempotent. Running it a second time without `--force` will detect the existing dataset and skip insertion to prevent duplicates.*

---

## 5. Starting the Backend API

From the `backend/` directory:
```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- **Interactive API Documentation (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative Documentation (ReDoc)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

---

## 6. API Endpoints Reference

All endpoints are prefixed with `/api/v1`:

| Method | Endpoint | Query Parameters | Description |
|---|---|---|---|
| `GET` | `/api/v1/health` | None | API and database connectivity status |
| `GET` | `/api/v1/meta/seed-status` | None | Dataset import status, company ID, and record counts |
| `GET` | `/api/v1/meta/data-summary` | None | Summary metrics (customer count, invoice totals, date range) |
| `GET` | `/api/v1/customers` | `page`, `page_size` | Paginated customer master records |
| `GET` | `/api/v1/invoices` | `page`, `page_size`, `customer_id`, `status`, `currency` | Paginated invoices with filtering |
| `GET` | `/api/v1/expenses` | `page`, `page_size`, `category` | Paginated expense items with category filter |
| `GET` | `/api/v1/transactions` | `page`, `page_size`, `transaction_type`, `start_date`, `end_date` | Paginated cash ledger with type & date range filters |
| `GET` | `/api/v1/cashflow/history` | None | 36-month chronological cash flow statements |

---

## 7. Automated Testing

To run the automated test suite using an isolated temporary database:
```powershell
pytest tests
```
Or with verbose output:
```powershell
pytest -v tests
```

