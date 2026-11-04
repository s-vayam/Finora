import csv
from decimal import Decimal
from pathlib import Path
import tempfile
import pytest
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.company import Company
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.expense import Expense
from app.models.cash_transaction import CashTransaction
from app.models.monthly_cashflow import MonthlyCashflow
from app.services.data_import_service import DataImportService, DataImportError

def test_dry_run_import(test_db_session: Session, raw_data_dir: Path):
    """Test that dry run validates all data without persisting anything to the database."""
    service = DataImportService(data_dir=raw_data_dir, db=test_db_session)
    summary = service.import_all(dry_run=True, force=False)

    assert summary["status"] == "dry_run_success"
    assert summary["dry_run"] is True
    assert summary["imported_counts"]["customers"] == 60
    assert summary["imported_counts"]["invoices"] == 899
    assert summary["imported_counts"]["expenses"] == 872
    assert summary["imported_counts"]["cash_transactions"] == 1722
    assert summary["imported_counts"]["monthly_cashflow"] == 36

    # Verify database remains completely empty
    assert test_db_session.query(func.count(Customer.customer_id)).scalar() == 0
    assert test_db_session.query(func.count(Invoice.invoice_id)).scalar() == 0
    assert test_db_session.query(func.count(Expense.expense_id)).scalar() == 0
    assert test_db_session.query(func.count(CashTransaction.transaction_id)).scalar() == 0
    assert test_db_session.query(func.count(MonthlyCashflow.id)).scalar() == 0

def test_successful_seed_import(test_db_session: Session, raw_data_dir: Path):
    """Test full actual import into empty database and verify exact record counts."""
    service = DataImportService(data_dir=raw_data_dir, db=test_db_session)
    summary = service.import_all(dry_run=False, force=False)

    assert summary["status"] == "success"
    assert summary["dry_run"] is False

    # Check database counts
    assert test_db_session.query(func.count(Company.company_id)).scalar() == 1
    assert test_db_session.query(func.count(Customer.customer_id)).scalar() == 60
    assert test_db_session.query(func.count(Invoice.invoice_id)).scalar() == 899
    assert test_db_session.query(func.count(Expense.expense_id)).scalar() == 872
    assert test_db_session.query(func.count(CashTransaction.transaction_id)).scalar() == 1722
    assert test_db_session.query(func.count(MonthlyCashflow.id)).scalar() == 36

def test_duplicate_import_handling(test_db_session: Session, raw_data_dir: Path):
    """Test that repeating import without force is idempotent and safely detects already-seeded state."""
    service = DataImportService(data_dir=raw_data_dir, db=test_db_session)
    # First import
    res1 = service.import_all(dry_run=False, force=False)
    assert res1["status"] == "success"

    # Second import without force
    res2 = service.import_all(dry_run=False, force=False)
    assert res2["status"] == "skipped_already_seeded"
    assert "already imported" in res2["message"]

    # Verify counts did not double
    assert test_db_session.query(func.count(Customer.customer_id)).scalar() == 60
    assert test_db_session.query(func.count(Invoice.invoice_id)).scalar() == 899

def test_invalid_row_handling_and_rollback(test_db_session: Session, raw_data_dir: Path):
    """Test that an invalid record raises an error and the entire transaction is rolled back atomically."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Copy valid customers, invoices, expenses, monthly_cashflow
        for fname in ["customers.csv", "expenses.csv", "cash_transactions.csv", "monthly_cashflow.csv"]:
            content = (raw_data_dir / fname).read_text(encoding="utf-8")
            (temp_path / fname).write_text(content, encoding="utf-8")

        # Create corrupted invoices.csv with an invalid date
        inv_content = (raw_data_dir / "invoices.csv").read_text(encoding="utf-8").splitlines()
        # Corrupt first data line with bad date
        first_row_parts = inv_content[1].split(",")
        first_row_parts[6] = "NOT_A_DATE"  # invoice_date column
        inv_content[1] = ",".join(first_row_parts)
        (temp_path / "invoices.csv").write_text("\n".join(inv_content), encoding="utf-8")

        service = DataImportService(data_dir=temp_path, db=test_db_session)
        with pytest.raises(DataImportError) as exc_info:
            service.import_all(dry_run=False, force=False)

        assert "Invalid date format" in str(exc_info.value)

        # Verify atomic rollback: customer records were NOT committed to database
        assert test_db_session.query(func.count(Customer.customer_id)).scalar() == 0
        assert test_db_session.query(func.count(Invoice.invoice_id)).scalar() == 0

def test_missing_files_error_reporting(test_db_session: Session):
    """Test that missing required CSV files are detected and reported clearly without fabricating data."""
    with tempfile.TemporaryDirectory() as empty_dir:
        service = DataImportService(data_dir=Path(empty_dir), db=test_db_session)
        with pytest.raises(FileNotFoundError) as exc_info:
            service.import_all()
        assert "Missing required dataset file" in str(exc_info.value)

def test_monthly_cashflow_balance_reconciliation(test_db_session: Session, raw_data_dir: Path):
    """Test mathematical consistency of all 36 monthly cashflow records and reconciliation with transactions."""
    service = DataImportService(data_dir=raw_data_dir, db=test_db_session)
    service.import_all(dry_run=False, force=False)

    monthly_records = test_db_session.query(MonthlyCashflow).order_by(MonthlyCashflow.month.asc()).all()
    assert len(monthly_records) == 36

    prev_closing = None
    for rec in monthly_records:
        # Arithmetic reconciliation
        assert rec.actual_inflows - rec.actual_outflows == rec.net_cash_flow, f"Net mismatch at {rec.month}"
        assert rec.opening_balance + rec.net_cash_flow == rec.closing_balance, f"Closing mismatch at {rec.month}"

        # Continuity rollover
        if prev_closing is not None:
            assert rec.opening_balance == prev_closing, f"Opening balance rollover mismatch at {rec.month}"
        prev_closing = rec.closing_balance

        # Transaction reconciliation
        inflows_sum = (
            test_db_session.query(func.sum(CashTransaction.amount))
            .filter(
                CashTransaction.transaction_type == "INFLOW",
                func.strftime("%Y-%m", CashTransaction.transaction_date) == rec.month,
            )
            .scalar()
            or Decimal("0")
        )
        assert abs(rec.actual_inflows - inflows_sum) < Decimal("0.01"), f"Inflow sum mismatch at {rec.month}"

        outflows_sum = (
            test_db_session.query(func.sum(CashTransaction.amount))
            .filter(
                CashTransaction.transaction_type == "OUTFLOW",
                func.strftime("%Y-%m", CashTransaction.transaction_date) == rec.month,
            )
            .scalar()
            or Decimal("0")
        )
        assert abs(rec.actual_outflows - outflows_sum) < Decimal("0.01"), f"Outflow sum mismatch at {rec.month}"

