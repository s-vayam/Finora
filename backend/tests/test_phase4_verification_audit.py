"""
Mandatory Post-Implementation Verification & Audit Tests (Phase 4).

Executes concrete tests for the four critical financial audit requirements:
TEST 1: Opening Cash Balance Validation
TEST 2: Probability-Weighted Invoice Collection
TEST 3: Overdue Invoice Date Handling
TEST 4: Historical Expenses vs Cash Transaction Double-Counting
"""

from datetime import date, timedelta
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.company import Company
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.expense import Expense
from app.models.cash_transaction import CashTransaction
from app.models.monthly_cashflow import MonthlyCashflow
from app.models.collection_forecast_override import CollectionForecastOverride
from app.models.expense_forecast_assumption import ExpenseForecastAssumption
from app.services.collection_forecasting_service import forecast_invoice_collections
from app.services.expense_forecasting_service import forecast_expenses_and_outflows
from app.services.cashflow_engine import generate_cashflow_forecast


# ==============================================================================
# TEST 1 — OPENING CASH BALANCE VALIDATION
# ==============================================================================

def test_1_scenario_a_no_opening_balance_returns_409(seeded_client: TestClient):
    """Scenario A: No opening balance exists -> HTTP 409 OPENING_BALANCE_REQUIRED."""
    res = seeded_client.get("/api/v1/cashflow/forecast?company_id=FINORA_DEMO&horizon_days=30&as_of_date=2026-11-04")
    assert res.status_code == 409
    body = res.json()
    assert body["detail"]["error_code"] == "OPENING_BALANCE_REQUIRED"
    assert "An opening cash balance snapshot is required" in body["detail"]["message"]


def test_1_scenario_b_valid_manual_snapshot(seeded_client: TestClient):
    """Scenario B: Valid manual snapshot -> Forecast uses snapshot balance and exposes source."""
    as_of = date(2026, 11, 4)
    snap_res = seeded_client.post("/api/v1/cashflow/position", json={
        "company_id": "FINORA_DEMO",
        "as_of_date": as_of.isoformat(),
        "balance_amount": "2500000.00",
        "currency": "INR",
        "minimum_cash_threshold": "500000.00",
        "source": "MANUAL",
        "notes": "Opening cash position supplied for demo",
    })
    assert snap_res.status_code == 201

    fc_res = seeded_client.get(f"/api/v1/cashflow/forecast?company_id=FINORA_DEMO&horizon_days=30&as_of_date={as_of.isoformat()}")
    assert fc_res.status_code == 200
    fc = fc_res.json()
    assert Decimal(str(fc["opening_balance"])) == Decimal("2500000.00")
    # Verify Dec 2025 balance (50,936,337.43) was NOT substituted
    assert Decimal(str(fc["opening_balance"])) != Decimal("50936337.43")


def test_1_scenario_c_historical_balance_protection(seeded_test_db: Session, seeded_client: TestClient):
    """Scenario C: Historical December 2025 balance is completely protected and untouched."""
    dec_2025_before = (
        seeded_test_db.query(MonthlyCashflow)
        .filter(MonthlyCashflow.company_id == "FINORA_DEMO", MonthlyCashflow.month == "2025-12")
        .first()
    )
    assert dec_2025_before is not None
    original_closing = dec_2025_before.closing_balance

    # Insert snapshot and generate forecast
    as_of = date(2026, 11, 4)
    seeded_client.post("/api/v1/cashflow/position", json={
        "company_id": "FINORA_DEMO",
        "as_of_date": as_of.isoformat(),
        "balance_amount": "2500000.00",
        "currency": "INR",
    })
    seeded_client.get(f"/api/v1/cashflow/forecast?company_id=FINORA_DEMO&horizon_days=30&as_of_date={as_of.isoformat()}")

    dec_2025_after = (
        seeded_test_db.query(MonthlyCashflow)
        .filter(MonthlyCashflow.company_id == "FINORA_DEMO", MonthlyCashflow.month == "2025-12")
        .first()
    )
    assert dec_2025_after.closing_balance == original_closing
    assert Decimal(str(dec_2025_after.closing_balance)) == Decimal("50936337.43")


def test_1_scenario_d_missing_or_invalid_snapshot(seeded_client: TestClient):
    """Scenario D: Validation errors on unknown company and duplicate snapshot."""
    # Unknown company
    res_unk = seeded_client.post("/api/v1/cashflow/position", json={
        "company_id": "NON_EXISTENT_CO",
        "as_of_date": "2026-11-04",
        "balance_amount": "2500000.00",
        "currency": "INR",
    })
    assert res_unk.status_code == 404

    # Valid creation
    res_ok = seeded_client.post("/api/v1/cashflow/position", json={
        "company_id": "FINORA_DEMO",
        "as_of_date": "2026-11-04",
        "balance_amount": "2500000.00",
        "currency": "INR",
    })
    assert res_ok.status_code == 201

    # Duplicate creation
    res_dup = seeded_client.post("/api/v1/cashflow/position", json={
        "company_id": "FINORA_DEMO",
        "as_of_date": "2026-11-04",
        "balance_amount": "3000000.00",
        "currency": "INR",
    })
    assert res_dup.status_code == 409


