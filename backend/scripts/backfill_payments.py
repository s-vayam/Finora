#!/usr/bin/env python3
"""
Historical Payment Backfill CLI for Finora.
Backfills payments table from existing cash_transactions linked to invoices.
"""
import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal
from app.services.payment_backfill_service import PaymentBackfillService, BackfillDiscrepancyError

def main():
    parser = argparse.ArgumentParser(description="Backfill historical payments from existing cash transactions.")
    parser.add_argument("--dry-run", action="store_true", help="Validate all mappings without committing payments")
    parser.add_argument("--force", action="store_true", help="Force re-backfill of SEED_BACKFILL payments")

    args = parser.parse_args()

    print("=" * 65)
    print("FINORA HISTORICAL PAYMENT BACKFILL")
    print("=" * 65)
    print(f"Dry Run Mode: {args.dry_run}")
    print(f"Force Mode  : {args.force}")
    print("-" * 65)

    db = SessionLocal()
    try:
        service = PaymentBackfillService(db=db)
        summary = service.validate_and_backfill(dry_run=args.dry_run, force=args.force)

        print(f"Status              : {summary['status'].upper()}")
        print(f"Total Paid Invoices : {summary['total_paid_invoices']}")
        print(f"Total Inflow Txns   : {summary['total_inflows']}")
        print(f"Payments Backfilled : {summary['payments_backfilled']}")
        if summary.get("message"):
            print(f"Notice              : {summary['message']}")
        print("=" * 65)

        if summary["status"] in ("success", "dry_run_success", "skipped_already_backfilled"):
            print("Backfill operation completed successfully.")
            sys.exit(0)
        else:
            print("Backfill completed with unexpected status.")
            sys.exit(1)

    except BackfillDiscrepancyError as e:
        print(f"\n[DISCREPANCY ERROR] {e}")
        for disc in e.discrepancies[:10]:
            print(f"  - {disc}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[UNEXPECTED ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
