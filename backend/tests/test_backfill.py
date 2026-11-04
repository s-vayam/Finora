from decimal import Decimal
from pathlib import Path
import pytest
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.invoice import Invoice
from app.models.cash_transaction import CashTransaction
from app.models.payment import Payment
from app.services.data_import_service import DataImportService
from app.services.payment_backfill_service import PaymentBackfillService, BackfillDiscrepancyError

def test_backfill_successful_and_exact_counts(test_db_session: Session, raw_data_dir: Path):
    """Test full backfill creates exactly 873 payment records linked to cash transactions."""
    # Seed base data
    import_service = DataImportService(data_dir=raw_data_dir, db=test_db_session)
    import_service.import_all(dry_run=False, force=False)

    backfill_service = PaymentBackfillService(db=test_db_session)
    summary = backfill_service.validate_and_backfill(dry_run=False, force=False)

    assert summary["status"] == "success"
    assert summary["total_paid_invoices"] == 873
    assert summary["total_inflows"] == 873
    assert summary["payments_backfilled"] == 873

    # Check payments table in database
    payment_count = test_db_session.query(func.count(Payment.payment_id)).scalar()
    assert payment_count == 873

    # Verify no cash transactions were duplicated
    txn_count = test_db_session.query(func.count(CashTransaction.transaction_id)).scalar()
    assert txn_count == 1722

    # Verify each backfilled payment links to its unique cash transaction
    payments = test_db_session.query(Payment).all()
    cash_txn_ids = {p.cash_transaction_id for p in payments}
    assert len(cash_txn_ids) == 873

    for p in payments:
        assert p.source == "SEED_BACKFILL"
        assert p.idempotency_key.startswith("BACKFILL-")
        assert p.amount > Decimal("0.00")
        assert p.currency == "INR"

def test_backfill_idempotency(test_db_session: Session, raw_data_dir: Path):
    """Test running backfill repeatedly does not create duplicate payment records."""
    import_service = DataImportService(data_dir=raw_data_dir, db=test_db_session)
    import_service.import_all(dry_run=False, force=False)

    backfill_service = PaymentBackfillService(db=test_db_session)
    # First run
    res1 = backfill_service.validate_and_backfill(dry_run=False, force=False)
    assert res1["status"] == "success"

    # Second run without force
    res2 = backfill_service.validate_and_backfill(dry_run=False, force=False)
    assert res2["status"] == "skipped_already_backfilled"

    # Confirm count remains 873
    payment_count = test_db_session.query(func.count(Payment.payment_id)).scalar()
    assert payment_count == 873

def test_backfill_detects_mismatch_and_aborts(test_db_session: Session, raw_data_dir: Path):
    """Test that data discrepancy causes backfill to abort with BackfillDiscrepancyError and roll back."""
    import_service = DataImportService(data_dir=raw_data_dir, db=test_db_session)
    import_service.import_all(dry_run=False, force=False)

    # Mutate one invoice amount to cause a mismatch with its linked transaction
    one_paid_inv = test_db_session.query(Invoice).filter(Invoice.status == "PAID").first()
    one_paid_inv.invoice_amount = one_paid_inv.invoice_amount + Decimal("1000.00")
    test_db_session.commit()

    backfill_service = PaymentBackfillService(db=test_db_session)
    with pytest.raises(BackfillDiscrepancyError) as exc_info:
        backfill_service.validate_and_backfill(dry_run=False, force=False)

    assert "Amount mismatch" in str(exc_info.value.discrepancies)

    # Verify zero payments were committed
    payment_count = test_db_session.query(func.count(Payment.payment_id)).scalar()
    assert payment_count == 0
