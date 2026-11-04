"""
FastAPI Router for Cash Flow and Liquidity Forecasting (Phase 4).

Preserves existing Phase 1 GET /history endpoint while providing comprehensive
endpoints for cash positions, collection overrides, expense assumptions,
predictive cash flow forecasts, what-if scenarios, and liquidity alerts.
"""

import json
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.monthly_cashflow import MonthlyCashflow
from app.models.cashflow_forecast_run import CashflowForecastRun
from app.schemas.cashflow import MonthlyCashflowResponse
from app.schemas.cashflow_forecast import (
    CashBalanceSnapshotCreate,
    CashBalanceSnapshotUpdate,
    CashBalanceSnapshotResponse,
    CollectionOverrideCreate,
    CollectionOverrideResponse,
    ExpenseAssumptionCreate,
    ExpenseAssumptionUpdate,
    ExpenseAssumptionResponse,
    LiquidityAlert,
    CashflowForecastResponse,
    ForecastGenerateRequest,
    WhatIfScenarioRequest,
    ScenarioComparisonResponse,
)
from app.services.cashflow_data_service import (
    record_cash_position,
    update_cash_position,
    get_latest_cash_position,
    create_collection_override,
    list_collection_overrides,
    deactivate_collection_override,
    create_expense_assumption,
    list_expense_assumptions,
    update_expense_assumption,
    deactivate_expense_assumption,
)
from app.services.cashflow_engine import (
    generate_cashflow_forecast,
    run_what_if_scenario,
)

router = APIRouter(prefix="/cashflow", tags=["Cash Flow & Liquidity Intelligence"])


# ==============================================================================
# 0. Phase 1 Preserved History Endpoint
# ==============================================================================

@router.get("/history", response_model=List[MonthlyCashflowResponse], summary="Get historical monthly cash flows")
def get_cashflow_history(db: Session = Depends(get_db)):
    """Return historical monthly cash-flow records in chronological order (Phase 1)."""
    cashflows = (
        db.query(MonthlyCashflow)
        .order_by(MonthlyCashflow.month.asc())
        .all()
    )
    return cashflows


# ==============================================================================
# 1. Opening Cash Balance Position APIs
# ==============================================================================

@router.post(
    "/position",
    response_model=CashBalanceSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record opening cash balance snapshot",
)
def record_cash_balance_position(
    payload: CashBalanceSnapshotCreate,
    db: Session = Depends(get_db),
):
    """Record an opening cash balance snapshot for a company and effective date."""
    snapshot = record_cash_position(db, payload)
    return snapshot


