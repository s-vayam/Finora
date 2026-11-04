"""
Payment Risk Prediction Service for Finora ML Engine.

Handles loading model artifacts, extracting live features from Finora database,
enforcing invoice eligibility rules, generating probability and delay predictions,
and persisting prediction records.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import joblib
import numpy as np
import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.ml_prediction import MLPrediction

try:
    from backend.ml.training.training_config import CONFIG
    from backend.ml.feature_schema import ALL_FEATURE_COLUMNS
    from backend.ml.customer_history_features import compute_live_customer_history
except ModuleNotFoundError:
    from ml.training.training_config import CONFIG
    from ml.feature_schema import ALL_FEATURE_COLUMNS
    from ml.customer_history_features import compute_live_customer_history


class PredictionEngine:
    """Singleton/cached loader for ML artifacts."""
    _instance: Optional["PredictionEngine"] = None

    def __init__(self):
        self.pipeline = None
        self.classifier = None
        self.regressor = None
        self.metadata: Dict[str, Any] = {}
        self.metrics: Dict[str, Any] = {}
        self.feature_importance: Dict[str, Any] = {}
        self.is_loaded = False
        self._load_artifacts()

    @classmethod
    def get_instance(cls) -> "PredictionEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_artifacts(self) -> None:
        try:
            if (
                CONFIG.feature_pipeline_artifact.exists()
                and CONFIG.classifier_artifact.exists()
                and CONFIG.regressor_artifact.exists()
            ):
                self.pipeline = joblib.load(CONFIG.feature_pipeline_artifact)
                self.classifier = joblib.load(CONFIG.classifier_artifact)
                self.regressor = joblib.load(CONFIG.regressor_artifact)

                if CONFIG.model_metadata_file.exists():
                    with open(CONFIG.model_metadata_file, "r", encoding="utf-8") as f:
                        self.metadata = json.load(f)

                if CONFIG.evaluation_metrics_file.exists():
                    with open(CONFIG.evaluation_metrics_file, "r", encoding="utf-8") as f:
                        self.metrics = json.load(f)

                if CONFIG.feature_importance_file.exists():
                    with open(CONFIG.feature_importance_file, "r", encoding="utf-8") as f:
                        self.feature_importance = json.load(f)

                self.is_loaded = True
        except Exception as e:
            self.is_loaded = False
            print(f"Warning: Failed to load ML artifacts: {e}")

    def ensure_loaded(self) -> None:
        if not self.is_loaded or self.classifier is None or self.regressor is None:
            self._load_artifacts()
            if not self.is_loaded:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="ML prediction models are not loaded or artifacts are missing.",
                )


def format_prediction_dict(pred: MLPrediction) -> Dict[str, Any]:
    """Helper to convert MLPrediction model to dict with parsed JSON features_snapshot."""
    snapshot = {}
    if pred.features_snapshot:
        try:
            snapshot = json.loads(pred.features_snapshot)
        except Exception:
            snapshot = {"raw": pred.features_snapshot}

    return {
        "id": pred.id,
        "invoice_id": pred.invoice_id,
        "prediction_timestamp": pred.prediction_timestamp,
        "model_version": pred.model_version,
        "predicted_late_probability": float(pred.predicted_late_probability),
        "risk_category": pred.risk_category,
        "predicted_delay_days": float(pred.predicted_delay_days),
        "expected_delay_days": float(pred.expected_delay_days),
        "estimated_payment_date": pred.estimated_payment_date,
        "features_snapshot": snapshot,
    }


def predict_invoice_payment_risk(
    db: Session,
    invoice_id: str,
) -> Dict[str, Any]:
    """
    Generate and persist a payment risk prediction for an eligible invoice.

    Strict eligibility:
    - Invoice must exist in the database.
    - Invoice must not be PAID, PARTIALLY_PAID, or CANCELLED.
    """
    engine = PredictionEngine.get_instance()
    engine.ensure_loaded()

    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice '{invoice_id}' not found.",
        )

    # Ineligibility check 1: status string
    inv_status = str(invoice.status).upper()
    if inv_status == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invoice '{invoice_id}' is CANCELLED and ineligible for payment risk prediction.",
        )
    if inv_status == "PAID":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invoice '{invoice_id}' is already PAID and ineligible for payment risk prediction.",
        )

    # Ineligibility check 2: existing payments in database
    existing_payments = db.query(Payment).filter(Payment.invoice_id == invoice_id).all()
    if existing_payments:
        total_paid = sum(float(p.amount) for p in existing_payments)
        if total_paid >= float(invoice.invoice_amount):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Invoice '{invoice_id}' has already been paid in full and is ineligible.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Invoice '{invoice_id}' is PARTIALLY_PAID and ineligible for payment risk prediction.",
            )

    # 1. Gather prior customer payments
    prior_payments_records = (
        db.query(Payment)
        .join(Invoice, Payment.invoice_id == Invoice.invoice_id)
        .filter(
            Invoice.customer_id == invoice.customer_id,
            Payment.payment_date <= invoice.invoice_date,
            Invoice.invoice_id != invoice_id,
        )
        .all()
    )

    prior_payments = [
        {"payment_date": p.payment_date, "due_date": p.invoice.due_date}
        for p in prior_payments_records
    ]

    hist_metrics = compute_live_customer_history(
        prior_payments, as_of_date=invoice.invoice_date
    )

    # 2. Extract invoice features
    amount = float(invoice.invoice_amount)
    log_amount = float(np.log1p(amount))
    terms_days = int((invoice.due_date - invoice.invoice_date).days)
    baseline_days = int(invoice.payment_terms_days) if invoice.payment_terms_days is not None else terms_days

    feature_data = {
        "invoice_amount": amount,
        "log_invoice_amount": log_amount,
        "terms_days": terms_days,
        "baseline_to_due_days": baseline_days,
        "invoice_month": invoice.invoice_date.month,
        "invoice_quarter": (invoice.invoice_date.month - 1) // 3 + 1,
        "invoice_dayofweek": invoice.invoice_date.weekday(),
        "due_month": invoice.due_date.month,
        "due_dayofweek": invoice.due_date.weekday(),
        "cust_prev_invoice_count": hist_metrics["cust_prev_invoice_count"],
        "cust_prev_late_rate": hist_metrics["cust_prev_late_rate"],
        "cust_prev_ontime_rate": hist_metrics["cust_prev_ontime_rate"],
        "cust_prev_avg_delay": hist_metrics["cust_prev_avg_delay"],
        "cust_prev_max_delay": hist_metrics["cust_prev_max_delay"],
        "is_cold_start": hist_metrics["is_cold_start"],
        "currency": str(invoice.currency).strip().upper() if invoice.currency else "USD",
        "business_code": "U001",
        "cust_payment_terms": "NAA8",
    }

    input_df = pd.DataFrame([feature_data])[ALL_FEATURE_COLUMNS]

    # 3. Model Inference
    X_trans = engine.pipeline.transform(input_df)
    prob = float(engine.classifier.predict_proba(X_trans)[0, 1])
    cond_delay = max(0.0, float(engine.regressor.predict(X_trans)[0]))

    # Risk categorization
    if prob < 0.35:
        risk_category = "LOW"
    elif prob <= 0.65:
        risk_category = "MEDIUM"
    else:
        risk_category = "HIGH"

    # Expected delay = probability * conditional delay
    expected_delay = prob * cond_delay
    estimated_payment_date = invoice.due_date + timedelta(days=int(round(expected_delay)))

    # 4. Save prediction record
    prediction_record = MLPrediction(
        invoice_id=invoice_id,
        prediction_timestamp=datetime.now(timezone.utc),
        model_version=engine.metadata.get("model_version", "v1.0.0"),
        predicted_late_probability=round(prob, 4),
        risk_category=risk_category,
        predicted_delay_days=round(cond_delay, 2),
        expected_delay_days=round(expected_delay, 2),
        estimated_payment_date=estimated_payment_date,
        features_snapshot=json.dumps(feature_data),
    )

    db.add(prediction_record)
    db.commit()
    db.refresh(prediction_record)

    return format_prediction_dict(prediction_record)


def get_latest_prediction(db: Session, invoice_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve the latest prediction for an invoice, or None if not found."""
    pred = (
        db.query(MLPrediction)
        .filter(MLPrediction.invoice_id == invoice_id)
        .order_by(MLPrediction.prediction_timestamp.desc())
        .first()
    )
    if not pred:
        return None
    return format_prediction_dict(pred)


