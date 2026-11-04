"""
Pydantic Schemas for Cash Flow and Liquidity Forecasting (Phase 4).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ForecastReliability(str, Enum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ForecastHorizon(int, Enum):
    DAYS_30 = 30
    DAYS_60 = 60
    DAYS_90 = 90


# ==============================================================================
# 1. Opening Cash Balance Snapshot Schemas
# ==============================================================================

class CashBalanceSnapshotCreate(BaseModel):
    company_id: str = Field(..., description="Target company ID")
    as_of_date: date = Field(..., description="Effective date for cash balance snapshot")
    balance_amount: Decimal = Field(..., gt=0, description="Actual opening balance in base currency")
    currency: str = Field("INR", min_length=3, max_length=10, description="Currency code")
    minimum_cash_threshold: Optional[Decimal] = Field(None, ge=0, description="Configured minimum cash reserve")
    source: str = Field("MANUAL", description="Source of snapshot: MANUAL or IMPORTED")
    notes: Optional[str] = Field(None, max_length=500, description="Descriptive notes or audit context")


class CashBalanceSnapshotUpdate(BaseModel):
    balance_amount: Optional[Decimal] = Field(None, gt=0, description="Updated balance amount in base currency")
    minimum_cash_threshold: Optional[Decimal] = Field(None, ge=0, description="Updated minimum cash reserve")
    as_of_date: Optional[date] = Field(None, description="Updated effective date for snapshot")
    notes: Optional[str] = Field(None, max_length=500, description="Audit reason or context for modification")


class CashBalanceSnapshotResponse(BaseModel):
    snapshot_id: str
    company_id: str
    as_of_date: date
    balance_amount: Decimal
    currency: str
    minimum_cash_threshold: Optional[Decimal] = None
    source: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# 2. Collection Forecast Override Schemas
# ==============================================================================

class CollectionOverrideCreate(BaseModel):
    company_id: str = Field(..., description="Company ID")
    invoice_id: str = Field(..., description="Target invoice ID")
    expected_collection_date: date = Field(..., description="Manual expected collection date")
    expected_amount: Optional[Decimal] = Field(None, gt=0, description="Expected collection amount")
    recovery_probability: Optional[Decimal] = Field(Decimal("1.00"), ge=0, le=1, description="Recovery probability 0.0 to 1.0")
    commitment_source: Optional[str] = Field("CUSTOMER_COMMITMENT", max_length=100, description="Commitment source")
    notes: Optional[str] = Field(None, max_length=500, description="Reason for override")
    is_active: bool = Field(True, description="Whether this override is active")


class CollectionOverrideUpdate(BaseModel):
    expected_collection_date: Optional[date] = Field(None, description="Updated collection date")
    expected_amount: Optional[Decimal] = Field(None, gt=0, description="Updated expected collection amount")
    recovery_probability: Optional[Decimal] = Field(None, ge=0, le=1, description="Updated recovery probability")
    commitment_source: Optional[str] = Field(None, max_length=100, description="Updated commitment source")
    notes: Optional[str] = Field(None, max_length=500, description="Updated notes")
    is_active: Optional[bool] = Field(None, description="Active status")


class CollectionOverrideResponse(BaseModel):
    override_id: str
    company_id: str
    invoice_id: str
    expected_collection_date: date
    expected_amount: Optional[Decimal] = None
    recovery_probability: Optional[Decimal] = Decimal("1.00")
    commitment_source: Optional[str] = "CUSTOMER_COMMITMENT"
    expected_inflow_amount: Optional[Decimal] = None
    notes: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# 3. Expense Forecast Assumption Schemas
# ==============================================================================

class ExpenseAssumptionCreate(BaseModel):
    company_id: str = Field(..., description="Company ID")
    category: str = Field(..., max_length=100, description="Expense category (e.g. SALARIES, RENT)")
    monthly_amount: Decimal = Field(..., gt=0, description="Expected recurring monthly amount")
    currency: str = Field("INR", min_length=3, max_length=10, description="Currency code")
    effective_start_date: date = Field(..., description="Start date for assumption")
    effective_end_date: Optional[date] = Field(None, description="Optional end date for assumption")
    description: Optional[str] = Field(None, max_length=500, description="Context or description")
    source: str = Field("MANUAL", description="Source: MANUAL or BUDGET")
    is_active: bool = Field(True, description="Whether assumption is currently active")


class ExpenseAssumptionUpdate(BaseModel):
    category: Optional[str] = Field(None, max_length=100)
    monthly_amount: Optional[Decimal] = Field(None, gt=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=10)
    effective_start_date: Optional[date] = None
    effective_end_date: Optional[date] = None
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class ExpenseAssumptionResponse(BaseModel):
    assumption_id: str
    company_id: str
    category: str
    monthly_amount: Decimal
    currency: str
    effective_start_date: date
    effective_end_date: Optional[date] = None
    description: Optional[str] = None
    source: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# 4. Forecast Output & Projection Schemas
# ==============================================================================

class LiquidityAlert(BaseModel):
    alert_id: str
    alert_type: str = Field(..., description="Alert classification")
    severity: str = Field(..., description="CRITICAL, WARNING, or INFO")
    related_date: Optional[date] = None
    relevant_amount: Optional[Decimal] = None
    description: str
    supporting_reference: Optional[str] = None
    recommended_action: str


class DailyCashflowProjection(BaseModel):
    date: date
    opening_balance: Decimal
    expected_inflows: Decimal
    expected_outflows: Decimal
    net_cash_flow: Decimal
    closing_balance: Decimal
    projected_liquidity_status: str = Field("HEALTHY", description="HEALTHY, CAUTION, or DEFICIT")
    # Convenience aliases for frontend Recharts compatibility
    inflow: Optional[Decimal] = None
    outflow: Optional[Decimal] = None
    net: Optional[Decimal] = None


class MonthlyCashflowProjection(BaseModel):
    month: str = Field(..., description="Calendar month YYYY-MM")
    opening_balance: Decimal
    expected_inflows: Decimal
    expected_outflows: Decimal
    net_cash_flow: Decimal
    closing_balance: Decimal


class ForecastSummary(BaseModel):
    opening_balance: Decimal
    expected_inflows: Decimal
    expected_outflows: Decimal
    net_cash_flow: Decimal
    closing_balance: Decimal
    # Collection breakdown and actual financial activity
    actual_inflows: Decimal = Decimal("0.00")
    actual_outflows: Decimal = Decimal("0.00")
    scheduled_collections: Decimal = Decimal("0.00")
    overdue_recovery_forecast: Decimal = Decimal("0.00")
    total_expected_inflows: Decimal = Decimal("0.00")
    projected_outflows: Decimal = Decimal("0.00")
    projected_closing_balance: Decimal = Decimal("0.00")
    minimum_projected_balance: Decimal
    minimum_balance_date: Optional[date] = None
    days_below_threshold: int = 0
    days_negative_balance: int = 0


class DataFreshnessReport(BaseModel):
    latest_actual_transaction_date: Optional[date] = None
    latest_complete_historical_month: Optional[str] = None
    days_since_last_actual_data: int = 0
    expense_data_stale: bool = False
    warnings: List[str] = Field(default_factory=list)


class CashflowForecastResponse(BaseModel):
    forecast_id: str
    company_id: str
    as_of_date: date
    base_currency: str = "INR"
    forecast_horizon_days: int
    opening_balance: Decimal
    forecast_reliability: ForecastReliability
    data_freshness: DataFreshnessReport
    summary: ForecastSummary
    alerts: List[LiquidityAlert] = Field(default_factory=list)
    monthly_projection: List[MonthlyCashflowProjection] = Field(default_factory=list)
    daily_projection: List[DailyCashflowProjection] = Field(default_factory=list)
    unresolved_overdue_receivables: List[Dict[str, Any]] = Field(default_factory=list)
    foreign_currency_exposures: List[Dict[str, Any]] = Field(default_factory=list)
    # Convenience top-level aliases for frontend backward compatibility
    total_inflow: Optional[Decimal] = None
    total_outflow: Optional[Decimal] = None
    net_cash_flow: Optional[Decimal] = None
    closing_balance: Optional[Decimal] = None
    daily_projections: Optional[List[DailyCashflowProjection]] = None
    # Collection breakdown top-level aliases
    actual_inflows: Optional[Decimal] = None
    actual_outflows: Optional[Decimal] = None
    scheduled_collections: Optional[Decimal] = None
    overdue_recovery_forecast: Optional[Decimal] = None
    total_expected_inflows: Optional[Decimal] = None
    projected_outflows: Optional[Decimal] = None
    projected_closing_balance: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# 5. Forecast Request & What-If Scenario Schemas
# ==============================================================================

class ForecastGenerateRequest(BaseModel):
    company_id: str = Field("FINORA_DEMO", description="Company ID")
    as_of_date: date = Field(..., description="As-of reference date")
    horizon_days: int = Field(30, description="30, 60, or 90 days")
    base_currency: str = Field("INR", description="Base reporting currency")


class WhatIfScenarioRequest(BaseModel):
    company_id: str = Field("FINORA_DEMO", description="Company ID")
    as_of_date: Optional[date] = Field(None, description="As-of reference date (defaults to latest snapshot date or today)")
    horizon_days: int = Field(90, description="Horizon days (30, 60, or 90)")
    payment_delay_days: int = Field(0, ge=0, le=90, description="Additional payment delay in days")
    expense_increase_percentage: Decimal = Field(
        Decimal("0.00"), ge=0, le=100, description="Percentage increase on projected expenses"
    )
    # Frontend aliases for seamless compatibility
    customer_delay_days: Optional[int] = Field(None, ge=0, le=90, description="Alias for payment_delay_days")
    expense_increase_percent: Optional[Decimal] = Field(None, ge=0, le=100, description="Alias for expense_increase_percentage")


class ScenarioComparisonResponse(BaseModel):
    baseline_forecast_id: str
    scenario_forecast_id: str
    company_id: str
    as_of_date: date
    horizon_days: int
    simulation_parameters: Dict[str, Any]
    baseline_ending_cash: Decimal
    scenario_ending_cash: Decimal
    net_cash_difference: Decimal
    baseline_minimum_balance: Decimal
    scenario_minimum_balance: Decimal
    baseline_shortage_date: Optional[date] = None
    scenario_shortage_date: Optional[date] = None
    additional_liquidity_pressure: Decimal
    collections_delayed_outside_horizon: Decimal
    explanation: str
    status: str = "SIMULATED"
    # Backward compatibility aliases for frontend
    difference_in_closing_balance: Optional[Decimal] = None
    liquidity_pressure: Optional[str] = None
    baseline: Optional[Dict[str, Any]] = None
    scenario: Optional[Dict[str, Any]] = None

