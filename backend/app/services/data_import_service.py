import csv
import logging
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.company import Company
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.expense import Expense
from app.models.cash_transaction import CashTransaction
from app.models.monthly_cashflow import MonthlyCashflow

logger = logging.getLogger(__name__)

REQUIRED_FILES = [
    "customers.csv",
    "invoices.csv",
    "expenses.csv",
    "cash_transactions.csv",
    "monthly_cashflow.csv",
]

class DataImportError(Exception):
    """Custom exception raised when data import validation fails."""
    pass

class DataImportService:
    def __init__(self, data_dir: Path, db: Session):
        self.data_dir = Path(data_dir)
        self.db = db

    def verify_files_exist(self) -> None:
        """Verify all required CSV files exist in data_dir."""
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Raw data directory does not exist: {self.data_dir.resolve()}")
        
        missing = [f for f in REQUIRED_FILES if not (self.data_dir / f).is_file()]
        if missing:
            raise FileNotFoundError(
                f"Missing required dataset file(s) in {self.data_dir.resolve()}: {', '.join(missing)}"
            )

    def is_already_seeded(self, company_id: str = "FINORA_DEMO") -> bool:
        """Check if seed data for company already exists in the database."""
        stmt = select(func.count(Customer.customer_id)).where(Customer.company_id == company_id)
        count = self.db.scalar(stmt)
        return bool(count and count > 0)

    def parse_date(self, val: Optional[str], field_name: str, row_id: str) -> Optional[date]:
        if not val or not val.strip():
            return None
        val_clean = val.strip()
        try:
            return datetime.strptime(val_clean, "%Y-%m-%d").date()
        except ValueError as e:
            raise DataImportError(f"Invalid date format '{val_clean}' for field '{field_name}' in row '{row_id}': {e}")

    def parse_decimal(self, val: Optional[str], field_name: str, row_id: str) -> Decimal:
        if val is None or not val.strip():
            raise DataImportError(f"Missing required numeric value for field '{field_name}' in row '{row_id}'")
        try:
            return Decimal(val.strip())
        except (InvalidOperation, ValueError) as e:
            raise DataImportError(f"Invalid decimal value '{val}' for field '{field_name}' in row '{row_id}': {e}")

    def parse_int(self, val: Optional[str], field_name: str, row_id: str, default: Optional[int] = None) -> Optional[int]:
        if not val or not val.strip():
            return default
        try:
            return int(val.strip())
        except ValueError as e:
            raise DataImportError(f"Invalid integer value '{val}' for field '{field_name}' in row '{row_id}': {e}")

    def import_all(self, dry_run: bool = False, force: bool = False) -> Dict[str, Any]:
        """
        Validate and import all seed data within an atomic transaction.
        If dry_run is True, validate everything without committing.
        """
        self.verify_files_exist()

        company_id = "FINORA_DEMO"
        if not force and self.is_already_seeded(company_id):
            return {
                "status": "skipped_already_seeded",
                "message": f"Seed data for company '{company_id}' is already imported. Use force=True to re-import.",
                "company_id": company_id,
                "dry_run": dry_run,
                "imported_counts": self.get_current_counts(company_id),
                "timestamp": datetime.utcnow().isoformat(),
            }

        summary = {
            "status": "success" if not dry_run else "dry_run_success",
            "company_id": company_id,
            "dry_run": dry_run,
            "imported_counts": {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        # If force=True, delete existing data in reverse dependency order
        if force and not dry_run:
            logger.info("Force flag enabled. Clearing existing records for %s", company_id)
            self.db.query(MonthlyCashflow).filter(MonthlyCashflow.company_id == company_id).delete()
            self.db.query(CashTransaction).filter(CashTransaction.company_id == company_id).delete()
            self.db.query(Expense).filter(Expense.company_id == company_id).delete()
            self.db.query(Invoice).filter(Invoice.company_id == company_id).delete()
            self.db.query(Customer).filter(Customer.company_id == company_id).delete()
            self.db.query(Company).filter(Company.company_id == company_id).delete()
            self.db.flush()

        try:
            # 1. Company
            company = self.db.query(Company).filter(Company.company_id == company_id).first()
            if not company:
                company = Company(
                    company_id=company_id,
                    company_name="Finora Demo Trading Co.",
                    base_currency="INR",
                    created_at=datetime.utcnow(),
                )
                if not dry_run:
                    self.db.add(company)
                    self.db.flush()
            summary["imported_counts"]["companies"] = 1

            # Track IDs in memory for foreign key validation
            customer_ids: Set[str] = set()
            invoice_ids: Set[str] = set()

            # 2. Customers
            customers_path = self.data_dir / "customers.csv"
            customer_records: List[Customer] = []
            with open(customers_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row_idx, row in enumerate(reader, start=1):
                    cid = row["customer_id"].strip()
                    if cid in customer_ids:
                        raise DataImportError(f"Duplicate customer_id '{cid}' in customers.csv at line {row_idx}")
                    customer_ids.add(cid)

                    cust = Customer(
                        customer_id=cid,
                        company_id=row["company_id"].strip(),
                        customer_name=row["customer_name"].strip(),
                        country=row["country"].strip(),
                        industry=row["industry"].strip(),
                        default_payment_terms_days=self.parse_int(row.get("default_payment_terms_days"), "default_payment_terms_days", cid, 30),
                    )
                    customer_records.append(cust)

            if not dry_run:
                self.db.add_all(customer_records)
                self.db.flush()
            summary["imported_counts"]["customers"] = len(customer_records)

            # 3. Invoices
            invoices_path = self.data_dir / "invoices.csv"
            invoice_records: List[Invoice] = []
            with open(invoices_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row_idx, row in enumerate(reader, start=1):
                    inv_id = row["invoice_id"].strip()
                    if inv_id in invoice_ids:
                        raise DataImportError(f"Duplicate invoice_id '{inv_id}' in invoices.csv at line {row_idx}")
                    invoice_ids.add(inv_id)

                    cid = row["customer_id"].strip()
                    if cid not in customer_ids:
                        raise DataImportError(f"Foreign key mismatch: customer_id '{cid}' on invoice '{inv_id}' does not exist.")

                    late_rate_str = row.get("historical_late_rate")
                    late_rate = Decimal(late_rate_str.strip()) if late_rate_str and late_rate_str.strip() else None

                    inv = Invoice(
                        invoice_id=inv_id,
                        company_id=row["company_id"].strip(),
                        customer_id=cid,
                        invoice_date=self.parse_date(row["invoice_date"], "invoice_date", inv_id),
                        due_date=self.parse_date(row["due_date"], "due_date", inv_id),
                        actual_payment_date=self.parse_date(row.get("actual_payment_date"), "actual_payment_date", inv_id),
                        payment_terms_days=self.parse_int(row["payment_terms_days"], "payment_terms_days", inv_id),
                        invoice_amount=self.parse_decimal(row["invoice_amount"], "invoice_amount", inv_id),
                        currency=row["currency"].strip(),
                        status=row["status"].strip(),
                        historical_invoice_count=self.parse_int(row.get("historical_invoice_count"), "historical_invoice_count", inv_id),
                        historical_late_rate=late_rate,
                    )
                    invoice_records.append(inv)

            if not dry_run:
                self.db.add_all(invoice_records)
                self.db.flush()
            summary["imported_counts"]["invoices"] = len(invoice_records)

            # 4. Expenses
            expenses_path = self.data_dir / "expenses.csv"
            expense_records: List[Expense] = []
            expense_ids: Set[str] = set()
            with open(expenses_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row_idx, row in enumerate(reader, start=1):
                    exp_id = row["expense_id"].strip()
                    if exp_id in expense_ids:
                        raise DataImportError(f"Duplicate expense_id '{exp_id}' in expenses.csv at line {row_idx}")
                    expense_ids.add(exp_id)

                    linked_inv = row.get("linked_invoice_id", "").strip() or None
                    if linked_inv and linked_inv not in invoice_ids:
                        raise DataImportError(f"Foreign key mismatch: linked_invoice_id '{linked_inv}' on expense '{exp_id}' does not exist.")

                    exp = Expense(
                        expense_id=exp_id,
                        company_id=row["company_id"].strip(),
                        expense_date=self.parse_date(row["expense_date"], "expense_date", exp_id),
                        due_date=self.parse_date(row["due_date"], "due_date", exp_id),
                        actual_payment_date=self.parse_date(row.get("actual_payment_date"), "actual_payment_date", exp_id),
                        category=row["category"].strip(),
                        amount=self.parse_decimal(row["amount"], "amount", exp_id),
                        currency=row["currency"].strip(),
                        status=row["status"].strip(),
                        linked_invoice_id=linked_inv,
                    )
                    expense_records.append(exp)

            if not dry_run:
                self.db.add_all(expense_records)
                self.db.flush()
            summary["imported_counts"]["expenses"] = len(expense_records)

            # 5. Cash Transactions
            tx_path = self.data_dir / "cash_transactions.csv"
            tx_records: List[CashTransaction] = []
            tx_ids: Set[str] = set()
            with open(tx_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row_idx, row in enumerate(reader, start=1):
                    txn_id = row["transaction_id"].strip()
                    if txn_id in tx_ids:
                        raise DataImportError(f"Duplicate transaction_id '{txn_id}' in cash_transactions.csv at line {row_idx}")
                    tx_ids.add(txn_id)

                    linked_inv = row.get("linked_invoice_id", "").strip() or None
                    if linked_inv and linked_inv not in invoice_ids:
                        raise DataImportError(f"Foreign key mismatch: linked_invoice_id '{linked_inv}' on txn '{txn_id}' does not exist.")

                    counterparty = row.get("counterparty_id", "").strip() or None

                    ttype = row["transaction_type"].strip()
                    if ttype not in ("INFLOW", "OUTFLOW"):
                        raise DataImportError(f"Invalid transaction_type '{ttype}' in row '{txn_id}'")

                    txn = CashTransaction(
                        transaction_id=txn_id,
                        company_id=row["company_id"].strip(),
                        transaction_date=self.parse_date(row["transaction_date"], "transaction_date", txn_id),
                        transaction_type=ttype,
                        category=row["category"].strip(),
                        amount=self.parse_decimal(row["amount"], "amount", txn_id),
                        currency=row["currency"].strip(),
                        linked_invoice_id=linked_inv,
                        counterparty_id=counterparty,
                        description=row.get("description", "").strip(),
                    )
                    tx_records.append(txn)

            if not dry_run:
                self.db.add_all(tx_records)
                self.db.flush()
            summary["imported_counts"]["cash_transactions"] = len(tx_records)

            # 6. Monthly Cash Flow
            cf_path = self.data_dir / "monthly_cashflow.csv"
            cf_records: List[MonthlyCashflow] = []
            seen_months: Set[str] = set()
            with open(cf_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row_idx, row in enumerate(reader, start=1):
                    m = row["month"].strip()
                    if m in seen_months:
                        raise DataImportError(f"Duplicate month '{m}' in monthly_cashflow.csv at line {row_idx}")
                    seen_months.add(m)

                    cf = MonthlyCashflow(
                        company_id=row["company_id"].strip(),
                        month=m,
                        opening_balance=self.parse_decimal(row["opening_balance"], "opening_balance", m),
                        actual_inflows=self.parse_decimal(row["actual_inflows"], "actual_inflows", m),
                        actual_outflows=self.parse_decimal(row["actual_outflows"], "actual_outflows", m),
                        net_cash_flow=self.parse_decimal(row["net_cash_flow"], "net_cash_flow", m),
                        closing_balance=self.parse_decimal(row["closing_balance"], "closing_balance", m),
                        inflow_transactions=self.parse_int(row["inflow_transactions"], "inflow_transactions", m),
                        outflow_transactions=self.parse_int(row["outflow_transactions"], "outflow_transactions", m),
                        currency=row["currency"].strip(),
                    )
                    cf_records.append(cf)

            if not dry_run:
                self.db.add_all(cf_records)
                self.db.commit()
            else:
                self.db.rollback()

            summary["imported_counts"]["monthly_cashflow"] = len(cf_records)
            return summary

        except Exception as e:
            self.db.rollback()
            logger.error("Data import failed and was rolled back: %s", str(e), exc_info=True)
            raise

    def get_current_counts(self, company_id: str = "FINORA_DEMO") -> Dict[str, int]:
        """Fetch current record counts in database for company."""
        return {
            "companies": self.db.query(func.count(Company.company_id)).filter(Company.company_id == company_id).scalar() or 0,
            "customers": self.db.query(func.count(Customer.customer_id)).filter(Customer.company_id == company_id).scalar() or 0,
            "invoices": self.db.query(func.count(Invoice.invoice_id)).filter(Invoice.company_id == company_id).scalar() or 0,
            "expenses": self.db.query(func.count(Expense.expense_id)).filter(Expense.company_id == company_id).scalar() or 0,
            "cash_transactions": self.db.query(func.count(CashTransaction.transaction_id)).filter(CashTransaction.company_id == company_id).scalar() or 0,
            "monthly_cashflow": self.db.query(func.count(MonthlyCashflow.id)).filter(MonthlyCashflow.company_id == company_id).scalar() or 0,
        }
