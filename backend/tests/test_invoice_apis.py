from datetime import date, timedelta
from fastapi.testclient import TestClient

def test_invoice_create_and_retrieve(seeded_client: TestClient):
    """Test invoice creation, unique ID generation, and detail retrieval."""
    today = date.today()
    due = today + timedelta(days=30)

    payload = {
        "company_id": "FINORA_DEMO",
        "customer_id": "CUST001",
        "invoice_date": today.isoformat(),
        "due_date": due.isoformat(),
        "payment_terms_days": 30,
        "invoice_amount": "50000.00",
        "currency": "INR",
    }
    res = seeded_client.post("/api/v1/invoices", json=payload)
    assert res.status_code == 201
    created = res.json()
    assert created["status"] == "OPEN"
    assert created["payment_status"] == "UNPAID"
    assert float(created["outstanding_amount"]) == 50000.0
    assert float(created["amount_paid"]) == 0.0
    inv_id = created["invoice_id"]

    # Retrieve detail view
    res_detail = seeded_client.get(f"/api/v1/invoices/{inv_id}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["invoice_id"] == inv_id
    assert detail["customer_id"] == "CUST001"
    assert detail["customer_name"] is not None
    assert detail["payments"] == []

def test_invoice_update_rules(seeded_client: TestClient):
    """Test safe update rules and validations on invoices."""
    today = date.today()
    due = today + timedelta(days=45)

    # 1. Create open invoice
    res = seeded_client.post("/api/v1/invoices", json={
        "company_id": "FINORA_DEMO",
        "customer_id": "CUST002",
        "invoice_date": today.isoformat(),
        "due_date": due.isoformat(),
        "payment_terms_days": 45,
        "invoice_amount": "80000.00",
        "currency": "INR",
    })
    assert res.status_code == 201
    inv_id = res.json()["invoice_id"]

    # 2. Update due date and terms
    new_due = today + timedelta(days=60)
    res_patch = seeded_client.patch(f"/api/v1/invoices/{inv_id}", json={
        "due_date": new_due.isoformat(),
        "payment_terms_days": 60,
        "invoice_amount": "85000.00",
    })
    assert res_patch.status_code == 200
    assert float(res_patch.json()["invoice_amount"]) == 85000.0
    assert res_patch.json()["due_date"] == new_due.isoformat()

    # 3. Invalid due date preceding invoice date
    bad_due = today - timedelta(days=1)
    res_bad_date = seeded_client.patch(f"/api/v1/invoices/{inv_id}", json={
        "due_date": bad_due.isoformat(),
    })
    assert res_bad_date.status_code == 422

def test_invoice_cancellation_rules(seeded_client: TestClient):
    """Test invoice cancellation succeeds with 0 payments and is rejected when payments exist."""
    today = date.today()
    # Create open invoice
    res = seeded_client.post("/api/v1/invoices", json={
        "company_id": "FINORA_DEMO",
        "customer_id": "CUST003",
        "invoice_date": today.isoformat(),
        "due_date": (today + timedelta(days=30)).isoformat(),
        "payment_terms_days": 30,
        "invoice_amount": "20000.00",
        "currency": "INR",
    })
    inv_id = res.json()["invoice_id"]

    # Cancel invoice (0 payments)
    res_cancel = seeded_client.post(f"/api/v1/invoices/{inv_id}/cancel")
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "CANCELLED"

    # Try cancelling a paid invoice with recorded payments -> 409 Conflict
    res_paid_cancel = seeded_client.post("/api/v1/invoices/INV-000022/cancel")
    assert res_paid_cancel.status_code == 409
    assert "recorded payments" in res_paid_cancel.json()["detail"].lower()