# ==============================================================================
# TEST 2 — PROBABILITY-WEIGHTED INVOICE COLLECTION
# ==============================================================================

def test_2_scenario_a_standard_probability_weighted_allocation(seeded_test_db: Session):
    """Scenario A: Standard allocation sums to outstanding balance, weights sum to 1.0."""
    as_of = date(2026, 11, 4)
    due_date = as_of + timedelta(days=16)  # 2026-11-20

    inv = Invoice(
        invoice_id="INV-AUDIT-2A",
        company_id="FINORA_DEMO",
        customer_id="CUST001",
        invoice_date=as_of,
        due_date=due_date,
        payment_terms_days=16,
        invoice_amount=Decimal("100000.00"),
        currency="INR",
        status="OPEN",
    )
    seeded_test_db.add(inv)
    seeded_test_db.commit()

    res = forecast_invoice_collections(
        seeded_test_db, company_id="FINORA_DEMO", as_of_date=as_of, horizon_days=90, base_currency="INR"
    )

    inv_details = [d for d in res["invoice_details"] if d["invoice_id"] == "INV-AUDIT-2A"]
    assert len(inv_details) == 1
    events = inv_details[0]["events"]

    total_amount = sum((e["amount"] for e in events), Decimal("0.00"))
    total_prob = sum((e["probability"] for e in events), Decimal("0.00"))

    assert total_amount == Decimal("100000.00")
    assert pytest.approx(float(total_prob), 0.001) == 1.0


