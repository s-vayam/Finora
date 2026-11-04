import argparse
import sys
from decimal import Decimal
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, func, distinct, text
from app.database import SessionLocal
from app.models.fx_rate_observation import FxRateObservation


def validate_fx_history():
    session = SessionLocal()
    print("=" * 60)
    print("FINORA FX HISTORICAL DATABASE VALIDATION")
    print("=" * 60)

    # 1. Total records
    total_count = session.scalar(select(func.count(FxRateObservation.id)))
    print(f"\n[CHECK 1] Total FX Rate Observations: {total_count:,}")
    assert total_count > 0, "No FX rate observations found in database!"

    # 2. Rate Types distribution
    type_counts = session.execute(
        select(FxRateObservation.rate_type, func.count(FxRateObservation.id)).group_by(FxRateObservation.rate_type)
    ).all()
    print("\n[CHECK 2] Rate Type Distribution:")
    for r_type, count in type_counts:
        print(f"  {r_type}: {count:,}")
        assert r_type in ["REFERENCE_DAILY", "INDICATIVE_LIVE"], f"Unexpected rate_type: {r_type}"

    # 3. Duplicate observation keys
    dup_query = session.execute(
        select(FxRateObservation.observation_key, func.count(FxRateObservation.id))
        .group_by(FxRateObservation.observation_key)
        .having(func.count(FxRateObservation.id) > 1)
    ).all()
    print(f"\n[CHECK 3] Duplicate Observation Keys: {len(dup_query)}")
    assert len(dup_query) == 0, f"Found {len(dup_query)} duplicate observation keys!"

    # 4. Currency pairs breakdown & sanity checks
    pairs = session.execute(
        select(
            FxRateObservation.base_currency,
            FxRateObservation.quote_currency,
            func.count(FxRateObservation.id),
            func.min(FxRateObservation.observation_date),
            func.max(FxRateObservation.observation_date),
            func.min(FxRateObservation.rate_value),
            func.max(FxRateObservation.rate_value)
        ).group_by(FxRateObservation.base_currency, FxRateObservation.quote_currency)
    ).all()

    print("\n[CHECK 4] Currency Pair Coverage & Rates:")
    for base_curr, quote_curr, count, min_d, max_d, min_r, max_r in pairs:
        print(f"  {base_curr}/{quote_curr}: {count:,} observations")
        print(f"    Date range : {min_d} to {max_d}")
        print(f"    Rate range : {min_r:.4f} to {max_r:.4f} INR")
        assert count > 1000, f"Insufficient observations for {base_curr}/{quote_curr}: {count}"
        assert min_r > 0, f"Negative or zero rate found for {base_curr}/{quote_curr}"

    # 5. Normalization audit: rate_value == original_rate_value / original_unit
    all_obs = session.scalars(select(FxRateObservation)).all()
    mismatches = 0
    for obs in all_obs:
        expected = Decimal(str(obs.original_rate_value)) / Decimal(obs.original_unit)
        actual = Decimal(str(obs.rate_value))
        if abs(expected - actual) > Decimal("0.000001"):
            mismatches += 1
            if mismatches <= 3:
                print(f"  Mismatch in {obs.id}: expected {expected}, got {actual}")

    print(f"\n[CHECK 5] Unit Normalization Consistency Audit: {mismatches} mismatches")
    assert mismatches == 0, f"Found {mismatches} unit normalization mismatches!"

    # 6. Daily jumps analysis (> 15% day-over-day movement check)
    large_jumps = []
    for base_curr in ["USD", "EUR", "GBP"]:
        obs_series = session.scalars(
            select(FxRateObservation)
            .where(FxRateObservation.base_currency == base_curr)
            .order_by(FxRateObservation.observation_date.asc())
        ).all()
        
        for i in range(1, len(obs_series)):
            prev_rate = float(obs_series[i-1].rate_value)
            curr_rate = float(obs_series[i].rate_value)
            pct_change = abs(curr_rate - prev_rate) / prev_rate * 100
            if pct_change > 10.0:
                large_jumps.append((base_curr, obs_series[i].observation_date, pct_change, prev_rate, curr_rate))

    print(f"\n[CHECK 6] Outlier Daily Shifts (> 10% daily jump): {len(large_jumps)} detected")
    for curr, dt, pct, p_r, c_r in large_jumps:
        print(f"  {curr} on {dt}: {pct:.2f}% jump ({p_r:.4f} -> {c_r:.4f})")

    # 7. Pre-existing database tables check
    tables = [
        ("companies", 1),
        ("customers", 60),
        ("invoices", 899),
        ("payments", 873),
        ("expenses", 872),
        ("cash_transactions", 1722),
        ("monthly_cashflow", 36),
    ]
    print("\n[CHECK 7] Pre-existing Table Row Counts Preservation:")
    for tbl, expected_count in tables:
        actual_cnt = session.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
        print(f"  {tbl}: {actual_cnt} (expected >= {expected_count})")
        assert actual_cnt >= expected_count, f"Table {tbl} row count reduced! Got {actual_cnt}, expected >= {expected_count}"

    session.close()
    print("\n" + "=" * 60)
    print("ALL FX HISTORICAL VALIDATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    validate_fx_history()
