"""
FastAPI Router for ML Payment Risk Engine.

Exposes endpoints for payment risk prediction, status checks, model metrics,
latest invoice prediction, and historical predictions.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.invoice import Invoice
from app.schemas.prediction import (
    PaymentRiskPredictionRequest,
    PaymentRiskPredictionResponse,
    MLStatusResponse,
    MLMetricsResponse,
)
from app.services.payment_prediction_service import (
    predict_invoice_payment_risk,
    get_latest_prediction,
    get_prediction_history,
    get_model_status_info,
    get_model_metrics_info,
)

router = APIRouter(tags=["ML Payment Risk Engine"])


@router.get(
    "/ml/payment-risk/status",
    response_model=MLStatusResponse,
    summary="Get ML payment risk model readiness status",
)
def get_ml_status():
    """Retrieve operational status and model readiness info."""
    return get_model_status_info()


@router.get(
    "/ml/payment-risk/metrics",
    response_model=MLMetricsResponse,
    summary="Get ML model evaluation metrics and feature importance",
)
def get_ml_metrics():
    """Retrieve test evaluation metrics, confusion matrix, and feature importances."""
    return get_model_metrics_info()


@router.post(
    "/predict/payment-risk",
    response_model=PaymentRiskPredictionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate payment risk prediction for an eligible unpaid invoice",
)
def predict_payment_risk(
    payload: PaymentRiskPredictionRequest,
    db: Session = Depends(get_db),
):
    """
    Run ML inference on an invoice to predict late payment probability,
    conditional delay, expected delay, and nominal estimated payment date.
    Strictly restricted to unpaid invoices.
    """
    prediction = predict_invoice_payment_risk(db, payload.invoice_id)
    return prediction


@router.get(
    "/invoices/{invoice_id}/payment-risk/latest",
    response_model=PaymentRiskPredictionResponse,
    summary="Get latest payment risk prediction for an invoice",
)
def get_invoice_latest_risk(
    invoice_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve the most recent prediction generated for the given invoice."""
    # Verify invoice exists
    inv = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice '{invoice_id}' not found.",
        )

    pred = get_latest_prediction(db, invoice_id)
    if not pred:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No prediction has been generated for invoice '{invoice_id}'.",
        )
    return pred


@router.get(
    "/invoices/{invoice_id}/payment-risk/history",
    response_model=List[PaymentRiskPredictionResponse],
    summary="Get payment risk prediction history for an invoice",
)
def get_invoice_risk_history(
    invoice_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve the complete chronological history of predictions for the given invoice."""
    inv = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice '{invoice_id}' not found.",
        )

    preds = get_prediction_history(db, invoice_id)
    return preds
