"""
Feature Schema Definitions for Finora ML Payment Risk Engine.

Defines feature names, types, default values, and column groupings
used across preprocessing, feature transformation, model training,
and inference pipelines.
"""

from typing import List, Dict, Any

NUMERICAL_FEATURES: List[str] = [
    "invoice_amount",
    "log_invoice_amount",
    "terms_days",
    "baseline_to_due_days",
    "invoice_month",
    "invoice_quarter",
    "invoice_dayofweek",
    "due_month",
    "due_dayofweek",
    "cust_prev_invoice_count",
    "cust_prev_late_rate",
    "cust_prev_ontime_rate",
    "cust_prev_avg_delay",
    "cust_prev_max_delay",
    "is_cold_start",
]

CATEGORICAL_FEATURES: List[str] = [
    "currency",
    "business_code",
    "cust_payment_terms",
]

ALL_FEATURE_COLUMNS: List[str] = NUMERICAL_FEATURES + CATEGORICAL_FEATURES

# Target column names
CLASSIFICATION_TARGET = "is_late"
REGRESSION_TARGET = "late_delay_days"

# Default values for cold-start / missing customer history
DEFAULT_CUSTOMER_HISTORY: Dict[str, Any] = {
    "cust_prev_invoice_count": 0,
    "cust_prev_late_rate": 0.0,
    "cust_prev_ontime_rate": 1.0,
    "cust_prev_avg_delay": 0.0,
    "cust_prev_max_delay": 0.0,
    "is_cold_start": 1,
}

# Categorical default values
DEFAULT_CATEGORICAL: Dict[str, str] = {
    "currency": "USD",
    "business_code": "U001",
    "cust_payment_terms": "NAA8",
}
