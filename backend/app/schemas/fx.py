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


class FxForecastRequest(BaseModel):
    company_id: str = Field(default="FINORA_DEMO", description="Company ID")
    currency_pair: str = Field(default="USD/INR", description="Currency pair e.g. USD/INR, EUR/INR, GBP/INR")
    as_of_date: Optional[date] = Field(default=None, description="Prediction origin date (default: latest reference date)")
    target_date: Optional[date] = Field(default=None, description="Calendar target date within 30 trading sessions")
    horizon_sessions: Optional[int] = Field(default=None, description="Trading session horizon (1 to 30)")


class FxForecastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    forecast_id: str
    company_id: str
    currency_pair: str
    anchor_rate: Decimal
    anchor_date: date
    target_date: date
    horizon_sessions: int
    predicted_rate: Decimal
    percentage_movement: Decimal
    predicted_direction: str  # UP, DOWN, NEUTRAL
    direction_probabilities: Dict[str, float]
    prediction_range_80: Optional[List[Decimal]] = None
    prediction_range_95: Optional[List[Decimal]] = None
    latest_indicative_rate: Optional[Decimal] = None
    latest_indicative_timestamp: Optional[datetime] = None
    model_version: str
    skill_status: str  # TRAINED_AND_VALIDATED, NO_SKILL_VS_BASELINE
    is_validated: bool = True
    freshness_warning: Optional[str] = None
    attribution: str = Field(default="Forecast generated from RBI/FBIL Reference Rates archive.")


class FxExposureItem(BaseModel):
    currency: str
    receivable_amount: Decimal = Field(default=Decimal("0.00"), description="Foreign currency receivable from open invoices")
    payable_amount: Decimal = Field(default=Decimal("0.00"), description="Foreign currency payable from open expenses")
    net_exposure: Decimal = Field(default=Decimal("0.00"), description="Net foreign currency exposure")
    benchmark_rate: Decimal = Field(..., description="Reference rate in INR used as benchmark")
    predicted_rate: Optional[Decimal] = None
    estimated_receivable_impact: Decimal = Field(default=Decimal("0.00"), description="INR impact on receivables")
    estimated_payable_impact: Decimal = Field(default=Decimal("0.00"), description="INR impact on payables")
    net_estimated_impact: Decimal = Field(default=Decimal("0.00"), description="Net estimated impact in INR")
    status: str = Field(default="ESTIMATED_UNREALIZED")


class FxExposureResponse(BaseModel):
    company_id: str
    as_of_date: date
    base_currency: str = "INR"
    supported_exposures: List[FxExposureItem]
    unsupported_exposures: List[FxExposureItem] = Field(default_factory=list)
    total_net_estimated_impact: Decimal
    disclaimer: str = Field(
        default="Estimated unrealized model-based exposure impact before spreads, hedging costs, tax, and transaction fees. Not an execution recommendation."
    )


class FxScenarioRequest(BaseModel):
    company_id: str = Field(default="FINORA_DEMO")
    currency_pair: str = Field(default="USD/INR")
    benchmark_rate: Optional[Decimal] = None
    scenario_type: str = Field(default="PERCENTAGE_MOVEMENT", description="PERCENTAGE_MOVEMENT or TARGET_RATE")
    percentage_change: Optional[Decimal] = Field(default=Decimal("5.0"), description="Percentage shift in rate e.g. 5.0 for +5%")
    scenario_rate: Optional[Decimal] = None


class FxScenarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scenario_id: str
    company_id: str
    currency_pair: str
    benchmark_rate: Decimal
    scenario_rate: Decimal
    percentage_change: Decimal
    receivable_exposure: Decimal
    payable_exposure: Decimal
    estimated_receivable_impact: Decimal
    estimated_payable_impact: Decimal
    net_estimated_impact: Decimal
    source: str = "SIMULATED"
    comparison_with_ml: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    disclaimer: str = Field(
        default="Simulated what-if scenario. Not financial advice or an execution guarantee."
    )
