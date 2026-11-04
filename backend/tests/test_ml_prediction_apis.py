"""
Tests for ML Payment Risk FastAPI Endpoints and Persistence (Stage 3E).
"""

from datetime import date, timedelta
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient


def test_ml_status_endpoint(client: TestClient):
    """Test GET /api/v1/ml/payment-risk/status."""
    response = client.get("/api/v1/ml/payment-risk/status")
    assert response.status_code == 200
    data = response.json()
    assert data["is_loaded"] is True
    assert data["model_version"] == "v1.0.0"
    assert "RandomForest" in data["classifier_type"]
    assert "Ridge" in data["regressor_type"]
    assert data["optimal_threshold"] > 0


def test_ml_metrics_endpoint(client: TestClient):
    """Test GET /api/v1/ml/payment-risk/metrics."""
    response = client.get("/api/v1/ml/payment-risk/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["model_version"] == "v1.0.0"
    assert "classification_test_metrics" in data
    assert "regression_test_metrics" in data
    assert "feature_importance" in data
    assert data["classification_test_metrics"]["roc_auc"] >= 0.70
    assert data["regression_test_metrics"]["mae"] < 10.0


def test_predict_payment_risk_on_open_invoice(seeded_client: TestClient):
    """Test POST /api/v1/predict/payment-risk on an open, unpaid invoice."""
    # Find an open invoice
    invoices_res = seeded_client.get("/api/v1/invoices?status=OPEN&page_size=1")
    assert invoices_res.status_code == 200
    items = invoices_res.json()["items"]
    assert len(items) > 0
    open_inv = items[0]
    inv_id = open_inv["invoice_id"]

    # Generate prediction
    pred_res = seeded_client.post(
        "/api/v1/predict/payment-risk",
        json={"invoice_id": inv_id},
    )
    assert pred_res.status_code == 201
    pred = pred_res.json()

    assert pred["invoice_id"] == inv_id
    assert 0.0 <= pred["predicted_late_probability"] <= 1.0
    assert pred["risk_category"] in ["LOW", "MEDIUM", "HIGH"]
    assert pred["predicted_delay_days"] >= 0.0
    assert pred["expected_delay_days"] >= 0.0
    assert "estimated_payment_date" in pred
    assert isinstance(pred["features_snapshot"], dict)
    assert "invoice_amount" in pred["features_snapshot"]
    assert "cust_prev_invoice_count" in pred["features_snapshot"]

    # Verify GET latest endpoint
    latest_res = seeded_client.get(f"/api/v1/invoices/{inv_id}/payment-risk/latest")
    assert latest_res.status_code == 200
    latest = latest_res.json()
    assert latest["id"] == pred["id"]
    assert latest["predicted_late_probability"] == pred["predicted_late_probability"]

    # Verify GET history endpoint
    history_res = seeded_client.get(f"/api/v1/invoices/{inv_id}/payment-risk/history")
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) == 1
    assert history[0]["id"] == pred["id"]

    # Generate second prediction to verify history tracking
    pred2_res = seeded_client.post(
        "/api/v1/predict/payment-risk",
        json={"invoice_id": inv_id},
    )
    assert pred2_res.status_code == 201
    pred2 = pred2_res.json()
    assert pred2["id"] > pred["id"]

    history2_res = seeded_client.get(f"/api/v1/invoices/{inv_id}/payment-risk/history")
    assert len(history2_res.json()) == 2


def test_prediction_ineligibility_and_rejections(seeded_client: TestClient):
    """
    Test eligibility enforcement:
    - 404 for non-existent invoice
    - 409 for PAID invoice
    - 409 for CANCELLED invoice
    - 409 for PARTIALLY_PAID invoice
    """
    # 1. Non-existent invoice -> 404
    res_404 = seeded_client.post(
        "/api/v1/predict/payment-risk",
        json={"invoice_id": "NON_EXISTENT_INV_123"},
    )
    assert res_404.status_code == 404

    # 2. Paid invoice -> 409
    paid_invs = seeded_client.get("/api/v1/invoices?status=PAID&page_size=1").json()["items"]
    assert len(paid_invs) > 0
    paid_id = paid_invs[0]["invoice_id"]
    res_paid = seeded_client.post(
        "/api/v1/predict/payment-risk",
        json={"invoice_id": paid_id},
    )
    assert res_paid.status_code == 409
    assert "already PAID" in res_paid.json()["detail"] or "paid in full" in res_paid.json()["detail"]

    # 3. Cancelled invoice -> 409
    # Create an invoice and cancel it
    today = date.today()
    new_inv = seeded_client.post("/api/v1/invoices", json={
        "company_id": "FINORA_DEMO",
        "customer_id": "CUST001",
        "invoice_date": today.isoformat(),
        "due_date": (today + timedelta(days=30)).isoformat(),
        "payment_terms_days": 30,
        "invoice_amount": "50000.00",
        "currency": "INR",
    }).json()
    cancel_id = new_inv["invoice_id"]
    seeded_client.post(f"/api/v1/invoices/{cancel_id}/cancel")

    res_cancel = seeded_client.post(
        "/api/v1/predict/payment-risk",
        json={"invoice_id": cancel_id},
    )
    assert res_cancel.status_code == 409
    assert "CANCELLED" in res_cancel.json()["detail"]

    # 4. Partially paid invoice -> 409
    partial_inv = seeded_client.post("/api/v1/invoices", json={
        "company_id": "FINORA_DEMO",
        "customer_id": "CUST001",
        "invoice_date": today.isoformat(),
        "due_date": (today + timedelta(days=30)).isoformat(),
        "payment_terms_days": 30,
        "invoice_amount": "80000.00",
        "currency": "INR",
    }).json()
    part_id = partial_inv["invoice_id"]

    # Record partial payment
    seeded_client.post(
        f"/api/v1/invoices/{part_id}/payments",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "amount": "25000.00",
            "currency": "INR",
            "payment_date": today.isoformat(),
            "payment_method": "BANK_TRANSFER",
        },
    )

    res_partial = seeded_client.post(
        "/api/v1/predict/payment-risk",
        json={"invoice_id": part_id},
    )
    assert res_partial.status_code == 409
    assert "PARTIALLY_PAID" in res_partial.json()["detail"]


def test_latest_prediction_not_found(seeded_client: TestClient):
    """Test 404 when querying latest prediction on an invoice without any predictions."""
    today = date.today()
    new_inv = seeded_client.post("/api/v1/invoices", json={
        "company_id": "FINORA_DEMO",
        "customer_id": "CUST001",
        "invoice_date": today.isoformat(),
        "due_date": (today + timedelta(days=30)).isoformat(),
        "payment_terms_days": 30,
        "invoice_amount": "20000.00",
        "currency": "INR",
    }).json()

    res = seeded_client.get(f"/api/v1/invoices/{new_inv['invoice_id']}/payment-risk/latest")
    assert res.status_code == 404
