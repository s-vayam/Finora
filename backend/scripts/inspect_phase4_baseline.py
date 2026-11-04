import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from app.models.company import Company
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.expense import Expense
from app.models.cash_transaction import CashTransaction
from app.models.monthly_cashflow import MonthlyCashflow
from app.models.ml_prediction import MLPrediction
from sqlalchemy import func

def inspect():
    db = SessionLocal()
    try:
        company = db.query(Company).first()
        comp_currency = getattr(company, "currency", None) or getattr(company, "base_currency", None)
        print("=== COMPANY INFO ===")
        print(f"Company ID: {company.company_id}, Name: {company.company_name}, Base Currency: {company.base_currency}")

        print("\n=== RECORD COUNTS ===")
        print(f"Customers: {db.query(Customer).count()}")
        print(f"Invoices: {db.query(Invoice).count()}")
        print(f"Invoice status distribution: {db.query(Invoice.status, func.count(Invoice.invoice_id)).group_by(Invoice.status).all()}")

        open_invs = db.query(Invoice).filter(Invoice.status == "OPEN").all()
        print(f"Open invoices: {len(open_invs)}")
        if open_invs:
            min_due = min(inv.due_date for inv in open_invs)
            max_due = max(inv.due_date for inv in open_invs)
            print(f"Open invoices due date range: {min_due} to {max_due}")
            currencies = set(inv.currency for inv in open_invs)
            print(f"Open invoices currencies: {currencies}")

        print(f"Payments: {db.query(Payment).count()}")
        total_paid = db.query(func.sum(Payment.amount)).scalar()
        print(f"Total payments sum: {total_paid}")

        print(f"Expenses: {db.query(Expense).count()}")
        expense_cats = db.query(Expense.category, func.count(Expense.expense_id), func.sum(Expense.amount)).group_by(Expense.category).all()
        print("Expense categories:")
        for cat, cnt, amt in expense_cats:
            print(f"  {cat}: count={cnt}, sum={amt}")

        expense_currencies = db.query(Expense.currency, func.count(Expense.expense_id)).group_by(Expense.currency).all()
        print(f"Expense currencies: {expense_currencies}")

        print(f"Cash transactions: {db.query(CashTransaction).count()}")
        txn_types = db.query(CashTransaction.transaction_type, func.count(CashTransaction.transaction_id), func.sum(CashTransaction.amount)).group_by(CashTransaction.transaction_type).all()
        print("Cash transactions by type:")
        for t, cnt, amt in txn_types:
            print(f"  {t}: count={cnt}, sum={amt}")

        min_txn_date = db.query(func.min(CashTransaction.transaction_date)).scalar()
        max_txn_date = db.query(func.max(CashTransaction.transaction_date)).scalar()
        print(f"Cash transactions date range: {min_txn_date} to {max_txn_date}")

        print(f"Monthly cash flow records: {db.query(MonthlyCashflow).count()}")
        min_mcf = db.query(func.min(MonthlyCashflow.month)).scalar()
        max_mcf = db.query(func.max(MonthlyCashflow.month)).scalar()
        print(f"Monthly cash flow range: {min_mcf} to {max_mcf}")

        last_mcf = db.query(MonthlyCashflow).filter(MonthlyCashflow.month == max_mcf).first()
        print(f"Latest monthly cash-flow closing balance ({max_mcf}): {last_mcf.closing_balance} {last_mcf.currency}")

        print(f"ML predictions: {db.query(MLPrediction).count()}")

        # Check latest completed historical month and latest transaction
        print("\n=== DATA FRESHNESS BASELINE ===")
        print(f"Latest cash transaction date: {max_txn_date}")
        print(f"Latest monthly cash-flow month: {max_mcf}")

    finally:
        db.close()

if __name__ == "__main__":
    inspect()
