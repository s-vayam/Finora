"""
Pydantic Schemas for ML Payment Risk Engine.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RiskCategory(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class PaymentRiskPredictionRequest(BaseModel):
    invoice_id: str = Field(..., description="Target invoice ID for payment risk prediction")


class PaymentRiskPredictionResponse(BaseModel):
    id: int
    prediction_id: Optional[str] = None
    invoice_id: str
    prediction_timestamp: datetime
    created_at: Optional[datetime] = None
    model_version: str
    predicted_late_probability: float = Field(..., ge=0.0, le=1.0)
    late_probability: Optional[float] = Field(None, ge=0.0, le=1.0, description="Convenience alias for predicted_late_probability")
    risk_category: RiskCategory
    predicted_delay_days: float = Field(..., ge=0.0, description="Conditional delay days if late")
    expected_delay_days: float = Field(..., ge=0.0, description="Probability-weighted delay days")
    estimated_payment_date: date
    features_snapshot: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class MLStatusResponse(BaseModel):
    model_version: str
    is_loaded: bool
    classifier_type: str
    regressor_type: str
    optimal_threshold: float
    trained_at: str


class MLMetricsResponse(BaseModel):
    model_version: str
    trained_at: str
    classification_test_metrics: Dict[str, Any]
    regression_test_metrics: Dict[str, Any]
    feature_importance: Dict[str, Any]
