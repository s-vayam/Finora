import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.invoice import Invoice
from app.models.cash_transaction import CashTransaction
from app.models.payment import Payment

logger = logging.getLogger(__name__)

class BackfillDiscrepancyError(Exception):
    """Raised when data inconsistency is discovered during backfill."""
    def __init__(self, message: str, discrepancies: List[str] = None):
        super().__init__(message)
        self.discrepancies = discrepancies or []

class PaymentBackfillService:
    def __init__(self, db: Session):
        self.db = db

    def validate_and_backfill(self, dry_run: bool = False, force: bool = False) -> Dict[str, Any]:
        """
        Validate existing historical inflow transactions and paid invoices,
        and atomically backfill records into the payments table.
        """
        discrepancies: List[str] = []

        # 1. Fetch all PAID invoices
        paid_invoices = self.db.query(Invoice).filter(Invoice.status == "PAID").all()
        paid_invoice_map = {inv.invoice_id: inv for inv in paid_invoices}

        # 2. Fetch all INFLOW cash transactions with linked invoices
        inflow_txns = (
            self.db.query(CashTransaction)
            .filter(
                CashTransaction.transaction_type == "INFLOW",
                CashTransaction.linked_invoice_id.isnot(None),
                CashTransaction.linked_invoice_id != "",
            )
            .order_by(CashTransaction.transaction_date.asc(), CashTransaction.transaction_id.asc())
            .all()
        )

        # 3. Check for 1:1 mapping and anomalies
        txn_by_invoice = {}
        for txn in inflow_txns:
            inv_id = txn.linked_invoice_id
            if inv_id in txn_by_invoice:
                discrepancies.append(
                    f"Duplicate inflow transactions for invoice {inv_id}: "
                    f"{txn_by_invoice[inv_id].transaction_id} and {txn.transaction_id}"
                )
            txn_by_invoice[inv_id] = txn

        # Check for unlinked paid invoices
        for inv_id in paid_invoice_map:
            if inv_id not in txn_by_invoice:
                discrepancies.append(f"Paid invoice {inv_id} has no corresponding INFLOW cash transaction")

        # Validate each pair
        payments_to_create: List[Payment] = []
        for txn in inflow_txns:
            inv = paid_invoice_map.get(txn.linked_invoice_id)
            if not inv:
                # Inflow links to a non-PAID or non-existent invoice
                other_inv = self.db.query(Invoice).filter(Invoice.invoice_id == txn.linked_invoice_id).first()
                if other_inv:
                    discrepancies.append(
                        f"Inflow transaction {txn.transaction_id} links to invoice {txn.linked_invoice_id} "
                        f"with unexpected status '{other_inv.status}'"
                    )
                else:
                    discrepancies.append(
                        f"Inflow transaction {txn.transaction_id} links to non-existent invoice {txn.linked_invoice_id}"
                    )
                continue

            # Company match
            if txn.company_id != inv.company_id:
                discrepancies.append(
                    f"Company mismatch for txn {txn.transaction_id} ({txn.company_id}) vs invoice {inv.invoice_id} ({inv.company_id})"
                )

            # Currency match
            if txn.currency != inv.currency:
                discrepancies.append(
                    f"Currency mismatch for txn {txn.transaction_id} ({txn.currency}) vs invoice {inv.invoice_id} ({inv.currency})"
                )

            # Amount match
            if abs(txn.amount - inv.invoice_amount) > Decimal("0.001"):
                discrepancies.append(
                    f"Amount mismatch for txn {txn.transaction_id} ({txn.amount}) vs invoice {inv.invoice_id} ({inv.invoice_amount})"
                )

            # Payment date vs invoice date
            if txn.transaction_date < inv.invoice_date:
                discrepancies.append(
                    f"Payment date {txn.transaction_date} precedes invoice date {inv.invoice_date} for {inv.invoice_id}"
                )

            # Build candidate payment object
            det_payment_id = f"PAY-BF-{txn.transaction_id}"
            det_idempotency_key = f"BACKFILL-{txn.transaction_id}"

            p = Payment(
                payment_id=det_payment_id,
                company_id=inv.company_id,
                invoice_id=inv.invoice_id,
                payment_date=txn.transaction_date,
                amount=txn.amount,
                currency=txn.currency,
                payment_method="BANK_TRANSFER",
                reference_number=txn.transaction_id,
                notes=f"Historical payment backfilled from transaction {txn.transaction_id}",
                cash_transaction_id=txn.transaction_id,
                idempotency_key=det_idempotency_key,
                source="SEED_BACKFILL",
                created_at=datetime.now(timezone.utc),
            )
            payments_to_create.append(p)

        if discrepancies:
            raise BackfillDiscrepancyError(
                f"Backfill validation encountered {len(discrepancies)} discrepancy/discrepancies.",
                discrepancies=discrepancies,
            )

        # 4. Check existing payments
        existing_backfills = (
            self.db.query(func.count(Payment.payment_id))
            .filter(Payment.source == "SEED_BACKFILL")
            .scalar()
            or 0
        )

        if existing_backfills == len(payments_to_create) and not force:
            return {
                "status": "skipped_already_backfilled",
                "message": f"All {existing_backfills} historical payments are already backfilled. Use force=True to re-run.",
                "total_paid_invoices": len(paid_invoices),
                "total_inflows": len(inflow_txns),
                "payments_backfilled": existing_backfills,
                "dry_run": dry_run,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # If force=True, only remove existing SEED_BACKFILL records
        if force and not dry_run:
            logger.info("Force flag enabled. Re-creating SEED_BACKFILL payment records.")
            self.db.query(Payment).filter(Payment.source == "SEED_BACKFILL").delete()
            self.db.flush()

        try:
            if not dry_run:
                self.db.add_all(payments_to_create)
                self.db.commit()
                status_str = "success"
            else:
                self.db.rollback()
                status_str = "dry_run_success"

            return {
                "status": status_str,
                "total_paid_invoices": len(paid_invoices),
                "total_inflows": len(inflow_txns),
                "payments_backfilled": len(payments_to_create),
                "dry_run": dry_run,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self.db.rollback()
            logger.error("Payment backfill transaction rolled back: %s", str(e), exc_info=True)
            raise
