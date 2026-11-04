"""
Invoice Collection Forecasting Service (Phase 4 Stage 4B).

Connects directly with Phase 3 ML Payment Risk Engine to produce
probability-weighted invoice collection events, respects manual collection
overrides, handles partially paid invoices with rule-based fallbacks,
and tracks unresolved overdue receivables without look-ahead date shifts.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.collection_forecast_override import CollectionForecastOverride
from app.services.payment_prediction_service import (
    predict_invoice_payment_risk,
    get_latest_prediction,
    PredictionEngine,
)


def get_invoice_financial_status(invoice: Invoice) -> Dict[str, Any]:
    """Calculate invoice amount paid, outstanding amount, and payment status."""
    total_amount = Decimal(str(invoice.invoice_amount))
    payments = invoice.payments or []
    amount_paid = sum((Decimal(str(p.amount)) for p in payments), Decimal("0.00"))
    outstanding = max(Decimal("0.00"), total_amount - amount_paid)

    if str(invoice.status).upper() == "CANCELLED":
        status_str = "CANCELLED"
    elif amount_paid >= total_amount and total_amount > 0:
        status_str = "PAID"
    elif amount_paid > 0:
        status_str = "PARTIALLY_PAID"
    else:
        status_str = "UNPAID"

    return {
        "total_amount": total_amount,
        "amount_paid": amount_paid,
        "outstanding_amount": outstanding,
        "payment_status": status_str,
    }


def forecast_invoice_collections(
    db: Session,
    company_id: str,
    as_of_date: date,
    horizon_days: int = 90,
    base_currency: str = "INR",
) -> Dict[str, Any]:
    """
    Generate schedule of probability-weighted invoice collections.

    Returns:
        Dict containing:
            - scheduled_events: List of daily collection events (date, amount, invoice_id, type)
            - invoice_details: Detailed breakdown per eligible invoice
            - unresolved_overdue: Overdue invoices with past collection estimates
            - foreign_currency_exposures: Invoices not in base_currency
            - aggregates: Inflow summary metrics
    """
    horizon_end_date = as_of_date + timedelta(days=horizon_days)

    # 1. Fetch all company invoices
    invoices = (
        db.query(Invoice)
        .filter(Invoice.company_id == company_id)
        .all()
    )

    # Fetch all active overrides for the company
    active_overrides = {
        ovr.invoice_id: ovr
        for ovr in db.query(CollectionForecastOverride)
        .filter(
            CollectionForecastOverride.company_id == company_id,
            CollectionForecastOverride.is_active == True,
        )
        .all()
    }

    scheduled_events: List[Dict[str, Any]] = []
    invoice_details: List[Dict[str, Any]] = []
    unresolved_overdue: List[Dict[str, Any]] = []
    foreign_currency_exposures: List[Dict[str, Any]] = []
    outside_horizon_events: List[Dict[str, Any]] = []

    total_outstanding_receivables = Decimal("0.00")
    total_forecastable_inflows = Decimal("0.00")
    total_overdue_unresolved = Decimal("0.00")

    for inv in invoices:
        fin = get_invoice_financial_status(inv)
        status_str = fin["payment_status"]
        outstanding = fin["outstanding_amount"]

        # Exclude settled or cancelled
        if status_str in ("PAID", "CANCELLED") or outstanding <= Decimal("0.00"):
            continue

        total_outstanding_receivables += outstanding

        # Foreign currency check
        inv_curr = str(inv.currency).strip().upper()
        if inv_curr != base_currency:
            foreign_currency_exposures.append({
                "invoice_id": inv.invoice_id,
                "customer_id": inv.customer_id,
                "amount": outstanding,
                "currency": inv_curr,
                "due_date": inv.due_date,
                "reason": f"Non-base currency ({inv_curr} vs {base_currency}) excluded from consolidated cashflow",
            })
            continue

        # Check Active Manual Override First
        if inv.invoice_id in active_overrides:
            override = active_overrides[inv.invoice_id]
            coll_date = override.expected_collection_date

            if coll_date < as_of_date:
                # Override date has already passed -> OVERDUE_UNRESOLVED
                unresolved_overdue.append({
                    "invoice_id": inv.invoice_id,
                    "customer_id": inv.customer_id,
                    "outstanding_amount": outstanding,
                    "due_date": inv.due_date,
                    "expected_collection_date": coll_date,
                    "status": "OVERDUE_UNRESOLVED",
                    "reason": "Active manual override collection date is in the past.",
                })
                total_overdue_unresolved += outstanding
            else:
                # Active override is current or future
                event = {
                    "date": coll_date,
                    "amount": outstanding,
                    "invoice_id": inv.invoice_id,
                    "customer_id": inv.customer_id,
                    "collection_type": "MANUAL_OVERRIDE",
                    "probability": Decimal("1.00"),
                }
                if as_of_date <= coll_date <= horizon_end_date:
                    scheduled_events.append(event)
                    total_forecastable_inflows += outstanding
                else:
                    outside_horizon_events.append(event)

                invoice_details.append({
                    "invoice_id": inv.invoice_id,
                    "customer_id": inv.customer_id,
                    "total_amount": fin["total_amount"],
                    "outstanding_amount": outstanding,
                    "due_date": inv.due_date,
                    "status": "OVERRIDDEN",
                    "source": "MANUAL_OVERRIDE",
                    "events": [event],
                })
            continue

        # Partially Paid Invoices -> RULE_BASED fallback
        if status_str == "PARTIALLY_PAID":
            coll_date = inv.due_date
            if coll_date < as_of_date:
                unresolved_overdue.append({
                    "invoice_id": inv.invoice_id,
                    "customer_id": inv.customer_id,
                    "outstanding_amount": outstanding,
                    "due_date": inv.due_date,
                    "expected_collection_date": coll_date,
                    "status": "OVERDUE_UNRESOLVED",
                    "reason": "Partially paid invoice due date is in the past.",
                })
                total_overdue_unresolved += outstanding
            else:
                event = {
                    "date": coll_date,
                    "amount": outstanding,
                    "invoice_id": inv.invoice_id,
                    "customer_id": inv.customer_id,
                    "collection_type": "RULE_BASED",
                    "probability": Decimal("1.00"),
                }
                if as_of_date <= coll_date <= horizon_end_date:
                    scheduled_events.append(event)
                    total_forecastable_inflows += outstanding
                else:
                    outside_horizon_events.append(event)

                invoice_details.append({
                    "invoice_id": inv.invoice_id,
                    "customer_id": inv.customer_id,
                    "total_amount": fin["total_amount"],
                    "outstanding_amount": outstanding,
                    "due_date": inv.due_date,
                    "status": "PARTIALLY_PAID",
                    "source": "RULE_BASED",
                    "events": [event],
                })
            continue

        # Completely UNPAID Invoice -> Phase 3 ML Model
        # Obtain prediction
        pred_dict = get_latest_prediction(db, inv.invoice_id)
        if not pred_dict:
            try:
                pred_dict = predict_invoice_payment_risk(db, inv.invoice_id)
            except Exception:
                pred_dict = None

        if pred_dict:
            p_late = Decimal(str(round(pred_dict["predicted_late_probability"], 4)))
            p_ontime = Decimal("1.0000") - p_late
            cond_delay = int(round(pred_dict["predicted_delay_days"]))

            ontime_date = inv.due_date
            late_date = inv.due_date + timedelta(days=cond_delay)

            ontime_amount = (outstanding * p_ontime).quantize(Decimal("0.01"))
            late_amount = outstanding - ontime_amount  # Guarantees exact sum = outstanding

            # Check overdue resolution
            # If both ontime_date and late_date are in the past relative to as_of_date:
            if late_date < as_of_date:
                unresolved_overdue.append({
                    "invoice_id": inv.invoice_id,
                    "customer_id": inv.customer_id,
                    "outstanding_amount": outstanding,
                    "due_date": inv.due_date,
                    "predicted_late_date": late_date,
                    "nominal_estimated_date": pred_dict["estimated_payment_date"],
                    "late_probability": float(p_late),
                    "status": "OVERDUE_UNRESOLVED",
                    "reason": "Nominal predicted payment date and due date are both in the past.",
                })
                total_overdue_unresolved += outstanding
                continue

            inv_events = []
            # On-time scenario
            if ontime_date >= as_of_date and ontime_amount > Decimal("0.00"):
                ev_ontime = {
                    "date": ontime_date,
                    "amount": ontime_amount,
                    "invoice_id": inv.invoice_id,
                    "customer_id": inv.customer_id,
                    "collection_type": "ML_ON_TIME",
                    "probability": p_ontime,
                }
                inv_events.append(ev_ontime)
                if ontime_date <= horizon_end_date:
                    scheduled_events.append(ev_ontime)
                    total_forecastable_inflows += ontime_amount
                else:
                    outside_horizon_events.append(ev_ontime)

            # Late scenario
            if late_date >= as_of_date and late_amount > Decimal("0.00"):
                ev_late = {
                    "date": late_date,
                    "amount": late_amount,
                    "invoice_id": inv.invoice_id,
                    "customer_id": inv.customer_id,
                    "collection_type": "ML_LATE",
                    "probability": p_late,
                }
                inv_events.append(ev_late)
                if late_date <= horizon_end_date:
                    scheduled_events.append(ev_late)
                    total_forecastable_inflows += late_amount
                else:
                    outside_horizon_events.append(ev_late)

            invoice_details.append({
                "invoice_id": inv.invoice_id,
                "customer_id": inv.customer_id,
                "total_amount": fin["total_amount"],
                "outstanding_amount": outstanding,
                "due_date": inv.due_date,
                "late_probability": float(p_late),
                "conditional_delay_days": cond_delay,
                "expected_delay_days": float(p_late) * cond_delay,
                "model_version": pred_dict["model_version"],
                "source": "ML_PREDICTED",
                "events": inv_events,
            })
        else:
            # Fallback if prediction unavailable
            if inv.due_date < as_of_date:
                unresolved_overdue.append({
                    "invoice_id": inv.invoice_id,
                    "customer_id": inv.customer_id,
                    "outstanding_amount": outstanding,
                    "due_date": inv.due_date,
                    "status": "OVERDUE_UNRESOLVED",
                    "reason": "Invoice due date is in the past and no ML prediction available.",
                })
                total_overdue_unresolved += outstanding
            else:
                ev = {
                    "date": inv.due_date,
                    "amount": outstanding,
                    "invoice_id": inv.invoice_id,
                    "customer_id": inv.customer_id,
                    "collection_type": "RULE_BASED",
                    "probability": Decimal("1.00"),
                }
                if inv.due_date <= horizon_end_date:
                    scheduled_events.append(ev)
                    total_forecastable_inflows += outstanding
                else:
                    outside_horizon_events.append(ev)

    # Sort scheduled events chronologically
    scheduled_events.sort(key=lambda x: x["date"])

    # Aggregates by horizon
    inflows_30d = sum(
        (ev["amount"] for ev in scheduled_events if ev["date"] <= as_of_date + timedelta(days=30)),
        Decimal("0.00"),
    )
    inflows_60d = sum(
        (ev["amount"] for ev in scheduled_events if ev["date"] <= as_of_date + timedelta(days=60)),
        Decimal("0.00"),
    )
    inflows_90d = sum(
        (ev["amount"] for ev in scheduled_events if ev["date"] <= as_of_date + timedelta(days=90)),
        Decimal("0.00"),
    )

    return {
        "scheduled_events": scheduled_events,
        "invoice_details": invoice_details,
        "unresolved_overdue": unresolved_overdue,
        "foreign_currency_exposures": foreign_currency_exposures,
        "outside_horizon_events": outside_horizon_events,
        "aggregates": {
            "total_outstanding_receivables": total_outstanding_receivables,
            "total_forecastable_inflows": total_forecastable_inflows,
            "total_overdue_unresolved": total_overdue_unresolved,
            "inflows_30d": inflows_30d,
            "inflows_60d": inflows_60d,
            "inflows_90d": inflows_90d,
        },
    }