@router.patch(
    "/position/{snapshot_id}",
    response_model=CashBalanceSnapshotResponse,
    summary="Update opening cash balance snapshot",
)
def update_cash_balance_position(
    snapshot_id: str,
    payload: CashBalanceSnapshotUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing cash balance snapshot with audit tracking."""
    return update_cash_position(db, snapshot_id, payload)


@router.get(
    "/position/latest",
    response_model=CashBalanceSnapshotResponse,
    summary="Get latest cash balance position",
)
def get_latest_cash_balance_position(
    company_id: str = Query("FINORA_DEMO", description="Target company ID"),
    as_of_date: Optional[date] = Query(None, description="Optional effective cutoff date"),
    currency: str = Query("INR", description="Reporting currency"),
    db: Session = Depends(get_db),
):
    """Retrieve the most recent cash balance snapshot for the company."""
    snapshot = get_latest_cash_position(db, company_id=company_id, as_of_date=as_of_date, currency=currency)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No cash balance snapshot found for company '{company_id}'.",
        )
    return snapshot


# ==============================================================================
# 2. Collection Forecast Override APIs
# ==============================================================================

@router.post(
    "/collection-overrides",
    response_model=CollectionOverrideResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create manual collection forecast override",
)
def create_invoice_collection_override(
    payload: CollectionOverrideCreate,
    db: Session = Depends(get_db),
):
    """Record a manual expected collection date override for an overdue or specific invoice."""
    override = create_collection_override(db, payload)
    return override


@router.get(
    "/collection-overrides",
    response_model=List[CollectionOverrideResponse],
    summary="List collection forecast overrides",
)
def list_invoice_collection_overrides(
    company_id: str = Query("FINORA_DEMO", description="Company ID"),
    invoice_id: Optional[str] = Query(None, description="Filter by invoice ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
):
    """Retrieve collection overrides for the company."""
    return list_collection_overrides(db, company_id=company_id, invoice_id=invoice_id, is_active=is_active)


@router.delete(
    "/collection-overrides/{override_id}",
    response_model=CollectionOverrideResponse,
    summary="Deactivate collection forecast override",
)
def remove_invoice_collection_override(
    override_id: str,
    db: Session = Depends(get_db),
):
    """Soft-deactivate an active collection override (maintains audit trail)."""
    return deactivate_collection_override(db, override_id)


# ==============================================================================
# 3. Expense Forecast Assumption APIs
# ==============================================================================

@router.post(
    "/expense-assumptions",
    response_model=ExpenseAssumptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create expense forecast assumption",
)
def create_expense_forecast_assumption(
    payload: ExpenseAssumptionCreate,
    db: Session = Depends(get_db),
):
    """Record a recurring monthly expense assumption that supersedes category baseline."""
    return create_expense_assumption(db, payload)


@router.get(
    "/expense-assumptions",
    response_model=List[ExpenseAssumptionResponse],
    summary="List expense forecast assumptions",
)
def list_expense_forecast_assumptions(
    company_id: str = Query("FINORA_DEMO", description="Company ID"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
):
    """Retrieve expense forecast assumptions for the company."""
    return list_expense_assumptions(db, company_id=company_id, category=category, is_active=is_active)


@router.patch(
    "/expense-assumptions/{assumption_id}",
    response_model=ExpenseAssumptionResponse,
    summary="Update expense forecast assumption",
)
def update_expense_forecast_assumption(
    assumption_id: str,
    payload: ExpenseAssumptionUpdate,
    db: Session = Depends(get_db),
):
    """Update active expense forecast assumption values."""
    return update_expense_assumption(db, assumption_id, payload)


@router.delete(
    "/expense-assumptions/{assumption_id}",
    response_model=ExpenseAssumptionResponse,
    summary="Deactivate expense forecast assumption",
)
def remove_expense_forecast_assumption(
    assumption_id: str,
    db: Session = Depends(get_db),
):
    """Soft-deactivate an active expense assumption."""
    return deactivate_expense_assumption(db, assumption_id)


# ==============================================================================
# 4. Cash Flow Forecast & Horizon APIs
# ==============================================================================

@router.get(
    "/forecast",
    response_model=CashflowForecastResponse,
    summary="Generate cash flow forecast by horizon (30/60/90 days)",
)
def get_cashflow_forecast(
    company_id: str = Query("FINORA_DEMO", description="Company ID"),
    horizon_days: int = Query(30, description="Forecast horizon (30, 60, or 90 days)"),
    as_of_date: Optional[date] = Query(None, description="Reference as-of date (default: today)"),
    base_currency: str = Query("INR", description="Base reporting currency"),
    db: Session = Depends(get_db),
):
    """
    Generate predictive cash flow forecast for 30, 60, or 90 days.
    Requires an applicable opening cash balance snapshot.
    """
    ref_date = as_of_date or date.today()
    forecast = generate_cashflow_forecast(
        db,
        company_id=company_id,
        as_of_date=ref_date,
        horizon_days=horizon_days,
        base_currency=base_currency,
        persist=True,
    )
    return forecast


@router.post(
    "/forecast/generate",
    response_model=CashflowForecastResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate and persist custom cash flow forecast",
)
def generate_custom_cashflow_forecast(
    payload: ForecastGenerateRequest,
    db: Session = Depends(get_db),
):
    """Generate and persist a cash flow forecast using explicit parameters."""
    forecast = generate_cashflow_forecast(
        db,
        company_id=payload.company_id,
        as_of_date=payload.as_of_date,
        horizon_days=payload.horizon_days,
        base_currency=payload.base_currency,
        persist=True,
    )
    return forecast


@router.get(
    "/forecast/{forecast_id}",
    response_model=CashflowForecastResponse,
    summary="Get persisted cash flow forecast by ID",
)
def get_persisted_cashflow_forecast(
    forecast_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve a previously generated and persisted forecast run."""
    run = db.query(CashflowForecastRun).filter(CashflowForecastRun.forecast_id == forecast_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast run '{forecast_id}' not found.",
        )
    try:
        data = json.loads(run.forecast_payload)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Corrupt forecast payload for '{forecast_id}': {e}",
        )


