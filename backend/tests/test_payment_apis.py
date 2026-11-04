from datetime import date, timedelta
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient

def test_full_and_partial_payments_lifecycle(seeded_client: TestClient):
    """
    Explicitly test scenarios:
    1. First partial payment
    2. Second partial payment
    3. Invoice becomes PAID after final installment
    4. Overpayment rejected
    5. Payment and cash transaction amount & currency consistency
    """
    today = date.today()
    # 1. Create an invoice for 100,000 INR
    inv_res = seeded_client.post("/api/v1/invoices", json={
        "company_id": "FINORA_DEMO",
        "customer_id": "CUST001",
        "invoice_date": today.isoformat(),
        "due_date": (today + timedelta(days=30)).isoformat(),
        "payment_terms_days": 30,
        "invoice_amount": "100000.00",
        "currency": "INR",
    })
    assert inv_res.status_code == 201
    inv_id = inv_res.json()["invoice_id"]

    # 2. First partial payment: 40,000 INR
    pay1_key = str(uuid.uuid4())
    pay1_res = seeded_client.post(
        f"/api/v1/invoices/{inv_id}/payments",
        headers={"Idempotency-Key": pay1_key},
        json={
            "amount": "40000.00",
            "currency": "INR",
            "payment_date": today.isoformat(),
            "payment_method": "BANK_TRANSFER",
            "reference_number": "REF-PARTIAL-1",
            "notes": "First installment",
        },
    )
    assert pay1_res.status_code == 201
    pay1_data = pay1_res.json()
    assert float(pay1_data["amount"]) == 40000.0
    assert pay1_data["currency"] == "INR"
    assert pay1_data["cash_transaction_id"] is not None

    # Check invoice status is PARTIALLY_PAID
    inv_check1 = seeded_client.get(f"/api/v1/invoices/{inv_id}").json()
    assert inv_check1["payment_status"] == "PARTIALLY_PAID"
    assert float(inv_check1["amount_paid"]) == 40000.0
    assert float(inv_check1["outstanding_amount"]) == 60000.0

    # 3. Overpayment rejected: try to pay 70,000 when only 60,000 remains
    overpay_res = seeded_client.post(
        f"/api/v1/invoices/{inv_id}/payments",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "amount": "70000.00",
            "currency": "INR",
            "payment_date": today.isoformat(),
        },
    )
    assert overpay_res.status_code == 409
    assert "exceeds" in overpay_res.json()["detail"].lower()

    # 4. Second partial payment: 35,000 INR
    pay2_key = str(uuid.uuid4())
    pay2_res = seeded_client.post(
        f"/api/v1/invoices/{inv_id}/payments",
        headers={"Idempotency-Key": pay2_key},
        json={
            "amount": "35000.00",
            "currency": "INR",
            "payment_date": today.isoformat(),
            "reference_number": "REF-PARTIAL-2",
        },
    )
    assert pay2_res.status_code == 201

    inv_check2 = seeded_client.get(f"/api/v1/invoices/{inv_id}").json()
    assert inv_check2["payment_status"] == "PARTIALLY_PAID"
    assert float(inv_check2["amount_paid"]) == 75000.0
    assert float(inv_check2["outstanding_amount"]) == 25000.0

    # 5. Final installment: 25,000 INR -> Invoice becomes PAID
    pay3_key = str(uuid.uuid4())
    pay3_res = seeded_client.post(
        f"/api/v1/invoices/{inv_id}/payments",
        headers={"Idempotency-Key": pay3_key},
        json={
            "amount": "25000.00",
            "currency": "INR",
            "payment_date": today.isoformat(),
            "reference_number": "REF-FINAL",
        },
    )
    assert pay3_res.status_code == 201

    inv_check3 = seeded_client.get(f"/api/v1/invoices/{inv_id}").json()
    assert inv_check3["payment_status"] == "PAID"
    assert inv_check3["due_status"] == "SETTLED"
    assert float(inv_check3["amount_paid"]) == 100000.0
    assert float(inv_check3["outstanding_amount"]) == 0.0

    # 6. Verify payments history (3 payments in chronological order)
    history_res = seeded_client.get(f"/api/v1/invoices/{inv_id}/payments")
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) == 3
    assert float(history[0]["amount"]) == 40000.0
    assert float(history[1]["amount"]) == 35000.0
    assert float(history[2]["amount"]) == 25000.0

def test_full_single_payment(seeded_client: TestClient):
    """Test full single payment settling entire invoice at once."""
    today = date.today()
    inv_res = seeded_client.post("/api/v1/invoices", json={
        "company_id": "FINORA_DEMO",
        "customer_id": "CUST002",
        "invoice_date": today.isoformat(),
        "due_date": (today + timedelta(days=15)).isoformat(),
        "payment_terms_days": 15,
        "invoice_amount": "50000.00",
        "currency": "INR",
    })
    inv_id = inv_res.json()["invoice_id"]

    pay_res = seeded_client.post(
        f"/api/v1/invoices/{inv_id}/payments",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "amount": "50000.00",
            "currency": "INR",
            "payment_date": today.isoformat(),
            "payment_method": "NEFT",
            "reference_number": "FULL-PAY-1",
        },
    )
    assert pay_res.status_code == 201

    inv = seeded_client.get(f"/api/v1/invoices/{inv_id}").json()
    assert inv["payment_status"] == "PAID"
    assert inv["due_status"] == "SETTLED"
    assert float(inv["outstanding_amount"]) == 0.0

