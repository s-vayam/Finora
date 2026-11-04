from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, select

from app.database import get_db
from app.models.company import Company
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.expense import Expense
from app.models.cash_transaction import CashTransaction
from app.models.monthly_cashflow import MonthlyCashflow
from app.schemas.common import SeedStatusResponse, DataSummaryResponse, DateRange

router = APIRouter(prefix="/meta", tags=["Metadata"])

@router.get("/seed-status", response_model=SeedStatusResponse)
def get_seed_status(db: Session = Depends(get_db)):
    """Return whether seed data has been imported, dataset identifier, timestamp, and counts."""
    company = db.query(Company).filter(Company.company_id == "FINORA_DEMO").first()
    if not company:
        return SeedStatusResponse(
            seeded=False,
            dataset_id=None,
            import_timestamp=None,
            record_counts={},
        )

    counts = {
        "companies": db.query(func.count(Company.company_id)).filter(Company.company_id == "FINORA_DEMO").scalar() or 0,
        "customers": db.query(func.count(Customer.customer_id)).filter(Customer.company_id == "FINORA_DEMO").scalar() or 0,
        "invoices": db.query(func.count(Invoice.invoice_id)).filter(Invoice.company_id == "FINORA_DEMO").scalar() or 0,
        "expenses": db.query(func.count(Expense.expense_id)).filter(Expense.company_id == "FINORA_DEMO").scalar() or 0,
        "cash_transactions": db.query(func.count(CashTransaction.transaction_id)).filter(CashTransaction.company_id == "FINORA_DEMO").scalar() or 0,
        "monthly_cashflow": db.query(func.count(MonthlyCashflow.id)).filter(MonthlyCashflow.company_id == "FINORA_DEMO").scalar() or 0,
    }

    return SeedStatusResponse(
        seeded=counts["customers"] > 0,
        dataset_id="FINORA_DEMO",
        import_timestamp=company.created_at.isoformat() if company.created_at else None,
        record_counts=counts,
    )

@router.get("/data-summary", response_model=DataSummaryResponse)
def get_data_summary(db: Session = Depends(get_db)):
    """Return global summary metrics for the imported dataset."""
    total_customers = db.query(func.count(Customer.customer_id)).scalar() or 0
    total_invoices = db.query(func.count(Invoice.invoice_id)).scalar() or 0
    total_paid_invoices = db.query(func.count(Invoice.invoice_id)).filter(Invoice.status == "PAID").scalar() or 0
    total_open_invoices = db.query(func.count(Invoice.invoice_id)).filter(Invoice.status == "OPEN").scalar() or 0
    total_expenses = db.query(func.count(Expense.expense_id)).scalar() or 0
    total_cash_transactions = db.query(func.count(CashTransaction.transaction_id)).scalar() or 0
    available_historical_months = db.query(func.count(MonthlyCashflow.id)).scalar() or 0

    # Dataset date range across invoices and transactions
    min_inv_date = db.query(func.min(Invoice.invoice_date)).scalar()
    max_inv_date = db.query(func.max(Invoice.invoice_date)).scalar()
    min_tx_date = db.query(func.min(CashTransaction.transaction_date)).scalar()
    max_tx_date = db.query(func.max(CashTransaction.transaction_date)).scalar()

    dates = [d for d in (min_inv_date, min_tx_date) if d is not None]
    start_date_str = str(min(dates)) if dates else None

    end_dates = [d for d in (max_inv_date, max_tx_date) if d is not None]
    end_date_str = str(max(end_dates)) if end_dates else None

    return DataSummaryResponse(
        total_customers=total_customers,
        total_invoices=total_invoices,
        total_paid_invoices=total_paid_invoices,
        total_open_invoices=total_open_invoices,
        total_expenses=total_expenses,
        total_cash_transactions=total_cash_transactions,
        available_historical_months=available_historical_months,
        dataset_date_range=DateRange(
            start_date=start_date_str,
            end_date=end_date_str,
        ),
    )

