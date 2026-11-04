"""
Predictive Cash Flow Calculation Engine (Phase 4 Stage 4D & 4E).

Combines ML invoice collection forecasts, expense baseline forecasts,
manual overrides and assumptions into decimal-safe daily roll-forward
projections, monthly aggregations, liquidity warnings, and what-if simulations.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.cashflow_forecast_run import CashflowForecastRun
from app.services.cashflow_data_service import get_latest_cash_position
from app.services.collection_forecasting_service import forecast_invoice_collections
from app.services.expense_forecasting_service import forecast_expenses_and_outflows
from app.schemas.cashflow_forecast import (
    ForecastReliability,
    LiquidityAlert,
    DailyCashflowProjection,
    MonthlyCashflowProjection,
    ForecastSummary,
    DataFreshnessReport,
    CashflowForecastResponse,
    ScenarioComparisonResponse,
)


def generate_cashflow_forecast(
    db: Session,
    company_id: str,
    as_of_date: date,
    horizon_days: int = 90,
    base_currency: str = "INR",
    payment_delay_days: int = 0,
    expense_increase_percentage: Decimal = Decimal("0.00"),
    forecast_type: str = "BASELINE",
    persist: bool = True,
) -> Dict[str, Any]:
    """
    Execute full predictive cash flow forecasting calculation.

    Raises:
        HTTPException 409 OPENING_BALANCE_REQUIRED if no opening balance snapshot exists.
        HTTPException 404 if company does not exist.
        HTTPException 422 if horizon is invalid.
    """
    if horizon_days not in (30, 60, 90):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Supported forecast horizons are 30, 60, or 90 days.",
        )

    company = db.query(Company).filter(Company.company_id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company '{company_id}' not found.",
        )

    # 1. Opening Cash Balance Snapshot Enforcement
    snapshot = get_latest_cash_position(
        db, company_id=company_id, as_of_date=as_of_date, currency=base_currency
    )
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "OPENING_BALANCE_REQUIRED",
                "message": (
                    f"An opening cash balance snapshot is required for company '{company_id}' "
                    f"as of '{as_of_date}' in currency '{base_currency}'. "
                    f"Please record an opening position via POST /api/v1/cashflow/position before generating a forecast."
                ),
            },
        )

    opening_balance = Decimal(str(snapshot.balance_amount))
    min_threshold = (
        Decimal(str(snapshot.minimum_cash_threshold))
        if snapshot.minimum_cash_threshold is not None
        else Decimal("0.00")
    )

    horizon_end_date = as_of_date + timedelta(days=horizon_days)

    # 2. Inflow Forecast (from Stage 4B)
    inflows_res = forecast_invoice_collections(
        db, company_id=company_id, as_of_date=as_of_date, horizon_days=horizon_days, base_currency=base_currency
    )

    scheduled_inflows: List[Dict[str, Any]] = []
    collections_delayed_outside_horizon = Decimal("0.00")

    for ev in inflows_res["scheduled_events"]:
        ev_date = ev["date"]
        ev_amt = ev["amount"]

        # Apply What-If payment delay if simulated
        if payment_delay_days > 0:
            ev_date = ev_date + timedelta(days=payment_delay_days)

        if as_of_date <= ev_date <= horizon_end_date:
            scheduled_inflows.append({
                "date": ev_date,
                "amount": ev_amt,
                "type": ev["collection_type"],
            })
        else:
            collections_delayed_outside_horizon += ev_amt

    # 3. Outflow Forecast (from Stage 4C)
    outflows_res = forecast_expenses_and_outflows(
        db, company_id=company_id, as_of_date=as_of_date, horizon_days=horizon_days, base_currency=base_currency
    )

    scheduled_outflows: List[Dict[str, Any]] = []
    expense_multiplier = Decimal("1.00") + (expense_increase_percentage / Decimal("100.00"))

    for ev in outflows_res["scheduled_events"]:
        ev_date = ev["date"]
        ev_amt = ev["amount"]

        # Apply What-If expense increase if simulated
        if expense_increase_percentage > Decimal("0.00"):
            ev_amt = (ev_amt * expense_multiplier).quantize(Decimal("0.01"))

        if as_of_date <= ev_date <= horizon_end_date:
            scheduled_outflows.append({
                "date": ev_date,
                "amount": ev_amt,
                "category": ev["category"],
                "type": ev["outflow_type"],
            })

    # Group events by calendar date
    inflows_by_date: Dict[date, Decimal] = {}
    for ev in scheduled_inflows:
        d = ev["date"]
        inflows_by_date[d] = inflows_by_date.get(d, Decimal("0.00")) + ev["amount"]

    outflows_by_date: Dict[date, Decimal] = {}
    for ev in scheduled_outflows:
        d = ev["date"]
        outflows_by_date[d] = outflows_by_date.get(d, Decimal("0.00")) + ev["amount"]

    # 4. Daily Projections with Decimal Roll-Forward
    daily_projections: List[Dict[str, Any]] = []
    curr_date = as_of_date
    running_opening = opening_balance

    min_projected_balance = opening_balance
    min_balance_date: Optional[date] = as_of_date
    days_below_threshold = 0
    days_negative_balance = 0

    cumulative_inflows = Decimal("0.00")
    cumulative_outflows = Decimal("0.00")

    while curr_date <= horizon_end_date:
        d_in = inflows_by_date.get(curr_date, Decimal("0.00"))
        d_out = outflows_by_date.get(curr_date, Decimal("0.00"))
        net = d_in - d_out
        closing = running_opening + net

        cumulative_inflows += d_in
        cumulative_outflows += d_out

        if closing < min_projected_balance:
            min_projected_balance = closing
            min_balance_date = curr_date

        if closing < Decimal("0.00"):
            status_str = "DEFICIT"
            days_negative_balance += 1
            days_below_threshold += 1
        elif closing < min_threshold:
            status_str = "CAUTION"
            days_below_threshold += 1
        else:
            status_str = "HEALTHY"

        daily_projections.append({
            "date": curr_date,
            "opening_balance": running_opening,
            "expected_inflows": d_in,
            "expected_outflows": d_out,
            "net_cash_flow": net,
            "closing_balance": closing,
            "projected_liquidity_status": status_str,
        })

        running_opening = closing
        curr_date += timedelta(days=1)

    # 5. Monthly Aggregation
    monthly_projections: List[Dict[str, Any]] = []
    months_dict: Dict[str, List[Dict[str, Any]]] = {}
    for day in daily_projections:
        m_key = day["date"].strftime("%Y-%m")
        if m_key not in months_dict:
            months_dict[m_key] = []
        months_dict[m_key].append(day)

    for m_key, days_list in months_dict.items():
        m_open = days_list[0]["opening_balance"]
        m_in = sum((d["expected_inflows"] for d in days_list), Decimal("0.00"))
        m_out = sum((d["expected_outflows"] for d in days_list), Decimal("0.00"))
        m_net = m_in - m_out
        m_close = days_list[-1]["closing_balance"]

        monthly_projections.append({
            "month": m_key,
            "opening_balance": m_open,
            "expected_inflows": m_in,
            "expected_outflows": m_out,
            "net_cash_flow": m_net,
            "closing_balance": m_close,
        })

    # 6. Deterministic Liquidity Alerts
    alerts: List[Dict[str, Any]] = []

    # Alert A: Cash Shortage (Negative balance)
    if days_negative_balance > 0:
        first_neg_day = next(d for d in daily_projections if d["closing_balance"] < Decimal("0.00"))
        alerts.append({
            "alert_id": f"ALT-SHORTAGE-{uuid.uuid4().hex[:8].upper()}",
            "alert_type": "CASH_SHORTAGE",
            "severity": "CRITICAL",
            "related_date": first_neg_day["date"],
            "relevant_amount": min_projected_balance,
            "description": (
                f"Projected closing cash balance enters a deficit starting on {first_neg_day['date']} "
                f"and reaches a low of {min_projected_balance} {base_currency}."
            ),
            "supporting_reference": f"Days in deficit: {days_negative_balance}",
            "recommended_action": "Arrange short-term credit facility or accelerate invoice collections immediately.",
        })

    # Alert B: Minimum Cash Threshold Breach
    if days_below_threshold > 0 and days_negative_balance == 0:
        first_breach_day = next(d for d in daily_projections if d["closing_balance"] < min_threshold)
        alerts.append({
            "alert_id": f"ALT-THRESHOLD-{uuid.uuid4().hex[:8].upper()}",
            "alert_type": "MINIMUM_THRESHOLD_BREACH",
            "severity": "WARNING",
            "related_date": first_breach_day["date"],
            "relevant_amount": min_projected_balance,
            "description": (
                f"Projected cash balance falls below configured minimum threshold of {min_threshold} {base_currency} "
                f"starting on {first_breach_day['date']}."
            ),
            "supporting_reference": f"Days below reserve: {days_below_threshold}",
            "recommended_action": "Review non-critical operational disbursements and defer discretionary capital expenditures.",
        })

    # Alert C: Delayed Collection Exposure
    for inv_detail in inflows_res["invoice_details"]:
        if (
            inv_detail.get("late_probability", 0.0) >= 0.60
            and inv_detail["outstanding_amount"] >= Decimal("500000.00")
        ):
            alerts.append({
                "alert_id": f"ALT-DELAY-{inv_detail['invoice_id']}",
                "alert_type": "DELAYED_COLLECTION_EXPOSURE",
                "severity": "WARNING",
                "related_date": inv_detail["due_date"],
                "relevant_amount": inv_detail["outstanding_amount"],
                "description": (
                    f"High-value invoice {inv_detail['invoice_id']} ({inv_detail['outstanding_amount']} {base_currency}) "
                    f"for customer {inv_detail['customer_id']} has high late payment risk ({inv_detail['late_probability']:.1%})."
                ),
                "supporting_reference": f"Conditional delay: {inv_detail.get('conditional_delay_days', 0)} days",
                "recommended_action": "Initiate early payment reminder and confirm invoice receipt with customer finance team.",
            })

    # Alert D: Overdue Receivables Unresolved
    unresolved_list = inflows_res["unresolved_overdue"]
    if unresolved_list:
        total_overdue = sum((item["outstanding_amount"] for item in unresolved_list), Decimal("0.00"))
        alerts.append({
            "alert_id": f"ALT-OVERDUE-{uuid.uuid4().hex[:8].upper()}",
            "alert_type": "OVERDUE_RECEIVABLES",
            "severity": "WARNING",
            "related_date": as_of_date,
            "relevant_amount": total_overdue,
            "description": (
                f"{len(unresolved_list)} unpaid invoice(s) totaling {total_overdue} {base_currency} "
                f"have past-due collection dates and are excluded from future cash inflows."
            ),
            "supporting_reference": f"Unresolved count: {len(unresolved_list)}",
            "recommended_action": "Review overdue receivables and supply manual collection overrides via POST /api/v1/cashflow/collection-overrides.",
        })

    # Alert E: Stale Expense Data
    data_freshness_dict = outflows_res["data_freshness"]
    if data_freshness_dict["expense_data_stale"]:
        alerts.append({
            "alert_id": f"ALT-STALE-{uuid.uuid4().hex[:8].upper()}",
            "alert_type": "STALE_EXPENSE_DATA",
            "severity": "WARNING",
            "related_date": as_of_date,
            "relevant_amount": None,
            "description": (
                f"Actual historical expense information is older than 90 days "
                f"(last recorded outflow: {data_freshness_dict['latest_actual_transaction_date']})."
            ),
            "supporting_reference": f"Gap: {data_freshness_dict['days_since_last_actual_data']} days",
            "recommended_action": "Define current monthly expense assumptions via POST /api/v1/cashflow/expense-assumptions.",
        })

    # Alert F: Foreign Currency Excluded
    if inflows_res["foreign_currency_exposures"]:
        alerts.append({
            "alert_id": f"ALT-FX-{uuid.uuid4().hex[:8].upper()}",
            "alert_type": "FOREIGN_CURRENCY_EXCLUDED",
            "severity": "INFO",
            "related_date": as_of_date,
            "relevant_amount": None,
            "description": (
                f"{len(inflows_res['foreign_currency_exposures'])} non-base-currency invoice(s) "
                f"were excluded from the consolidated {base_currency} cashflow forecast."
            ),
            "supporting_reference": "FX conversion integration scheduled for Phase 5",
            "recommended_action": "Review separate foreign currency exposures list.",
        })

    # 7. Forecast Reliability Scoring
    active_assumptions_count = outflows_res["forecasting_metadata"]["active_assumptions_count"]
    is_stale = data_freshness_dict["expense_data_stale"]
    unresolved_ratio = (
        float(inflows_res["aggregates"]["total_overdue_unresolved"] / inflows_res["aggregates"]["total_outstanding_receivables"])
        if inflows_res["aggregates"]["total_outstanding_receivables"] > 0
        else 0.0
    )

    if is_stale and active_assumptions_count == 0:
        reliability = ForecastReliability.LOW
    elif is_stale or unresolved_ratio > 0.50:
        reliability = ForecastReliability.MODERATE
    else:
        reliability = ForecastReliability.HIGH

    # 8. Assemble Result Payload
    forecast_id = f"CF-{uuid.uuid4().hex[:12].upper()}"
    final_closing = daily_projections[-1]["closing_balance"]
    net_cf = cumulative_inflows - cumulative_outflows

    summary_data = {
        "opening_balance": opening_balance,
        "expected_inflows": cumulative_inflows,
        "expected_outflows": cumulative_outflows,
        "net_cash_flow": net_cf,
        "closing_balance": final_closing,
        "minimum_projected_balance": min_projected_balance,
        "minimum_balance_date": min_balance_date,
        "days_below_threshold": days_below_threshold,
        "days_negative_balance": days_negative_balance,
    }

    result = {
        "forecast_id": forecast_id,
        "company_id": company_id,
        "as_of_date": as_of_date,
        "base_currency": base_currency,
        "forecast_horizon_days": horizon_days,
        "opening_balance": opening_balance,
        "forecast_reliability": reliability.value,
        "data_freshness": data_freshness_dict,
        "summary": summary_data,
        "alerts": alerts,
        "monthly_projection": monthly_projections,
        "daily_projection": daily_projections,
        "unresolved_overdue_receivables": inflows_res["unresolved_overdue"],
        "foreign_currency_exposures": inflows_res["foreign_currency_exposures"],
        "simulation_metadata": {
            "is_simulated": forecast_type == "SIMULATED",
            "payment_delay_days": payment_delay_days,
            "expense_increase_percentage": float(expense_increase_percentage),
            "collections_delayed_outside_horizon": float(collections_delayed_outside_horizon),
        },
    }

    # 9. Persistence in cashflow_forecast_runs
    if persist:
        # Convert Decimal and date objects to strings for JSON serialization
        def json_serial(obj):
            if isinstance(obj, (date, datetime)):
                return obj.isoformat()
            if isinstance(obj, Decimal):
                return str(obj)
            raise TypeError(f"Type {type(obj)} not serializable")

        run_record = CashflowForecastRun(
            forecast_id=forecast_id,
            company_id=company_id,
            as_of_date=as_of_date,
            horizon_days=horizon_days,
            base_currency=base_currency,
            opening_balance=opening_balance,
            forecast_method_version="v1.0.0",
            payment_model_version="v1.0.0",
            data_freshness_status="STALE_EXPENSES" if is_stale else "CURRENT",
            forecast_reliability=reliability.value,
            forecast_type=forecast_type,
            forecast_payload=json.dumps(result, default=json_serial),
        )
        db.add(run_record)
        db.commit()

    return result


def run_what_if_scenario(
    db: Session,
    company_id: str,
    as_of_date: date,
    horizon_days: int = 90,
    payment_delay_days: int = 0,
    expense_increase_percentage: Decimal = Decimal("0.00"),
) -> Dict[str, Any]:
    """
    Run what-if simulation by comparing baseline with modified delay/expense parameters.
    """
    # 1. Baseline forecast
    baseline = generate_cashflow_forecast(
        db,
        company_id=company_id,
        as_of_date=as_of_date,
        horizon_days=horizon_days,
        payment_delay_days=0,
        expense_increase_percentage=Decimal("0.00"),
        forecast_type="BASELINE",
        persist=True,
    )

    # 2. Simulated scenario forecast
    scenario = generate_cashflow_forecast(
        db,
        company_id=company_id,
        as_of_date=as_of_date,
        horizon_days=horizon_days,
        payment_delay_days=payment_delay_days,
        expense_increase_percentage=expense_increase_percentage,
        forecast_type="SIMULATED",
        persist=True,
    )

    base_end = baseline["summary"]["closing_balance"]
    scen_end = scenario["summary"]["closing_balance"]
    diff = scen_end - base_end

    base_min = baseline["summary"]["minimum_projected_balance"]
    scen_min = scenario["summary"]["minimum_projected_balance"]
    liquidity_pressure = base_min - scen_min

    # Shortage dates
    base_shortage = next(
        (d["date"] for d in baseline["daily_projection"] if d["closing_balance"] < Decimal("0.00")),
        None,
    )
    scen_shortage = next(
        (d["date"] for d in scenario["daily_projection"] if d["closing_balance"] < Decimal("0.00")),
        None,
    )

    delayed_outside = Decimal(str(scenario["simulation_metadata"]["collections_delayed_outside_horizon"]))

    explanation = (
        f"Simulated scenario applied +{payment_delay_days} days collection delay and "
        f"+{expense_increase_percentage}% expense inflation. Ending cash shifted from "
        f"{base_end} to {scen_end} (net impact: {diff} INR). "
        f"Collections delayed outside the {horizon_days}-day horizon: {delayed_outside} INR."
    )

    return {
        "baseline_forecast_id": baseline["forecast_id"],
        "scenario_forecast_id": scenario["forecast_id"],
        "company_id": company_id,
        "as_of_date": as_of_date,
        "horizon_days": horizon_days,
        "simulation_parameters": {
            "payment_delay_days": payment_delay_days,
            "expense_increase_percentage": float(expense_increase_percentage),
        },
        "baseline_ending_cash": base_end,
        "scenario_ending_cash": scen_end,
        "net_cash_difference": diff,
        "baseline_minimum_balance": base_min,
        "scenario_minimum_balance": scen_min,
        "baseline_shortage_date": base_shortage,
        "scenario_shortage_date": scen_shortage,
        "additional_liquidity_pressure": liquidity_pressure,
        "collections_delayed_outside_horizon": delayed_outside,
        "explanation": explanation,
        "status": "SIMULATED",
    }

