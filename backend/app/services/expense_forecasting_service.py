"""
Expense & Outflow Forecasting Service (Phase 4 Stage 4C).

Aggregates historical cash transactions (OUTFLOW) as the single source of truth,
implements transparent baseline forecasting methods with rolling backtests,
identifies future scheduled commitments, incorporates manual expense assumptions
with category precedence, and tracks data freshness / staleness.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.cash_transaction import CashTransaction
from app.models.expense import Expense
from app.models.monthly_cashflow import MonthlyCashflow
from app.models.expense_forecast_assumption import ExpenseForecastAssumption


def run_chronological_baseline_backtest(monthly_series: List[Decimal]) -> Dict[str, Any]:
    """
    Perform rolling-origin backtesting over historical monthly outflows.
    
    Evaluates:
      A. Last observation
      B. Trailing 3-month average
      C. Trailing 6-month average
      D. Trailing 12-month average
      E. Seasonal naive (12 months lag)
    """
    n = len(monthly_series)
    if n < 14:
        return {
            "selected_method": "TRAILING_3M_AVG",
            "backtest_results": {},
        }

    # Evaluate rolling 1-step-ahead forecasts from month index 12 to n-1
    methods = ["LAST_OBS", "TRAILING_3M", "TRAILING_6M", "TRAILING_12M", "SEASONAL_NAIVE"]
    errors = {m: [] for m in methods}

    for t in range(12, n):
        actual = monthly_series[t]

        # Predictions
        preds = {
            "LAST_OBS": monthly_series[t - 1],
            "TRAILING_3M": sum(monthly_series[t - 3 : t]) / Decimal("3"),
            "TRAILING_6M": sum(monthly_series[t - 6 : t]) / Decimal("6"),
            "TRAILING_12M": sum(monthly_series[t - 12 : t]) / Decimal("12"),
            "SEASONAL_NAIVE": monthly_series[t - 12],
        }

        for m in methods:
            err = actual - preds[m]
            errors[m].append((actual, preds[m], abs(err), err))

    results = {}
    best_method = "TRAILING_3M"
    best_wape = Decimal("1000.0")

    for m in methods:
        data = errors[m]
        tot_actual = sum(x[0] for x in data)
        tot_abs_err = sum(x[2] for x in data)
        tot_bias = sum(x[3] for x in data)
        count = len(data)

        mae = (tot_abs_err / Decimal(str(count))).quantize(Decimal("0.01"))
        wape = ((tot_abs_err / tot_actual) * Decimal("100")).quantize(Decimal("0.01")) if tot_actual > 0 else Decimal("0.00")
        bias = (tot_bias / Decimal(str(count))).quantize(Decimal("0.01"))

        results[m] = {
            "mae": float(mae),
            "wape_pct": float(wape),
            "bias": float(bias),
            "eval_months_count": count,
        }

        if wape < best_wape:
            best_wape = wape
            best_method = m

    return {
        "selected_method": best_method,
        "backtest_results": results,
    }


def forecast_expenses_and_outflows(
    db: Session,
    company_id: str,
    as_of_date: date,
    horizon_days: int = 90,
    base_currency: str = "INR",
) -> Dict[str, Any]:
    """
    Generate daily and monthly outflow projections.
    
    1. Aggregates historical completed outflows from cash_transactions.
    2. Measures data freshness and staleness against as_of_date.
    3. Runs baseline selection.
    4. Identifies valid future scheduled commitments from expenses table.
    5. Incorporates active expense forecast assumptions (superseding category baselines).
    6. Produces daily and monthly outflow schedules.
    """
    horizon_end_date = as_of_date + timedelta(days=horizon_days)

    # 1. Historical completed outflows from cash_transactions (SINGLE SOURCE OF TRUTH)
    hist_txns = (
        db.query(CashTransaction)
        .filter(
            CashTransaction.company_id == company_id,
            CashTransaction.transaction_type == "OUTFLOW",
            CashTransaction.currency == base_currency,
        )
        .order_by(CashTransaction.transaction_date.asc())
        .all()
    )

    latest_actual_date: Optional[date] = None
    if hist_txns:
        latest_actual_date = max(t.transaction_date for t in hist_txns)

    # Data freshness check
    days_since_last_actual = (as_of_date - latest_actual_date).days if latest_actual_date else 999
    expense_data_stale = days_since_last_actual > 90
    warnings = []
    if expense_data_stale:
        warnings.append(
            f"Historical expense information is older than 90 days (last actual: {latest_actual_date}, "
            f"gap: {days_since_last_actual} days relative to as-of date {as_of_date})."
        )

    # Monthly cashflow history
    monthly_cf_records = (
        db.query(MonthlyCashflow)
        .filter(
            MonthlyCashflow.company_id == company_id,
            MonthlyCashflow.currency == base_currency,
        )
        .order_by(MonthlyCashflow.month.asc())
        .all()
    )

    monthly_outflows = [Decimal(str(m.actual_outflows)) for m in monthly_cf_records]
    latest_complete_month = monthly_cf_records[-1].month if monthly_cf_records else None

    # Run backtest comparison
    backtest = run_chronological_baseline_backtest(monthly_outflows)
    selected_method = backtest["selected_method"]

    # Calculate baseline total monthly run-rate
    if len(monthly_outflows) >= 3:
        if selected_method == "TRAILING_6M" and len(monthly_outflows) >= 6:
            baseline_total_monthly = sum(monthly_outflows[-6:]) / Decimal("6")
        elif selected_method == "LAST_OBS":
            baseline_total_monthly = monthly_outflows[-1]
        else:
            baseline_total_monthly = sum(monthly_outflows[-3:]) / Decimal("3")
    elif monthly_outflows:
        baseline_total_monthly = sum(monthly_outflows) / Decimal(str(len(monthly_outflows)))
    else:
        baseline_total_monthly = Decimal("0.00")

    # Category historical proportions from expenses table (paid expenses)
    cat_totals = (
        db.query(Expense.category, func.sum(Expense.amount))
        .filter(
            Expense.company_id == company_id,
            Expense.status == "PAID",
            Expense.currency == base_currency,
        )
        .group_by(Expense.category)
        .all()
    )
    total_paid_expenses = sum((Decimal(str(amt)) for _, amt in cat_totals), Decimal("0.00"))
    cat_proportions = {}
    if total_paid_expenses > 0:
        for cat, amt in cat_totals:
            cat_proportions[cat] = Decimal(str(amt)) / total_paid_expenses
    else:
        cat_proportions = {"GENERAL_OPERATING": Decimal("1.00")}

    # Baseline monthly amount per category
    category_baselines: Dict[str, Decimal] = {}
    for cat, prop in cat_proportions.items():
        category_baselines[cat] = (baseline_total_monthly * prop).quantize(Decimal("0.01"))

    # 2. Fetch Active Manual Expense Assumptions
    active_assumptions = (
        db.query(ExpenseForecastAssumption)
        .filter(
            ExpenseForecastAssumption.company_id == company_id,
            ExpenseForecastAssumption.is_active == True,
            ExpenseForecastAssumption.currency == base_currency,
        )
        .all()
    )

    # 3. Fetch Future Scheduled Commitments from expenses table
    future_commitments = (
        db.query(Expense)
        .filter(
            Expense.company_id == company_id,
            Expense.status != "PAID",
            Expense.currency == base_currency,
            Expense.due_date >= as_of_date,
            Expense.due_date <= horizon_end_date,
        )
        .order_by(Expense.due_date.asc())
        .all()
    )

    scheduled_events: List[Dict[str, Any]] = []

    # Add committed scheduled expenses (exact dates)
    for comm in future_commitments:
        scheduled_events.append({
            "date": comm.due_date,
            "amount": Decimal(str(comm.amount)),
            "category": comm.category,
            "outflow_type": "COMMITTED_EXPENSE",
            "source": f"EXPENSE_ID_{comm.expense_id}",
            "is_estimated": False,
        })

    # 4. Generate daily timeline across horizon
    current_date = as_of_date
    daily_estimated_events: List[Dict[str, Any]] = []

    # Map months in horizon to their active assumptions and baseline overrides
    # For each month, determine effective amount per category
    # Track days per month
    month_days: Dict[str, List[date]] = {}
    while current_date <= horizon_end_date:
        m_str = current_date.strftime("%Y-%m")
        if m_str not in month_days:
            month_days[m_str] = []
        month_days[m_str].append(current_date)
        current_date += timedelta(days=1)

    for m_str, days in month_days.items():
        days_in_month = len(days)
        # Determine for each category whether an assumption applies to this month
        m_start = days[0]
        m_end = days[-1]

        for cat, base_amt in category_baselines.items():
            # Check if active assumption covers this category and period
            matching_asm = next(
                (
                    asm for asm in active_assumptions
                    if asm.category == cat
                    and asm.effective_start_date <= m_end
                    and (asm.effective_end_date is None or asm.effective_end_date >= m_start)
                ),
                None,
            )

            if matching_asm:
                monthly_amt = Decimal(str(matching_asm.monthly_amount))
                src_label = f"MANUAL_ASSUMPTION_{matching_asm.assumption_id}"
            else:
                monthly_amt = base_amt
                src_label = f"BASELINE_{selected_method}"

            daily_rate = (monthly_amt / Decimal(str(days_in_month))).quantize(Decimal("0.01"))
            daily_remainder = monthly_amt - (daily_rate * Decimal(str(days_in_month)))

            for i, d in enumerate(days):
                amt = daily_rate + (daily_remainder if i == 0 else Decimal("0.00"))
                if amt > Decimal("0.00"):
                    daily_estimated_events.append({
                        "date": d,
                        "amount": amt,
                        "category": cat,
                        "outflow_type": "ESTIMATED_OPERATING_EXPENSE",
                        "source": src_label,
                        "is_estimated": True,
                    })

    # Combine committed and estimated events
    all_outflow_events = scheduled_events + daily_estimated_events
    all_outflow_events.sort(key=lambda x: x["date"])

    # Aggregates by horizon
    outflows_30d = sum(
        (ev["amount"] for ev in all_outflow_events if ev["date"] <= as_of_date + timedelta(days=30)),
        Decimal("0.00"),
    )
    outflows_60d = sum(
        (ev["amount"] for ev in all_outflow_events if ev["date"] <= as_of_date + timedelta(days=60)),
        Decimal("0.00"),
    )
    outflows_90d = sum(
        (ev["amount"] for ev in all_outflow_events if ev["date"] <= as_of_date + timedelta(days=90)),
        Decimal("0.00"),
    )

    return {
        "scheduled_events": all_outflow_events,
        "committed_events": scheduled_events,
        "estimated_events": daily_estimated_events,
        "data_freshness": {
            "latest_actual_transaction_date": latest_actual_date,
            "latest_complete_historical_month": latest_complete_month,
            "days_since_last_actual_data": days_since_last_actual,
            "expense_data_stale": expense_data_stale,
            "warnings": warnings,
        },
        "forecasting_metadata": {
            "selected_method": selected_method,
            "baseline_total_monthly": float(baseline_total_monthly),
            "backtest_results": backtest["backtest_results"],
            "active_assumptions_count": len(active_assumptions),
            "future_commitments_count": len(future_commitments),
        },
        "aggregates": {
            "outflows_30d": outflows_30d,
            "outflows_60d": outflows_60d,
            "outflows_90d": outflows_90d,
        },
    }

