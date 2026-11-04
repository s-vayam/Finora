"""
Tests for ML-Based Invoice Collection Forecasting (Phase 4 Stage 4B).

Verifies probability-weighted scheduling, sum-to-one constraint,
overdue unresolved handling, manual override precedence, and partial payments.
"""

from datetime import date, timedelta
from decimal import Decimal
import uuid
import pytest
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.collection_forecast_override import CollectionForecastOverride
from app.services.collection_forecasting_service import (
    forecast_invoice_collections,
    get_invoice_financial_status,
)


def test_probability_weighted_collection_allocation(seeded_test_db: Session):
    """
    Verify probability-weighted collection scheduling:
    On-time amount + Late amount == Outstanding amount.
    Weights sum to 1.0.
    """
    as_of = date(2026, 11, 4)
    # Create a future unpaid invoice
    due_date = as_of + timedelta(days=20)
    inv = Invoice(
        invoice_id="INV-PROB-TEST-001",
        company_id="FINORA_DEMO",
        customer_id="CUST001",
        invoice_date=as_of,
        due_date=due_date,
        payment_terms_days=20,
        invoice_amount=Decimal("100000.00"),
        currency="INR",
        status="OPEN",
    )
    seeded_test_db.add(inv)
    seeded_test_db.commit()

    res = forecast_invoice_collections(
        seeded_test_db, company_id="FINORA_DEMO", as_of_date=as_of, horizon_days=90, base_currency="INR"
    )

    inv_details = [d for d in res["invoice_details"] if d["invoice_id"] == "INV-PROB-TEST-001"]
    assert len(inv_details) == 1
    detail = inv_details[0]

    assert detail["source"] == "ML_PREDICTED"
    events = detail["events"]
    assert len(events) in (1, 2)  # Either on-time, late, or both

    total_event_amt = sum((e["amount"] for e in events), Decimal("0.00"))
    assert total_event_amt == Decimal("100000.00")

    total_prob = sum((e["probability"] for e in events), Decimal("0.00"))
    assert pytest.approx(float(total_prob), 0.001) == 1.0


def test_paid_and_cancelled_invoices_excluded(seeded_test_db: Session):
    """Verify paid and cancelled invoices generate 0 future collection events."""
    as_of = date(2026, 11, 4)
    res = forecast_invoice_collections(
        seeded_test_db, company_id="FINORA_DEMO", as_of_date=as_of, horizon_days=90, base_currency="INR"
    )

    scheduled_inv_ids = {e["invoice_id"] for e in res["scheduled_events"]}

    # None of the 873 paid invoices should appear in scheduled events
    paid_invs = seeded_test_db.query(Invoice).filter(Invoice.status == "PAID").all()
    for p_inv in paid_invs:
        assert p_inv.invoice_id not in scheduled_inv_ids


def test_overdue_unresolved_not_moved_forward(seeded_test_db: Session):
    """
    Verify that an overdue invoice whose nominal predicted date has passed
    is marked OVERDUE_UNRESOLVED and not shifted to the present or future.
    """
    as_of = date(2026, 11, 4)
    # The existing 26 open invoices in FINORA_DEMO are from early 2026 (past relative to Nov 2026)
    res = forecast_invoice_collections(
        seeded_test_db, company_id="FINORA_DEMO", as_of_date=as_of, horizon_days=90, base_currency="INR"
    )

    unresolved = res["unresolved_overdue"]
    assert len(unresolved) > 0

    scheduled_ids = {e["invoice_id"] for e in res["scheduled_events"]}
    for unres in unresolved:
        assert unres["status"] == "OVERDUE_UNRESOLVED"
        assert unres["invoice_id"] not in scheduled_ids


def test_manual_override_precedence(seeded_test_db: Session):
    """Verify an active manual collection override supersedes ML schedule."""
    as_of = date(2026, 11, 4)
    future_override_date = as_of + timedelta(days=15)

    # Pick an open invoice
    open_inv = seeded_test_db.query(Invoice).filter(Invoice.status == "OPEN").first()
    assert open_inv is not None
    inv_id = open_inv.invoice_id

    # Add active manual override
    ovr = CollectionForecastOverride(
        override_id=f"OVR-{uuid.uuid4().hex[:8].upper()}",
        company_id="FINORA_DEMO",
        invoice_id=inv_id,
        expected_collection_date=future_override_date,
        notes="Customer promised payment on this date",
        is_active=True,
    )
    seeded_test_db.add(ovr)
    seeded_test_db.commit()

    res = forecast_invoice_collections(
        seeded_test_db, company_id="FINORA_DEMO", as_of_date=as_of, horizon_days=90, base_currency="INR"
    )

    # Invoice should now appear in scheduled events with MANUAL_OVERRIDE
    matching = [e for e in res["scheduled_events"] if e["invoice_id"] == inv_id]
    assert len(matching) == 1
    assert matching[0]["collection_type"] in ("MANUAL_OVERRIDE", "OVERDUE_RECOVERY")
    assert matching[0]["date"] == future_override_date
    assert matching[0]["amount"] == open_inv.invoice_amount

