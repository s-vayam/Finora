from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class FxRateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    base_currency: str = Field(..., description="Foreign currency e.g. USD, EUR, GBP")
    quote_currency: str = Field(default="INR", description="Base currency (always INR)")
    currency_pair: str = Field(..., description="e.g. USD/INR")
    rate_value: Decimal = Field(..., description="Exchange rate in INR per 1 unit of foreign currency")
    rate_type: str = Field(..., description="REFERENCE_DAILY or INDICATIVE_LIVE")
    provider: str = Field(..., description="e.g. RBI_FBIL_ARCHIVE, EXCHANGERATE_DEV")
    observation_date: date
    provider_effective_at: Optional[datetime] = None
    fetched_at: datetime
    market_session: Optional[str] = None
    is_stale: bool = False
    is_derived: bool = False
    freshness_status: str = Field(default="FRESH_INDICATIVE", description="FRESH_INDICATIVE, DELAYED_INDICATIVE, STALE, MARKET_CLOSED")
    source: Optional[str] = None
    source_notice: Optional[str] = None


class FxQuotaStatus(BaseModel):
    provider: str = "EXCHANGERATE_DEV"
    requests_today: int
    requests_this_month: int
    monthly_budget: int
    remaining_budget: int
    is_budget_exceeded: bool
    last_fetch_at: Optional[datetime] = None
    last_fetch_status: Optional[str] = None


class FxFetchResult(BaseModel):
    success: bool
    status: str
    rates_fetched: Dict[str, Decimal] = Field(default_factory=dict)
    message: str
    quota_status: Optional[FxQuotaStatus] = None
    fetch_id: Optional[str] = None