def test_payment_validations_and_rejections(seeded_client: TestClient):
    """Test wrong currency, cancelled invoice, past/future dates, invalid idempotency."""
    today = date.today()
    inv_res = seeded_client.post("/api/v1/invoices", json={
        "company_id": "FINORA_DEMO",
        "customer_id": "CUST003",
        "invoice_date": today.isoformat(),
        "due_date": (today + timedelta(days=30)).isoformat(),
        "payment_terms_days": 30,
        "invoice_amount": "30000.00",
        "currency": "INR",
    })
    inv_id = inv_res.json()["invoice_id"]

    # 1. Wrong currency rejected (409)
    res_wrong_curr = seeded_client.post(
        f"/api/v1/invoices/{inv_id}/payments",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "amount": "10000.00",
            "currency": "USD",
            "payment_date": today.isoformat(),
        },
    )
    assert res_wrong_curr.status_code == 409

    # 2. Payment date precedes invoice date rejected (422)
    past_date = today - timedelta(days=5)
    res_past = seeded_client.post(
        f"/api/v1/invoices/{inv_id}/payments",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "amount": "10000.00",
            "currency": "INR",
            "payment_date": past_date.isoformat(),
        },
    )
    assert res_past.status_code == 422

    # 3. Future payment date rejected (422)
    future_date = today + timedelta(days=2)
    res_future = seeded_client.post(
        f"/api/v1/invoices/{inv_id}/payments",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "amount": "10000.00",
            "currency": "INR",
            "payment_date": future_date.isoformat(),
        },
    )
    assert res_future.status_code == 422

    # 4. Payment on cancelled invoice rejected (409)
    cancel_res = seeded_client.post(f"/api/v1/invoices/{inv_id}/cancel")
    assert cancel_res.status_code == 200

    res_cancel_pay = seeded_client.post(
        f"/api/v1/invoices/{inv_id}/payments",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "amount": "10000.00",
            "currency": "INR",
            "payment_date": today.isoformat(),
        },
    )
    assert res_cancel_pay.status_code == 409

def test_idempotency_behavior(seeded_client: TestClient):
    """Test duplicate request replay vs conflicting payload with same key."""
    today = date.today()
    inv_res = seeded_client.post("/api/v1/invoices", json={
        "company_id": "FINORA_DEMO",
        "customer_id": "CUST004",
        "invoice_date": today.isoformat(),
        "due_date": (today + timedelta(days=30)).isoformat(),
        "payment_terms_days": 30,
        "invoice_amount": "45000.00",
        "currency": "INR",
    })
    inv_id = inv_res.json()["invoice_id"]

    shared_key = str(uuid.uuid4())
    payload = {
        "amount": "15000.00",
        "currency": "INR",
        "payment_date": today.isoformat(),
        "notes": "First attempt",
    }

    # Initial request -> 201 Created
    res1 = seeded_client.post(
        f"/api/v1/invoices/{inv_id}/payments",
        headers={"Idempotency-Key": shared_key},
        json=payload,
    )
    assert res1.status_code == 201
    pay_id1 = res1.json()["payment_id"]

    # Exact replay with same key -> Returns 200/201 with SAME payment_id
    res2 = seeded_client.post(
        f"/api/v1/invoices/{inv_id}/payments",
        headers={"Idempotency-Key": shared_key},
        json=payload,
    )
    assert res2.status_code in (200, 201)
    assert res2.json()["payment_id"] == pay_id1

    # Conflicting payload with same key -> 409 Conflict
    conflicting_payload = {
        "amount": "20000.00",  # Different amount!
        "currency": "INR",
        "payment_date": today.isoformat(),
    }
    res_conflict = seeded_client.post(
        f"/api/v1/invoices/{inv_id}/payments",
        headers={"Idempotency-Key": shared_key},
        json=conflicting_payload,
    )
    assert res_conflict.status_code == 409

def test_payments_listing_and_detail(seeded_client: TestClient):
    """Test GET /payments and GET /payments/{payment_id}."""
    # List payments (should contain backfilled records)
    res_list = seeded_client.get("/api/v1/payments?page=1&page_size=10")
    assert res_list.status_code == 200
    data = res_list.json()
    assert data["total"] >= 873
    assert len(data["items"]) == 10
    first_payment_id = data["items"][0]["payment_id"]

    # Detail view of a payment
    res_detail = seeded_client.get(f"/api/v1/payments/{first_payment_id}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["payment"]["payment_id"] == first_payment_id
    assert detail["invoice_id"] is not None
    assert float(detail["invoice_amount"]) > 0

    # 404 for unknown payment
    res_404 = seeded_client.get("/api/v1/payments/NON_EXISTENT_PAY_ID")
    assert res_404.status_code == 404
