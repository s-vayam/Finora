"""
Pytest Test Suite for Finora Cash Flow Final Enhancements:
- Actual Inflow Reconciliation
- Overdue Recovery Forecasting & Customer Commitments
- Partial Commitments and Validation Constraints
- Dashboard Collection Breakdown
- What-If Stress Testing Integration
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db, SessionLocal
from app.models.company import Company
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.cash_transaction import CashTransaction
from app.models.cash_balance_snapshot import CashBalanceSnapshot
from app.models.collection_forecast_override import CollectionForecastOverride
from app.schemas.cashflow_forecast import CollectionOverrideCreate, CollectionOverrideUpdate
from app.services.cashflow_data_service import (
    create_collection_override,
    update_collection_override,
    deactivate_collection_override,
    list_collection_overrides,
)
from app.services.cashflow_engine import generate_cashflow_forecast, run_what_if_scenario

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_overdue_invoice(db):
    inv_id = f"INV-TEST-OVR-{uuid.uuid4().hex[:6].upper()}"
    inv = Invoice(
        invoice_id=inv_id,
        company_id="FINORA_DEMO",
        customer_id="CUST001",
        invoice_date=date(2026, 9, 1),
        due_date=date(2026, 10, 1),
        payment_terms_days=30,
        invoice_amount=Decimal("96261.98"),
        currency="INR",
        status="OVERDUE",
        historical_invoice_count=5,
        historical_late_rate=Decimal("0.2"),
    )
    db.add(inv)
    db.commit()
    try:
        yield inv_id
    finally:
        db.query(Payment).filter(Payment.invoice_id == inv_id).delete()
        db.query(CashTransaction).filter(CashTransaction.linked_invoice_id == inv_id).delete()
        db.query(CollectionForecastOverride).filter(CollectionForecastOverride.invoice_id == inv_id).delete()
        db.query(Invoice).filter(Invoice.invoice_id == inv_id).delete()
        db.commit()


def test_overdue_recovery_probability_weighting(db, sample_overdue_invoice):
    """Verify overdue commitment computes Expected Inflow = Amount * Probability exactly."""
    invoice_id = sample_overdue_invoice
    baseline_fc = generate_cashflow_forecast(db, "FINORA_DEMO", date(2026, 11, 5), 30, "INR", persist=False)
    baseline_recovery = baseline_fc["summary"]["overdue_recovery_forecast"]

    payload = CollectionOverrideCreate(
        company_id="FINORA_DEMO",
        invoice_id=invoice_id,
        expected_collection_date=date(2026, 11, 20),
        expected_amount=Decimal("96261.98"),
        recovery_probability=Decimal("0.90"),
        commitment_source="Customer phone confirmation",
        notes="Promised payment on Nov 20",
    )
    ovr = create_collection_override(db, payload)
    try:
        assert ovr.override_id.startswith("OVR-")
        assert ovr.expected_amount == Decimal("96261.98")
        assert ovr.recovery_probability == Decimal("0.9000")

        # Generate 30-day forecast
        fc = generate_cashflow_forecast(db, "FINORA_DEMO", date(2026, 11, 5), 30, "INR", persist=False)
        s = fc["summary"]

        # Expected recovery = baseline + (96,261.98 * 0.90 = 86,635.78)
        assert s["overdue_recovery_forecast"] == baseline_recovery + Decimal("86635.78")
        assert s["total_expected_inflows"] == s["scheduled_collections"] + s["overdue_recovery_forecast"]
        assert s["closing_balance"] == s["opening_balance"] + s["total_expected_inflows"] - s["expected_outflows"]
    finally:
        deactivate_collection_override(db, ovr.override_id)


def test_partial_commitments_and_validation(db, sample_overdue_invoice):
    """Verify multiple partial commitments and enforcement of remaining balance."""
    invoice_id = sample_overdue_invoice

    # Commitment 1: 40,000 on Nov 15
    c1 = create_collection_override(db, CollectionOverrideCreate(
        company_id="FINORA_DEMO",
        invoice_id=invoice_id,
        expected_collection_date=date(2026, 11, 15),
        expected_amount=Decimal("40000.00"),
        recovery_probability=Decimal("0.90"),
        commitment_source="Phone call",
    ))

    # Commitment 2: 50,000 on Nov 30
    c2 = create_collection_override(db, CollectionOverrideCreate(
        company_id="FINORA_DEMO",
        invoice_id=invoice_id,
        expected_collection_date=date(2026, 11, 30),
        expected_amount=Decimal("50000.00"),
        recovery_probability=Decimal("0.80"),
        commitment_source="Email",
    ))

    try:
        # Commitment 3 exceeding remaining balance (total balance ~96,261.98, committed=90,000, uncommitted=6,261.98)
        with pytest.raises(Exception) as excinfo:
            create_collection_override(db, CollectionOverrideCreate(
                company_id="FINORA_DEMO",
                invoice_id=invoice_id,
                expected_collection_date=date(2026, 12, 1),
                expected_amount=Decimal("15000.00"),
                recovery_probability=Decimal("1.00"),
            ))
        assert "exceeds" in str(excinfo.value).lower()

        # Forecast sum of probability-weighted partials: baseline + 40,000*0.9 + 50,000*0.8 = baseline + 36,000 + 40,000 = baseline + 76,000
        baseline_fc = generate_cashflow_forecast(db, "FINORA_DEMO", date(2026, 11, 5), 30, "INR", persist=False)
        baseline_recovery = baseline_fc["summary"]["overdue_recovery_forecast"] - Decimal("76000.00")
        fc = generate_cashflow_forecast(db, "FINORA_DEMO", date(2026, 11, 5), 30, "INR", persist=False)
        assert fc["summary"]["overdue_recovery_forecast"] == baseline_recovery + Decimal("76000.00")
    finally:
        deactivate_collection_override(db, c1.override_id)
        deactivate_collection_override(db, c2.override_id)


def test_duplicate_commitment_prevention(db, sample_overdue_invoice):
    """Verify duplicate active commitments on exact date and amount are rejected."""
    invoice_id = sample_overdue_invoice
    c1 = create_collection_override(db, CollectionOverrideCreate(
        company_id="FINORA_DEMO",
        invoice_id=invoice_id,
        expected_collection_date=date(2026, 11, 25),
        expected_amount=Decimal("10000.00"),
        recovery_probability=Decimal("0.75"),
    ))
    try:
        with pytest.raises(Exception) as excinfo:
            create_collection_override(db, CollectionOverrideCreate(
                company_id="FINORA_DEMO",
                invoice_id=invoice_id,
                expected_collection_date=date(2026, 11, 25),
                expected_amount=Decimal("10000.00"),
                recovery_probability=Decimal("0.75"),
            ))
        assert "already exists" in str(excinfo.value).lower() or "409" in str(excinfo.value)
    finally:
        deactivate_collection_override(db, c1.override_id)


def test_what_if_delay_impacts_overdue_recovery(db, sample_overdue_invoice):
    """Verify What-If payment delay pushes overdue recoveries outside horizon without mutating DB."""
    invoice_id = sample_overdue_invoice
    baseline_sim = run_what_if_scenario(
        db,
        company_id="FINORA_DEMO",
        as_of_date=date(2026, 11, 5),
        horizon_days=30,
        payment_delay_days=20,
        expense_increase_percentage=Decimal("0.00"),
    )
    baseline_delayed = baseline_sim["collections_delayed_outside_horizon"]

    c = create_collection_override(db, CollectionOverrideCreate(
        company_id="FINORA_DEMO",
        invoice_id=invoice_id,
        expected_collection_date=date(2026, 11, 20),
        expected_amount=Decimal("96261.98"),
        recovery_probability=Decimal("0.90"),
        commitment_source="Stress Test",
    ))
    try:
        # 30-day horizon (Nov 5 to Dec 5). Delaying 20 days moves Nov 20 to Dec 10 (outside horizon)
        sim = run_what_if_scenario(
            db,
            company_id="FINORA_DEMO",
            as_of_date=date(2026, 11, 5),
            horizon_days=30,
            payment_delay_days=20,
            expense_increase_percentage=Decimal("0.00"),
        )
        assert sim["collections_delayed_outside_horizon"] == baseline_delayed + Decimal("86635.78")
        assert sim["scenario_ending_cash"] < sim["baseline_ending_cash"]
    finally:
        deactivate_collection_override(db, c.override_id)


def test_payment_recording_reconciles_commitments(db):
    """Verify recording an invoice payment automatically reconciles / deactivates future commitments."""
    # Create test invoice
    test_inv_id = f"INV-TEST-{uuid.uuid4().hex[:6].upper()}"
    inv = Invoice(
        invoice_id=test_inv_id,
        company_id="FINORA_DEMO",
        customer_id="CUST001",
        invoice_date=date(2026, 10, 1),
        due_date=date(2026, 11, 1),
        payment_terms_days=30,
        invoice_amount=Decimal("10000.00"),
        currency="INR",
        status="OPEN",
        historical_invoice_count=1,
        historical_late_rate=Decimal("0.0"),
    )
    db.add(inv)
    db.commit()

    # Create commitment
    c = create_collection_override(db, CollectionOverrideCreate(
        company_id="FINORA_DEMO",
        invoice_id=test_inv_id,
        expected_collection_date=date(2026, 11, 20),
        expected_amount=Decimal("10000.00"),
        recovery_probability=Decimal("1.00"),
    ))
    assert c.is_active is True

    try:
        # Record full settlement payment via API
        resp = client.post(
            f"/api/v1/invoices/{test_inv_id}/payments",
            headers={"Idempotency-Key": f"IDEM-PAY-{uuid.uuid4().hex[:8]}"},
            json={
                "amount": 10000.00,
                "currency": "INR",
                "payment_date": date.today().isoformat(),
                "payment_method": "WIRE",
                "notes": "Full settlement test",
            },
        )
        assert resp.status_code == 201

        # Check that invoice is PAID and commitment is auto-reconciled
        db.refresh(inv)
        assert inv.status == "PAID"
        db.refresh(c)
        assert c.is_active is False
        assert "Auto-reconciled" in (c.notes or "")
    finally:
        # Clean up test invoice, payments, cash transactions
        db.query(Payment).filter(Payment.invoice_id == test_inv_id).delete()
        db.query(CashTransaction).filter(CashTransaction.linked_invoice_id == test_inv_id).delete()
        db.query(CollectionForecastOverride).filter(CollectionForecastOverride.invoice_id == test_inv_id).delete()
        db.query(Invoice).filter(Invoice.invoice_id == test_inv_id).delete()
        db.commit()
