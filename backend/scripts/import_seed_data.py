#!/usr/bin/env python3
"""
Seed Data Import Script for Finora.
Imports operational CSVs into the SQLite database with full transaction support.
"""
import argparse
import sys
from pathlib import Path

# Add backend directory to sys.path so app modules can be imported
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import engine, init_db, SessionLocal
from app.services.data_import_service import DataImportService, DataImportError

def main():
    parser = argparse.ArgumentParser(description="Import Finora synthetic financial seed data into database.")
    parser.add_argument(
        "--data-dir",
        type=str,
        default=str(BACKEND_DIR / "data" / "raw" / "finora_synthetic_data"),
        help="Path to folder containing raw synthetic CSV files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate all files and records without committing to the database",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite/re-import of existing seed data",
    )

    args = parser.parse_args()
    data_dir = Path(args.data_dir)

    print("=" * 60)
    print("FINORA SEED DATA IMPORTER")
    print("=" * 60)
    print(f"Data Directory : {data_dir.resolve()}")
    print(f"Dry Run Mode   : {args.dry_run}")
    print(f"Force Re-import: {args.force}")
    print("-" * 60)

    # Initialize tables if needed
    init_db()

    db = SessionLocal()
    try:
        service = DataImportService(data_dir=data_dir, db=db)
        summary = service.import_all(dry_run=args.dry_run, force=args.force)

        print(f"Status: {summary['status'].upper()}")
        if summary.get("message"):
            print(f"Message: {summary['message']}")
        
        print("\nRecord Counts:")
        for table, count in summary.get("imported_counts", {}).items():
            print(f"  - {table:<20}: {count:>6}")

        print("=" * 60)
        if summary["status"] in ("success", "dry_run_success", "skipped_already_seeded"):
            print("Import completed successfully.")
            sys.exit(0)
        else:
            print("Import completed with warnings or non-success status.")
            sys.exit(1)

    except FileNotFoundError as e:
        print(f"\n[ERROR] Missing dataset file: {e}")
        sys.exit(1)
    except DataImportError as e:
        print(f"\n[ERROR] Data validation error: {e}")
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

