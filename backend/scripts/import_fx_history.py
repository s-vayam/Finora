import argparse
import csv
import datetime
import hashlib
import sys
import uuid
from decimal import Decimal
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.database import SessionLocal
from app.models.fx_rate_observation import FxRateObservation


SUPPORTED_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "AED", "IDR"]
PRIMARY_PAIRS = ["USD", "EUR", "GBP"]
SOURCE_URL = "https://github.com/the-solipsist/rbi-forex-reference-rates"
SOURCE_NOTICE = "Historical Reserve Bank of India (RBI) / Financial Benchmarks India Pvt Ltd (FBIL) Reference Rates archive compiled by Pranesh Prakash (CC0 1.0 Public Domain)."


def compute_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()


def import_fx_history(
    csv_file: Path,
    dry_run: bool = False,
    currencies: list[str] = None,
    limit: int = None
):
    if not csv_file.exists():
        print(f"Error: File not found: {csv_file}")
        sys.exit(1)

    file_sha256 = compute_sha256(csv_file)
    file_size = csv_file.stat().st_size
    print(f"Dataset: {csv_file} ({file_size:,} bytes)")
    print(f"SHA-256 Provenance: {file_sha256}")
    print(f"Dry Run Mode: {dry_run}")
    
    target_currencies = set(c.upper() for c in (currencies or PRIMARY_PAIRS))
    print(f"Target Currencies: {sorted(target_currencies)}")

    session = SessionLocal()
    
    # Query existing observation keys to ensure idempotent re-runs
    existing_keys_query = select(FxRateObservation.observation_key).where(
        FxRateObservation.rate_type == "REFERENCE_DAILY"
    )
    existing_keys = set(session.scalars(existing_keys_query).all())
    print(f"Pre-existing REFERENCE_DAILY records in database: {len(existing_keys):,}")

    stats = {
        "total_rows_read": 0,
        "processed_rows": 0,
        "inserted": 0,
        "skipped_existing": 0,
        "skipped_currency": 0,
        "rejected_invalid": 0,
        "by_currency": {c: {"inserted": 0, "existing": 0, "min_date": None, "max_date": None} for c in target_currencies}
    }
    rejected_rows = []
    to_insert = []
    now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_idx, row in enumerate(reader, start=2):
            stats["total_rows_read"] += 1
            if limit and stats["processed_rows"] >= limit:
                break

            curr = (row.get("currency") or "").strip().upper()
            if curr not in target_currencies:
                stats["skipped_currency"] += 1
                continue

            stats["processed_rows"] += 1
            date_str = (row.get("date") or "").strip()
            raw_rate = (row.get("rate") or "").strip()
            raw_unit = (row.get("unit") or "1").strip()

            # Validation
            try:
                obs_date = datetime.date.fromisoformat(date_str)
            except Exception as e:
                stats["rejected_invalid"] += 1
                rejected_rows.append((row_idx, row, f"Invalid date: {e}"))
                continue

            try:
                unit_int = int(raw_unit)
                if unit_int <= 0:
                    raise ValueError("Unit must be positive")
            except Exception as e:
                stats["rejected_invalid"] += 1
                rejected_rows.append((row_idx, row, f"Invalid unit: {e}"))
                continue

            try:
                rate_dec = Decimal(raw_rate)
                if rate_dec <= 0:
                    raise ValueError("Rate must be positive")
                # Normalize to rate per 1 unit of foreign currency
                normalized_rate = rate_dec / Decimal(unit_int)
            except Exception as e:
                stats["rejected_invalid"] += 1
                rejected_rows.append((row_idx, row, f"Invalid rate: {e}"))
                continue

            obs_key = f"REFERENCE_DAILY_{curr}_INR_{obs_date.isoformat()}"
            if obs_key in existing_keys:
                stats["skipped_existing"] += 1
                stats["by_currency"][curr]["existing"] += 1
                continue

            # Add to pending insert
            obs_record = FxRateObservation(
                id=str(uuid.uuid4()),
                base_currency=curr,
                quote_currency="INR",
                rate_type="REFERENCE_DAILY",
                rate_value=normalized_rate,
                original_rate_value=rate_dec,
                original_unit=unit_int,
                provider="RBI_FBIL_ARCHIVE",
                provider_effective_at=datetime.datetime.combine(obs_date, datetime.time(13, 0)),  # Typical RBI 13:00 reference time
                observation_date=obs_date,
                fetched_at=now_utc,
                market_session="DAILY_REFERENCE",
                source=SOURCE_URL,
                is_stale=False,
                is_derived=False,
                data_delay_seconds=0,
                source_notice=SOURCE_NOTICE,
                observation_key=obs_key,
                created_at=now_utc
            )
            to_insert.append(obs_record)
            existing_keys.add(obs_key)  # Prevent duplicate within file

            stats["inserted"] += 1
            curr_stat = stats["by_currency"][curr]
            curr_stat["inserted"] += 1
            if curr_stat["min_date"] is None or obs_date < curr_stat["min_date"]:
                curr_stat["min_date"] = obs_date
            if curr_stat["max_date"] is None or obs_date > curr_stat["max_date"]:
                curr_stat["max_date"] = obs_date

    print("\n--- IMPORT SUMMARY ---")
    print(f"Total rows read: {stats['total_rows_read']:,}")
    print(f"Processed target rows: {stats['processed_rows']:,}")
    print(f"Skipped other currencies: {stats['skipped_currency']:,}")
    print(f"Skipped pre-existing: {stats['skipped_existing']:,}")
    print(f"Rejected invalid rows: {stats['rejected_invalid']:,}")
    print(f"New observations to insert: {stats['inserted']:,}")

    print("\nBreakdown by currency:")
    for c, c_info in sorted(stats["by_currency"].items()):
        min_d = c_info["min_date"] or "N/A"
        max_d = c_info["max_date"] or "N/A"
        print(f"  {c}/INR: {c_info['inserted']:,} new, {c_info['existing']:,} existing. Range: {min_d} to {max_d}")

    if rejected_rows:
        print("\nFirst 5 rejected rows:")
        for idx, r, err in rejected_rows[:5]:
            print(f"  Row {idx}: {r} -> {err}")

    if not dry_run and to_insert:
        print(f"\nPersisting {len(to_insert):,} records to database...")
        session.bulk_save_objects(to_insert)
        session.commit()
        print("Commit successful!")
    elif dry_run:
        print("\nDry-run complete. Database unchanged.")

    session.close()
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import historical RBI/FBIL forex reference rates")
    parser.add_argument("--file", type=Path, default=Path("data/raw/rbi_forex/rbi_forex_reference_rates_long.csv"), help="Path to long CSV")
    parser.add_argument("--dry-run", action="store_true", help="Perform validation without database write")
    parser.add_argument("--currencies", type=str, default="USD,EUR,GBP", help="Comma-separated currencies to import")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of rows to process")
    
    args = parser.parse_args()
    currencies = [c.strip() for c in args.currencies.split(",") if c.strip()]
    import_fx_history(args.file, dry_run=args.dry_run, currencies=currencies, limit=args.limit)