def get_prediction_history(db: Session, invoice_id: str) -> List[Dict[str, Any]]:
    """Retrieve all chronological prediction records for an invoice."""
    preds = (
        db.query(MLPrediction)
        .filter(MLPrediction.invoice_id == invoice_id)
        .order_by(MLPrediction.prediction_timestamp.asc())
        .all()
    )
    return [format_prediction_dict(p) for p in preds]


def get_model_status_info() -> Dict[str, Any]:
    """Retrieve model readiness status and metadata."""
    engine = PredictionEngine.get_instance()
    meta = engine.metadata
    return {
        "model_version": meta.get("model_version", "v1.0.0"),
        "is_loaded": engine.is_loaded,
        "classifier_type": meta.get("classifier", {}).get("model_type", "Unknown"),
        "regressor_type": meta.get("regressor", {}).get("model_type", "Unknown"),
        "optimal_threshold": float(meta.get("classifier", {}).get("optimal_threshold", 0.50)),
        "trained_at": meta.get("trained_at", ""),
    }


def get_model_metrics_info() -> Dict[str, Any]:
    """Retrieve test evaluation metrics and feature importance summaries."""
    engine = PredictionEngine.get_instance()
    meta = engine.metadata
    metrics = engine.metrics
    return {
        "model_version": meta.get("model_version", "v1.0.0"),
        "trained_at": meta.get("trained_at", ""),
        "classification_test_metrics": metrics.get("classification", {}).get(
            "champion_test_at_optimal_threshold", {}
        ),
        "regression_test_metrics": metrics.get("regression", {}).get(
            "champion_test_metrics", {}
        ),
        "feature_importance": engine.feature_importance,
    }
