import datetime
import logging
import time
import uuid
from decimal import Decimal
from typing import Dict, Any, Optional, List
import httpx
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.config import settings
from app.models.fx_rate_observation import FxRateObservation
from app.models.fx_fetch_run import FxFetchRun
from app.schemas.fx import FxQuotaStatus, FxRateResponse, FxFetchResult

logger = logging.getLogger("finora.fx_provider")

PROVIDER_NAME = "EXCHANGERATE_DEV"
DEFAULT_PAIRS = ["USD/INR", "EUR/INR", "GBP/INR"]
ATTRIBUTION_SOURCE = "https://exchangerate.dev"
ATTRIBUTION_NOTICE = "Indicative rates from exchangerate.dev (not for settlement)."


class FxProviderService:
    def __init__(self, api_base: Optional[str] = None, api_key: Optional[str] = None):
        self.api_base = api_base or settings.EXCHANGERATE_API_BASE
        self.api_key = api_key or settings.EXCHANGERATE_API_KEY
        self.timeout = settings.FX_REQUEST_TIMEOUT_SECONDS
        self.max_retries = settings.FX_MAX_RETRIES

    def get_quota_status(self, db: Session) -> FxQuotaStatus:
        now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        start_of_day = datetime.datetime.combine(now_utc.date(), datetime.time.min)
        start_of_month = datetime.datetime(now_utc.year, now_utc.month, 1)

        today_count = db.scalar(
            select(func.count(FxFetchRun.fetch_id)).where(
                and_(
                    FxFetchRun.provider == PROVIDER_NAME,
                    FxFetchRun.requested_at >= start_of_day
                )
            )
        ) or 0

        month_count = db.scalar(
            select(func.count(FxFetchRun.fetch_id)).where(
                and_(
                    FxFetchRun.provider == PROVIDER_NAME,
                    FxFetchRun.requested_at >= start_of_month
                )
            )
        ) or 0

        last_run = db.scalars(
            select(FxFetchRun)
            .where(FxFetchRun.provider == PROVIDER_NAME)
            .order_by(FxFetchRun.requested_at.desc())
            .limit(1)
        ).first()

        budget = settings.FX_MONTHLY_REQUEST_BUDGET
        remaining = max(0, budget - month_count)

        return FxQuotaStatus(
            provider=PROVIDER_NAME,
            requests_today=today_count,
            requests_this_month=month_count,
            monthly_budget=budget,
            remaining_budget=remaining,
            is_budget_exceeded=month_count >= budget,
            last_fetch_at=last_run.completed_at if last_run else None,
            last_fetch_status=last_run.status if last_run else None
        )

    def fetch_latest_rates(self, db: Session, force: bool = False, mock_client: Optional[httpx.Client] = None) -> FxFetchResult:
        quota = self.get_quota_status(db)
        if quota.is_budget_exceeded and not force:
            msg = f"Monthly request budget ({quota.monthly_budget}) exhausted. Polling stopped to avoid charges."
            logger.warning(msg)
            return FxFetchResult(
                success=False,
                status="QUOTA_EXHAUSTED",
                rates_fetched={},
                message=msg,
                quota_status=quota
            )

        fetch_id = str(uuid.uuid4())
        requested_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        fetch_run = FxFetchRun(
            fetch_id=fetch_id,
            provider=PROVIDER_NAME,
            requested_at=requested_at,
            status="RUNNING",
            request_count=1
        )
        db.add(fetch_run)
        db.commit()

        url = f"{self.api_base.rstrip('/')}/latest"
        headers = {"User-Agent": "Finora-FX-Engine/1.0"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        attempt = 0
        last_exception = None
        data = None

        while attempt < self.max_retries:
            attempt += 1
            try:
                if mock_client:
                    response = mock_client.get(url, headers=headers)
                else:
                    with httpx.Client(timeout=self.timeout) as client:
                        response = client.get(url, headers=headers)

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    fetch_run.status = "FAILED"
                    fetch_run.error_code = "HTTP_429_RATE_LIMITED"
                    fetch_run.error_message = f"Rate limited by provider. Retry-After: {retry_after}s"
                    fetch_run.completed_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
                    db.commit()
                    return FxFetchResult(
                        success=False,
                        status="RATE_LIMITED",
                        message=fetch_run.error_message,
                        quota_status=self.get_quota_status(db),
                        fetch_id=fetch_id
                    )

                response.raise_for_status()
                data = response.json()
                if data.get("result") != "success":
                    raise ValueError(f"Provider error: {data.get('message', 'Unknown failure')}")
                break
            except Exception as e:
                last_exception = e
                logger.warning(f"FX fetch attempt {attempt} failed: {e}")
                if attempt < self.max_retries:
                    time.sleep(1.0 * (2 ** (attempt - 1)))

        completed_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        if not data:
            fetch_run.status = "FAILED"
            fetch_run.error_code = "NETWORK_OR_PARSE_ERROR"
            fetch_run.error_message = str(last_exception)
            fetch_run.completed_at = completed_at
            db.commit()
            return FxFetchResult(
                success=False,
                status="FAILED",
                message=f"Failed to fetch live FX rates after {attempt} attempts: {last_exception}",
                quota_status=self.get_quota_status(db),
                fetch_id=fetch_id
            )

        # Parse data
        rates_dict = data.get("rates", {})
        stale_dict = data.get("stale", {})
        effective_at_dict = data.get("effective_at", {})
        market_session = data.get("market_session", "open")
        data_updated_at_str = data.get("data_updated_at")

        inr_per_usd = Decimal(str(rates_dict.get("INR", 0)))
        eur_per_usd = Decimal(str(rates_dict.get("EUR", 0)))
        gbp_per_usd = Decimal(str(rates_dict.get("GBP", 0)))

        if inr_per_usd <= 0:
            fetch_run.status = "FAILED"
            fetch_run.error_code = "MISSING_INR_RATE"
            fetch_run.error_message = "Provider did not return a valid INR quote."
            fetch_run.completed_at = completed_at
            db.commit()
            return FxFetchResult(
                success=False,
                status="FAILED",
                message="Missing valid INR rate in provider response",
                quota_status=self.get_quota_status(db),
                fetch_id=fetch_id
            )

        # Build pair records
        # 1. USD/INR (direct)
        usd_inr_rate = inr_per_usd
        # 2. EUR/INR (cross: inr_per_usd / eur_per_usd)
        eur_inr_rate = (inr_per_usd / eur_per_usd) if eur_per_usd > 0 else Decimal(0)
        # 3. GBP/INR (cross: inr_per_usd / gbp_per_usd)
        gbp_inr_rate = (inr_per_usd / gbp_per_usd) if gbp_per_usd > 0 else Decimal(0)

        pairs_to_process = [
            ("USD", usd_inr_rate, False, stale_dict.get("INR", False), effective_at_dict.get("INR")),
            ("EUR", eur_inr_rate, True, stale_dict.get("EUR", False) or stale_dict.get("INR", False), effective_at_dict.get("EUR")),
            ("GBP", gbp_inr_rate, True, stale_dict.get("GBP", False) or stale_dict.get("INR", False), effective_at_dict.get("GBP")),
        ]

        stored_rates = {}
        for curr, rate_val, is_derived, is_stale, eff_str in pairs_to_process:
            if rate_val <= 0:
                continue

            eff_dt = None
            if eff_str:
                try:
                    eff_dt = datetime.datetime.fromisoformat(eff_str.replace("Z", "+00:00")).astimezone(datetime.timezone.utc).replace(tzinfo=None)
                except Exception:
                    pass
            if not eff_dt and data_updated_at_str:
                try:
                    eff_dt = datetime.datetime.fromisoformat(data_updated_at_str.replace("Z", "+00:00")).astimezone(datetime.timezone.utc).replace(tzinfo=None)
                except Exception:
                    pass
            if not eff_dt:
                eff_dt = requested_at

            delay_secs = max(0, int((completed_at - eff_dt).total_seconds()))
            obs_date = eff_dt.date()
            # Observation key based on hour bucket or exact timestamp to prevent duplicate collisions
            eff_key_str = eff_dt.strftime("%Y%m%d%H%M")
            obs_key = f"INDICATIVE_LIVE_{curr}_INR_{eff_key_str}"

            existing_obs = db.scalars(
                select(FxRateObservation).where(FxRateObservation.observation_key == obs_key)
            ).first()

            if existing_obs:
                existing_obs.rate_value = rate_val
                existing_obs.original_rate_value = rate_val
                existing_obs.fetched_at = completed_at
                existing_obs.is_stale = is_stale
                existing_obs.data_delay_seconds = delay_secs
                existing_obs.market_session = market_session
            else:
                new_obs = FxRateObservation(
                    id=str(uuid.uuid4()),
                    base_currency=curr,
                    quote_currency="INR",
                    rate_type="INDICATIVE_LIVE",
                    rate_value=rate_val,
                    original_rate_value=rate_val,
                    original_unit=1,
                    provider=PROVIDER_NAME,
                    provider_effective_at=eff_dt,
                    observation_date=obs_date,
                    fetched_at=completed_at,
                    market_session=market_session,
                    source=ATTRIBUTION_SOURCE,
                    is_stale=is_stale,
                    is_derived=is_derived,
                    data_delay_seconds=delay_secs,
                    source_notice=ATTRIBUTION_NOTICE,
                    observation_key=obs_key,
                    created_at=completed_at
                )
                db.add(new_obs)

            stored_rates[f"{curr}/INR"] = rate_val

        fetch_run.status = "SUCCESS"
        fetch_run.completed_at = completed_at
        fetch_run.response_metadata = {
            "rates_count": len(rates_dict),
            "market_session": market_session,
            "pairs_stored": list(stored_rates.keys())
        }
        db.commit()

        return FxFetchResult(
            success=True,
            status="SUCCESS",
            rates_fetched=stored_rates,
            message=f"Successfully fetched and stored live rates for: {list(stored_rates.keys())}",
            quota_status=self.get_quota_status(db),
            fetch_id=fetch_id
        )

    def get_current_rates(self, db: Session, pairs: Optional[List[str]] = None) -> List[FxRateResponse]:
        target_pairs = pairs or DEFAULT_PAIRS
        results = []
        now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

        for pair_str in target_pairs:
            parts = pair_str.split("/")
            base_curr = parts[0].strip().upper()
            quote_curr = parts[1].strip().upper() if len(parts) > 1 else "INR"

            # Prefer latest INDICATIVE_LIVE
            latest_live = db.scalars(
                select(FxRateObservation).where(
                    and_(
                        FxRateObservation.base_currency == base_curr,
                        FxRateObservation.quote_currency == quote_curr,
                        FxRateObservation.rate_type == "INDICATIVE_LIVE"
                    )
                ).order_by(FxRateObservation.fetched_at.desc()).limit(1)
            ).first()

            target_obs = latest_live
            if not target_obs:
                # Fallback to latest REFERENCE_DAILY
                target_obs = db.scalars(
                    select(FxRateObservation).where(
                        and_(
                            FxRateObservation.base_currency == base_curr,
                            FxRateObservation.quote_currency == quote_curr,
                            FxRateObservation.rate_type == "REFERENCE_DAILY"
                        )
                    ).order_by(FxRateObservation.observation_date.desc()).limit(1)
                ).first()

            if not target_obs:
                continue

            # Determine freshness
            delay_sec = int((now_utc - (target_obs.provider_effective_at or datetime.datetime.combine(target_obs.observation_date, datetime.time(12, 0)))).total_seconds())
            if target_obs.market_session == "closed":
                freshness = "MARKET_CLOSED"
            elif delay_sec > 86400 or target_obs.is_stale:
                freshness = "STALE"
            elif delay_sec > 3600:
                freshness = "DELAYED_INDICATIVE"
            else:
                freshness = "FRESH_INDICATIVE"

            results.append(
                FxRateResponse(
                    base_currency=target_obs.base_currency,
                    quote_currency=target_obs.quote_currency,
                    currency_pair=f"{target_obs.base_currency}/{target_obs.quote_currency}",
                    rate_value=target_obs.rate_value,
                    rate_type=target_obs.rate_type,
                    provider=target_obs.provider,
                    observation_date=target_obs.observation_date,
                    provider_effective_at=target_obs.provider_effective_at,
                    fetched_at=target_obs.fetched_at,
                    market_session=target_obs.market_session,
                    is_stale=target_obs.is_stale,
                    is_derived=target_obs.is_derived,
                    freshness_status=freshness,
                    source=target_obs.source,
                    source_notice=target_obs.source_notice
                )
            )

        return results

