"""
Comprehensive Tests for ML Model Loading, Artifact Path Resolution, and Invoice Inference.
"""

from datetime import date
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.ml_prediction import MLPrediction
from app.services.payment_prediction_service import PredictionEngine


def _setup_test_environment(db: Session):
    co = db.query(Company).filter(Company.company_id == "FINORA_DEMO").first()
    if not co:
        co = Company(
            company_id="FINORA_DEMO",
            company_name="Finora Demo Exports Pvt Ltd",
            base_currency="INR",
        )
        db.add(co)

    cust = db.query(Customer).filter(Customer.customer_id == "CUST058").first()
    if not cust:
        cust = Customer(
            customer_id="CUST058",
            company_id="FINORA_DEMO",
            customer_name="Global Trade Partners",
            country="United States",
            industry="Manufacturing",
        )
        db.add(cust)

    inv = db.query(Invoice).filter(Invoice.invoice_id == "INV-000853").first()
    if not inv:
        inv = Invoice(
            invoice_id="INV-000853",
            company_id="FINORA_DEMO",
            customer_id="CUST058",
            invoice_date=date(2025, 11, 12),
            due_date=date(2025, 12, 27),
            payment_terms_days=45,
            invoice_amount=96261.98,
            currency="INR",
            status="OPEN",
        )
        db.add(inv)

    db.commit()


def test_prediction_engine_loaded():
    """Verify PredictionEngine singleton successfully discovers and loads model artifacts."""
    engine = PredictionEngine.get_instance()
    assert engine.is_loaded is True
    assert engine.classifier is not None
    assert engine.regressor is not None
    assert engine.pipeline is not None
    assert "model_version" in engine.metadata


def test_ml_status_endpoint(client: TestClient):
    """Verify GET /api/v1/ml/payment-risk/status returns operational readiness."""
    res = client.get("/api/v1/ml/payment-risk/status")
    assert res.status_code == 200
    data = res.json()
    assert data["is_loaded"] is True
    assert data["classifier_type"] == "RandomForestClassifier"
    assert data["regressor_type"] == "Ridge"
    assert "model_version" in data


def test_predict_payment_risk_inv_000853(client: TestClient, test_db_session: Session):
    """Verify inference pipeline executes successfully on diagnostic invoice INV-000853."""
    _setup_test_environment(test_db_session)

    res = client.post(
        "/api/v1/predict/payment-risk",
        json={"invoice_id": "INV-000853"},
    )
    assert res.status_code == 201
    pred = res.json()

    assert pred["invoice_id"] == "INV-000853"
    assert 0.0 <= pred["predicted_late_probability"] <= 1.0
    assert pred["late_probability"] == pred["predicted_late_probability"]
    assert pred["risk_category"] in ("LOW", "MEDIUM", "HIGH")
    assert pred["predicted_delay_days"] >= 0.0
    assert pred["expected_delay_days"] >= 0.0
    assert "estimated_payment_date" in pred
    assert pred["prediction_id"].startswith("PRD-")

    # Verify prediction persisted in database
    db_pred = (
        test_db_session.query(MLPrediction)
        .filter(MLPrediction.invoice_id == "INV-000853")
        .first()
    )
    assert db_pred is not None
    assert db_pred.risk_category == pred["risk_category"]

    # Verify latest endpoint returns the newly generated prediction
    latest_res = client.get("/api/v1/invoices/INV-000853/payment-risk/latest")
    assert latest_res.status_code == 200
    assert latest_res.json()["invoice_id"] == "INV-000853"
