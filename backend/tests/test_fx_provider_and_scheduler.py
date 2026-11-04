import datetime
from decimal import Decimal
import httpx
import pytest
from sqlalchemy import select, func
from app.database import SessionLocal
from app.models.fx_rate_observation import FxRateObservation
from app.models.fx_fetch_run import FxFetchRun
from app.services.fx_provider_service import FxProviderService, PROVIDER_NAME
from app.jobs.fx_scheduler import FxScheduler, LOCK_FILE


MOCK_SUCCESS_PAYLOAD = {
    "result": "success",
    "base": "USD",
    "source": "market_daily",
    "market_session": "open",
    "timestamp": "2026-11-04T18:48:20Z",
    "data_updated_at": "2026-11-04T18:00:00Z",
    "effective_at": {
        "INR": "2026-11-04T18:30:00Z",
        "EUR": "2026-11-04T18:30:00Z",
        "GBP": "2026-11-04T18:30:00Z"
    },
    "rates": {
        "USD": 1.0,
        "INR": 94.5000,
        "EUR": 0.9000,
        "GBP": 0.7500
    },
    "stale": {
        "INR": False,
        "EUR": False,
        "GBP": False
    },
    "notice": "Indicative rates from exchangerate.dev (not for settlement)."
}


def test_provider_response_parsing_and_cross_rates():
    session = SessionLocal()
    try:
        service = FxProviderService()

        # Mock transport
        def handler(request: httpx.Request):
            return httpx.Response(200, json=MOCK_SUCCESS_PAYLOAD)

        mock_client = httpx.Client(transport=httpx.MockTransport(handler))
        result = service.fetch_latest_rates(session, force=True, mock_client=mock_client)

        assert result.success is True
        assert result.status == "SUCCESS"
        assert "USD/INR" in result.rates_fetched
        assert "EUR/INR" in result.rates_fetched
        assert "GBP/INR" in result.rates_fetched

        # Math checks
        # USD/INR = 94.5
        assert result.rates_fetched["USD/INR"] == Decimal("94.5000")
        # EUR/INR = 94.5 / 0.9 = 105.0
        assert result.rates_fetched["EUR/INR"] == Decimal("105")
        # GBP/INR = 94.5 / 0.75 = 126.0
        assert result.rates_fetched["GBP/INR"] == Decimal("126")

        # Verify in database
        obs_usd = session.scalars(
            select(FxRateObservation).where(
                FxRateObservation.base_currency == "USD",
                FxRateObservation.rate_type == "INDICATIVE_LIVE"
            ).order_by(FxRateObservation.fetched_at.desc())
        ).first()
        assert obs_usd is not None
        assert obs_usd.is_derived is False
        assert obs_usd.rate_value == Decimal("94.5000")

        obs_eur = session.scalars(
            select(FxRateObservation).where(
                FxRateObservation.base_currency == "EUR",
                FxRateObservation.rate_type == "INDICATIVE_LIVE"
            ).order_by(FxRateObservation.fetched_at.desc())
        ).first()
        assert obs_eur is not None
        assert obs_eur.is_derived is True
        assert obs_eur.rate_value == Decimal("105")
    finally:
        session.close()


def test_rate_freshness_classification():
    session = SessionLocal()
    try:
        service = FxProviderService()
        now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

        # 1. Fresh observation
        obs_fresh = FxRateObservation(
            id="test-fresh",
            base_currency="USD",
            quote_currency="INR",
            rate_type="INDICATIVE_LIVE",
            rate_value=Decimal("94.50"),
            original_rate_value=Decimal("94.50"),
            original_unit=1,
            provider="EXCHANGERATE_DEV",
            provider_effective_at=now_utc - datetime.timedelta(minutes=15),
            observation_date=now_utc.date(),
            fetched_at=now_utc,
            market_session="open",
            is_stale=False,
            is_derived=False,
            observation_key="INDICATIVE_LIVE_USD_INR_TEST_FRESH"
        )
        session.add(obs_fresh)
        session.commit()

        current_rates = service.get_current_rates(session, ["USD/INR"])
        assert len(current_rates) == 1
        assert current_rates[0].freshness_status == "FRESH_INDICATIVE"

        # Cleanup
        session.delete(obs_fresh)
        session.commit()
    finally:
        session.close()


def test_http_429_rate_limiting_resilience():
    session = SessionLocal()
    try:
        service = FxProviderService()

        def handler(request: httpx.Request):
            return httpx.Response(429, headers={"Retry-After": "120"}, json={"error": "too many requests"})

        mock_client = httpx.Client(transport=httpx.MockTransport(handler))
        result = service.fetch_latest_rates(session, force=True, mock_client=mock_client)

        assert result.success is False
        assert result.status == "RATE_LIMITED"
        assert "Retry-After" in result.message

        # Verify run logged as FAILED
        last_run = session.scalars(
            select(FxFetchRun).order_by(FxFetchRun.requested_at.desc())
        ).first()
        assert last_run.status == "FAILED"
        assert last_run.error_code == "HTTP_429_RATE_LIMITED"
    finally:
        session.close()


def test_quota_monitoring_and_budget_exhaustion():
    session = SessionLocal()
    try:
        service = FxProviderService()
        quota = service.get_quota_status(session)
        assert quota.monthly_budget == 1000
        assert quota.requests_this_month >= 0
        assert quota.remaining_budget <= 1000

        # Simulate budget exhaustion by setting a temporarily tiny budget
        from app.config import settings
        original_budget = settings.FX_MONTHLY_REQUEST_BUDGET
        settings.FX_MONTHLY_REQUEST_BUDGET = 0

        try:
            exhausted_quota = service.get_quota_status(session)
            assert exhausted_quota.is_budget_exceeded is True

            # Attempt fetch without force
            result = service.fetch_latest_rates(session, force=False)
            assert result.success is False
            assert result.status == "QUOTA_EXHAUSTED"
        finally:
            settings.FX_MONTHLY_REQUEST_BUDGET = original_budget
    finally:
        session.close()


def test_scheduler_lock_and_concurrency_prevention():
    scheduler1 = FxScheduler(dry_run=True)
    scheduler2 = FxScheduler(dry_run=True)

    try:
        # Acquire lock on first instance
        assert scheduler1.acquire_lock() is True
        assert LOCK_FILE.exists()

        # Second instance should fail to acquire lock
        assert scheduler2.acquire_lock() is False
    finally:
        scheduler1.release_lock()
        assert not LOCK_FILE.exists()

