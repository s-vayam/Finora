import datetime
from decimal import Decimal
import pytest
from sqlalchemy import select, func, inspect
from app.database import SessionLocal, engine
from app.models.fx_rate_observation import FxRateObservation
from app.models.fx_fetch_run import FxFetchRun
from app.models.company import Company
from app.models.invoice import Invoice
from app.models.payment import Payment


def test_migration_004_tables_and_columns():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "fx_rate_observations" in tables
    assert "fx_fetch_runs" in tables

    # Inspect columns of fx_rate_observations
    obs_cols = {c["name"]: c for c in inspector.get_columns("fx_rate_observations")}
    required_cols = [
        "id", "base_currency", "quote_currency", "rate_type", "rate_value",
        "original_rate_value", "original_unit", "provider", "provider_effective_at",
        "observation_date", "fetched_at", "market_session", "source", "is_stale",
        "is_derived", "data_delay_seconds", "source_notice", "observation_key", "created_at"
    ]
    for col in required_cols:
        assert col in obs_cols, f"Column {col} missing from fx_rate_observations"

    # Inspect columns of fx_fetch_runs
    fetch_cols = {c["name"]: c for c in inspector.get_columns("fx_fetch_runs")}
    required_fetch_cols = [
        "fetch_id", "provider", "requested_at", "completed_at", "status",
        "request_count", "error_code", "error_message", "response_metadata", "created_at"
    ]
    for col in required_fetch_cols:
        assert col in fetch_cols, f"Column {col} missing from fx_fetch_runs"


def test_fx_rate_observations_coverage_and_provenance():
    session = SessionLocal()
    try:
        # Check USD, EUR, GBP counts
        for curr in ["USD", "EUR", "GBP"]:
            count = session.scalar(
                select(func.count(FxRateObservation.id)).where(
                    FxRateObservation.base_currency == curr,
                    FxRateObservation.quote_currency == "INR",
                    FxRateObservation.rate_type == "REFERENCE_DAILY"
                )
            )
            assert count >= 6000, f"Expected >= 6000 observations for {curr}/INR, found {count}"

            # Check min and max date
            min_date = session.scalar(
                select(func.min(FxRateObservation.observation_date)).where(
                    FxRateObservation.base_currency == curr
                )
            )
            max_date = session.scalar(
                select(func.max(FxRateObservation.observation_date)).where(
                    FxRateObservation.base_currency == curr
                )
            )
            assert min_date <= datetime.date(2000, 1, 1), f"Earliest date too recent for {curr}: {min_date}"
            assert max_date >= datetime.date(2026, 1, 1), f"Latest date too old for {curr}: {max_date}"
    finally:
        session.close()


def test_fx_rate_normalization_and_unit_audit():
    session = SessionLocal()
    try:
        # Fetch a sample of observations
        sample = session.scalars(select(FxRateObservation).limit(100)).all()
        assert len(sample) > 0
        for obs in sample:
            expected = Decimal(str(obs.original_rate_value)) / Decimal(obs.original_unit)
            actual = Decimal(str(obs.rate_value))
            assert abs(expected - actual) < Decimal("0.000001"), f"Normalization error in observation {obs.id}"
            assert obs.quote_currency == "INR"
            assert obs.rate_value > 0
    finally:
        session.close()


def test_fx_rate_observation_idempotency_and_uniqueness():
    session = SessionLocal()
    try:
        # Duplicate keys query
        dups = session.execute(
            select(FxRateObservation.observation_key, func.count(FxRateObservation.id))
            .group_by(FxRateObservation.observation_key)
            .having(func.count(FxRateObservation.id) > 1)
        ).all()
        assert len(dups) == 0, f"Duplicate observation keys found: {dups}"
    finally:
        session.close()


def test_preexisting_financial_records_unaffected():
    session = SessionLocal()
    try:
        company_count = session.scalar(select(func.count(Company.company_id)))
        invoice_count = session.scalar(select(func.count(Invoice.invoice_id)))
        payment_count = session.scalar(select(func.count(Payment.payment_id)))
        total_payment_sum = session.scalar(select(func.sum(Payment.amount)))

        assert company_count == 1
        assert invoice_count == 899
        assert payment_count >= 873
        assert total_payment_sum >= Decimal("122169067.90")
    finally:
        session.close()