# ==============================================================================
# 5. What-If Scenario Simulator API
# ==============================================================================

@router.post(
    "/scenario",
    response_model=ScenarioComparisonResponse,
    summary="Run what-if scenario simulation",
)
def simulate_what_if_scenario(
    payload: WhatIfScenarioRequest,
    db: Session = Depends(get_db),
):
    """
    Simulate financial impact of customer payment delays and expense increases.
    Compares simulated cash trajectory against baseline forecast.
    """
    ref_date = payload.as_of_date
    if not ref_date:
        latest_pos = get_latest_cash_position(db, company_id=payload.company_id)
        ref_date = latest_pos.as_of_date if latest_pos else date.today()

    delay_days = payload.payment_delay_days
    if payload.customer_delay_days is not None and delay_days == 0:
        delay_days = payload.customer_delay_days

    expense_pct = payload.expense_increase_percentage
    if payload.expense_increase_percent is not None and expense_pct == Decimal("0.00"):
        expense_pct = payload.expense_increase_percent

    comparison = run_what_if_scenario(
        db,
        company_id=payload.company_id,
        as_of_date=ref_date,
        horizon_days=payload.horizon_days,
        payment_delay_days=delay_days,
        expense_increase_percentage=expense_pct,
    )
    return comparison


# ==============================================================================
# 6. Liquidity Alerts API
# ==============================================================================

@router.get(
    "/alerts",
    response_model=List[LiquidityAlert],
    summary="Get liquidity and financial risk alerts",
)
def get_liquidity_alerts(
    company_id: str = Query("FINORA_DEMO", description="Company ID"),
    horizon_days: int = Query(90, description="Forecast horizon"),
    as_of_date: Optional[date] = Query(None, description="Reference date"),
    db: Session = Depends(get_db),
):
    """Retrieve active liquidity alerts, cash shortage warnings, and threshold breaches."""
    ref_date = as_of_date or date.today()
    forecast = generate_cashflow_forecast(
        db,
        company_id=company_id,
        as_of_date=ref_date,
        horizon_days=horizon_days,
        persist=False,
    )
    return forecast["alerts"]


# ==============================================================================
# 7. Forecast History API
# ==============================================================================

@router.get(
    "/forecast-history",
    response_model=List[Dict[str, Any]],
    summary="Get historical forecast runs",
)
def get_forecast_history(
    company_id: str = Query("FINORA_DEMO", description="Company ID"),
    limit: int = Query(20, ge=1, le=100, description="Number of runs to return"),
    db: Session = Depends(get_db),
):
    """Retrieve recent forecast run metadata and summaries."""
    runs = (
        db.query(CashflowForecastRun)
        .filter(CashflowForecastRun.company_id == company_id)
        .order_by(CashflowForecastRun.created_at.desc())
        .limit(limit)
        .all()
    )
    results = []
    for r in runs:
        results.append({
            "forecast_id": r.forecast_id,
            "company_id": r.company_id,
            "as_of_date": r.as_of_date,
            "horizon_days": r.horizon_days,
            "base_currency": r.base_currency,
            "opening_balance": r.opening_balance,
            "forecast_method_version": r.forecast_method_version,
            "payment_model_version": r.payment_model_version,
            "data_freshness_status": r.data_freshness_status,
            "forecast_reliability": r.forecast_reliability,
            "forecast_type": r.forecast_type,
            "created_at": r.created_at,
        })
    return results