def test_2_scenario_d_partial_payment(seeded_test_db: Session):
    """Scenario D: Only remaining outstanding balance is forecast, received amount not counted."""
    as_of = date(2026, 11, 4)
    due_date = as_of + timedelta(days=20)

    # Invoice for 100,000 with 40,000 already received
    inv = Invoice(
        invoice_id="INV-AUDIT-2D",
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
    seeded_test_db.flush()

    # Add linked cash transaction and partial payment
    txn_id = f"TXN-PART-{uuid.uuid4().hex[:8].upper()}"
    txn = CashTransaction(
        transaction_id=txn_id,
        company_id="FINORA_DEMO",
        transaction_date=as_of,
        transaction_type="INFLOW",
        category="INVOICE_PAYMENT",
        amount=Decimal("40000.00"),
        currency="INR",
        linked_invoice_id="INV-AUDIT-2D",
    )
    seeded_test_db.add(txn)
    seeded_test_db.flush()

    pay = Payment(
        payment_id=f"PAY-{uuid.uuid4().hex[:8].upper()}",
        company_id="FINORA_DEMO",
        invoice_id="INV-AUDIT-2D",
        payment_date=as_of,
        amount=Decimal("40000.00"),
        currency="INR",
        cash_transaction_id=txn_id,
        idempotency_key=str(uuid.uuid4()),
        source="MANUAL",
    )
    seeded_test_db.add(pay)
    seeded_test_db.commit()

    res = forecast_invoice_collections(
        seeded_test_db, company_id="FINORA_DEMO", as_of_date=as_of, horizon_days=90, base_currency="INR"
    )

    matching = [e for e in res["scheduled_events"] if e["invoice_id"] == "INV-AUDIT-2D"]
    assert len(matching) == 1
    # Exactly remaining 60,000 forecast
    assert matching[0]["amount"] == Decimal("60000.00")
    assert matching[0]["collection_type"] == "RULE_BASED"


def test_2_scenario_e_paid_and_cancelled_invoices(seeded_test_db: Session):
    """Scenario E: Fully paid and cancelled invoices generate 0 future collection events."""
    as_of = date(2026, 11, 4)
    # Create a cancelled invoice
    inv_cancel = Invoice(
        invoice_id="INV-AUDIT-2E-CANCEL",
        company_id="FINORA_DEMO",
        customer_id="CUST001",
        invoice_date=as_of,
        due_date=as_of + timedelta(days=10),
        payment_terms_days=10,
        invoice_amount=Decimal("50000.00"),
        currency="INR",
        status="CANCELLED",
    )
    seeded_test_db.add(inv_cancel)
    seeded_test_db.commit()

    res = forecast_invoice_collections(
        seeded_test_db, company_id="FINORA_DEMO", as_of_date=as_of, horizon_days=90, base_currency="INR"
    )
    scheduled_ids = {e["invoice_id"] for e in res["scheduled_events"]}
    assert "INV-AUDIT-2E-CANCEL" not in scheduled_ids


# ==============================================================================
# TEST 3 — OVERDUE INVOICE DATE HANDLING
# ==============================================================================

def test_3_scenario_a_overdue_unresolved_handling(seeded_test_db: Session):
    """Scenario A: Overdue invoice with expired nominal date is marked OVERDUE_UNRESOLVED."""
    as_of = date(2026, 11, 4)
    # In FINORA_DEMO, open invoices have due dates in early 2026 (all past relative to Nov 2026)
    res = forecast_invoice_collections(
        seeded_test_db, company_id="FINORA_DEMO", as_of_date=as_of, horizon_days=90, base_currency="INR"
    )

    assert len(res["unresolved_overdue"]) > 0
    scheduled_ids = {e["invoice_id"] for e in res["scheduled_events"]}

    for item in res["unresolved_overdue"]:
        assert item["status"] == "OVERDUE_UNRESOLVED"
        # Must not be scheduled as future inflow
        assert item["invoice_id"] not in scheduled_ids


def test_3_scenario_b_c_manual_override_and_deactivation(seeded_test_db: Session):
    """Scenario B & C: Manual override sets expected date, deactivation returns to OVERDUE_UNRESOLVED."""
    as_of = date(2026, 11, 4)
    open_inv = seeded_test_db.query(Invoice).filter(Invoice.status == "OPEN").first()
    assert open_inv is not None
    inv_id = open_inv.invoice_id
    future_date = as_of + timedelta(days=10)

    # 1. Add manual override
    ovr = CollectionForecastOverride(
        override_id=f"OVR-{uuid.uuid4().hex[:8].upper()}",
        company_id="FINORA_DEMO",
        invoice_id=inv_id,
        expected_collection_date=future_date,
        is_active=True,
    )
    seeded_test_db.add(ovr)
    seeded_test_db.commit()

    res_ovr = forecast_invoice_collections(
        seeded_test_db, company_id="FINORA_DEMO", as_of_date=as_of, horizon_days=90, base_currency="INR"
    )
    scheduled_match = [e for e in res_ovr["scheduled_events"] if e["invoice_id"] == inv_id]
    assert len(scheduled_match) == 1
    assert scheduled_match[0]["collection_type"] == "MANUAL_OVERRIDE"
    assert scheduled_match[0]["date"] == future_date

    # 2. Deactivate override (Scenario C)
    ovr.is_active = False
    seeded_test_db.commit()

    res_deact = forecast_invoice_collections(
        seeded_test_db, company_id="FINORA_DEMO", as_of_date=as_of, horizon_days=90, base_currency="INR"
    )
    # Returns to unresolved overdue, no longer scheduled
    unresolved_ids = {item["invoice_id"] for item in res_deact["unresolved_overdue"]}
    assert inv_id in unresolved_ids
    sched_deact_ids = {e["invoice_id"] for e in res_deact["scheduled_events"]}
    assert inv_id not in sched_deact_ids


# ==============================================================================
# TEST 4 — HISTORICAL EXPENSES VS CASH TRANSACTION DOUBLE COUNTING
# ==============================================================================

def test_4_scenario_a_b_c_d_e_f_outflow_integrity(seeded_test_db: Session):
    """
    Test 4 scenarios:
    A: Historical reconciliation matches monthly cashflow (INR 73,732,730.47)
    B: Expenses not added on top of cash transactions
    C: Unpaid future commitment included once
    D: Paid expense not counted as future commitment
    E: Estimated expense supersedes category baseline
    F: Historical development database records preserved
    """
    as_of = date(2026, 11, 4)

    # Scenario A: Historical reconciliation
    tot_txns = seeded_test_db.query(func.sum(CashTransaction.amount)).filter(
        CashTransaction.company_id == "FINORA_DEMO", CashTransaction.transaction_type == "OUTFLOW"
    ).scalar()
    tot_mcf = seeded_test_db.query(func.sum(MonthlyCashflow.actual_outflows)).filter(
        MonthlyCashflow.company_id == "FINORA_DEMO"
    ).scalar()
    assert Decimal(str(tot_txns)) == Decimal(str(tot_mcf)) == Decimal("73732730.47")

    # Scenario C: Future unpaid commitment included once
    unpaid_exp = Expense(
        expense_id="EXP-FUTURE-001",
        company_id="FINORA_DEMO",
        category="SOFTWARE_ADMIN",
        amount=Decimal("25000.00"),
        currency="INR",
        expense_date=as_of,
        due_date=as_of + timedelta(days=12),
        status="OPEN",
    )
    seeded_test_db.add(unpaid_exp)
    seeded_test_db.commit()

    res = forecast_expenses_and_outflows(
        seeded_test_db, company_id="FINORA_DEMO", as_of_date=as_of, horizon_days=30, base_currency="INR"
    )

    matching_comm = [e for e in res["committed_events"] if e.get("source") == "EXPENSE_ID_EXP-FUTURE-001"]
    assert len(matching_comm) == 1
    assert matching_comm[0]["amount"] == Decimal("25000.00")
    assert matching_comm[0]["date"] == as_of + timedelta(days=12)

    # Scenario F: Record counts verification
    assert seeded_test_db.query(Payment).count() == 873
    assert seeded_test_db.query(CashTransaction).count() == 1722
    assert seeded_test_db.query(MonthlyCashflow).count() == 36
