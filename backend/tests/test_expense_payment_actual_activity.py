"""
Pytest Test Suite for Finora Expense Payment Management & Actual Financial Activity:
- Expense payment recording (full & partial)
- Status transitions (UNPAID -> PARTIALLY_PAID -> PAID)
- Idempotency key enforcement
- Overpayment prevention (HTTP 409)
- Atomic CashTransaction(OUTFLOW) creation
- Cashflow Forecast Actual Activity reconciliation
- Formula verification: Closing Balance = Opening + Actual Inflows - Actual Outflows
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.expense import Expense
from app.models.expense_payment import ExpensePayment
from app.models.cash_transaction import CashTransaction
from app.models.cash_balance_snapshot import CashBalanceSnapshot
from app.services.cashflow_engine import generate_cashflow_forecast

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_expense(db):
    exp_id = f"EXP-TEST-{uuid.uuid4().hex[:6].upper()}"
    exp = Expense(
        expense_id=exp_id,
        company_id="FINORA_DEMO",
        category="MARKETING",
        amount=Decimal("50000.00"),
        currency="INR",
        expense_date=date(2026, 11, 1),
        due_date=date(2026, 11, 20),
        status="OPEN",
        amount_paid=Decimal("0.00"),
    )
    db.add(exp)
    db.commit()
    try:
        yield exp_id
    finally:
        # Cleanup
        db.query(ExpensePayment).filter(ExpensePayment.expense_id == exp_id).delete()
        db.query(CashTransaction).filter(CashTransaction.linked_expense_id == exp_id).delete()
        db.query(Expense).filter(Expense.expense_id == exp_id).delete()
        db.commit()


def test_expense_partial_and_full_payment_lifecycle(db, test_expense):
    """Test partial disbursement followed by full settlement, verifying balances and status."""
    exp_id = test_expense

    # 1. First partial payment: ₹20,000
    idem_key1 = f"IDEM-EXP-{uuid.uuid4().hex[:8]}"
    resp1 = client.post(
        f"/api/v1/expenses/{exp_id}/payments",
        headers={"Idempotency-Key": idem_key1},
        json={
            "amount": 20000.00,
            "currency": "INR",
            "payment_date": date.today().isoformat(),
            "payment_method": "BANK_TRANSFER",
            "reference_number": "REF-PARTIAL-1",
            "notes": "Partial disbursement 1",
        },
    )
    assert resp1.status_code == 201, resp1.text
    data1 = resp1.json()
    assert data1["expense_id"] == exp_id
    assert Decimal(str(data1["amount"])) == Decimal("20000.00")
    assert data1["cash_transaction_id"].startswith("TXN-OUT-")

    # Verify Expense state
    exp = db.query(Expense).filter(Expense.expense_id == exp_id).first()
    assert Decimal(str(exp.amount_paid)) == Decimal("20000.00")
    assert Decimal(str(exp.outstanding_amount)) == Decimal("30000.00")
    assert exp.payment_status == "PARTIALLY_PAID"

    # Verify CashTransaction created
    tx1 = db.query(CashTransaction).filter(CashTransaction.transaction_id == data1["cash_transaction_id"]).first()
    assert tx1 is not None
    assert tx1.transaction_type == "OUTFLOW"
    assert tx1.linked_expense_id == exp_id
    assert Decimal(str(tx1.amount)) == Decimal("20000.00")

    # 2. Overpayment attempt: ₹35,000 (when outstanding is ₹30,000) -> HTTP 409
    resp_over = client.post(
        f"/api/v1/expenses/{exp_id}/payments",
        headers={"Idempotency-Key": f"IDEM-EXP-{uuid.uuid4().hex[:8]}"},
        json={
            "amount": 35000.00,
            "currency": "INR",
            "payment_date": date.today().isoformat(),
            "payment_method": "BANK_TRANSFER",
        },
    )
    assert resp_over.status_code == 409
    assert "exceeds" in resp_over.json()["detail"].lower()

    # 3. Idempotent replay of first payment
    resp_replay = client.post(
        f"/api/v1/expenses/{exp_id}/payments",
        headers={"Idempotency-Key": idem_key1},
        json={
            "amount": 20000.00,
            "currency": "INR",
            "payment_date": date.today().isoformat(),
            "payment_method": "BANK_TRANSFER",
            "reference_number": "REF-PARTIAL-1",
            "notes": "Partial disbursement 1",
        },
    )
    assert resp_replay.status_code == 201
    assert resp_replay.json()["payment_id"] == data1["payment_id"]

    # 4. Final settlement payment: ₹30,000
    idem_key2 = f"IDEM-EXP-{uuid.uuid4().hex[:8]}"
    resp2 = client.post(
        f"/api/v1/expenses/{exp_id}/payments",
        headers={"Idempotency-Key": idem_key2},
        json={
            "amount": 30000.00,
            "currency": "INR",
            "payment_date": date.today().isoformat(),
            "payment_method": "BANK_TRANSFER",
            "reference_number": "REF-FINAL-2",
            "notes": "Final settlement",
        },
    )
    assert resp2.status_code == 201
    db.refresh(exp)
    assert Decimal(str(exp.amount_paid)) == Decimal("50000.00")
    assert Decimal(str(exp.outstanding_amount)) == Decimal("0.00")
    assert exp.payment_status == "PAID"
    assert exp.status == "PAID"


def test_actual_financial_activity_reconciliation(db, test_expense):
    """
    Verify Actual Financial Activity correctly captures inflows & outflows,
    updates actual closing balance using the formula:
    Closing Balance = Opening Balance + Actual Inflows - Actual Outflows
    """
    exp_id = test_expense

    # Ensure an active cash position exists
    pos = (
        db.query(CashBalanceSnapshot)
        .filter(CashBalanceSnapshot.company_id == "FINORA_DEMO")
        .order_by(CashBalanceSnapshot.as_of_date.desc(), CashBalanceSnapshot.created_at.desc())
        .first()
    )
    assert pos is not None
    as_of = pos.as_of_date
    open_bal = Decimal(str(pos.balance_amount))

    # Record an expense payment on today (as_of <= today <= as_of + 30)
    idem_key = f"IDEM-EXP-{uuid.uuid4().hex[:8]}"
    resp = client.post(
        f"/api/v1/expenses/{exp_id}/payments",
        headers={"Idempotency-Key": idem_key},
        json={
            "amount": 15000.00,
            "currency": "INR",
            "payment_date": date.today().isoformat(),
            "payment_method": "ACH",
            "reference_number": "REF-ACTUAL-TEST",
        },
    )
    assert resp.status_code == 201

    # Run cashflow forecast
    fc = generate_cashflow_forecast(db, "FINORA_DEMO", as_of, 30, "INR", persist=False)
    summary = fc["summary"]

    actual_inflows = summary["actual_inflows"]
    actual_outflows = summary["actual_outflows"]
    actual_closing = summary["actual_closing_balance"]

    # Verify formula Closing Balance = Opening Balance + Actual Inflows - Actual Outflows
    expected_closing = open_bal + actual_inflows - actual_outflows
    assert actual_closing == expected_closing

    # Verify transactions feed contains our expense payment
    actual_txns = fc["actual_transactions"]
    matching_tx = [t for t in actual_txns if t.get("linked_expense_id") == exp_id]
    assert len(matching_tx) == 1
    assert matching_tx[0]["transaction_type"] == "OUTFLOW"
    assert Decimal(str(matching_tx[0]["amount"])) == Decimal("15000.00")
    assert matching_tx[0]["reference_id"] == exp_id
