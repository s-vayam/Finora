"""
Feature Engineering and Transformation Pipeline for Finora ML.

Constructs invoice-level and customer-historical features, builds
scikit-learn ColumnTransformer preprocessing pipelines, and provides
chronological dataset splitting.
"""

from __future__ import annotations

from typing import Tuple, List, Optional
import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer

from backend.ml.feature_schema import (
    NUMERICAL_FEATURES,
    CATEGORICAL_FEATURES,
    ALL_FEATURE_COLUMNS,
    CLASSIFICATION_TARGET,
    REGRESSION_TARGET,
)
from backend.ml.customer_history_features import compute_offline_customer_history


def extract_raw_features(
    df: pd.DataFrame,
    include_customer_history: bool = True,
    hist_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Extract raw feature columns from cleaned invoice DataFrame.

    Ensures that all features in ALL_FEATURE_COLUMNS are computed and present.
    """
    df_work = df.copy()

    # Ensure datetime types
    if not pd.api.types.is_datetime64_any_dtype(df_work["posting_date_dt"]):
        df_work["posting_date_dt"] = pd.to_datetime(df_work["posting_date_dt"])
    if not pd.api.types.is_datetime64_any_dtype(df_work["due_date_dt"]):
        df_work["due_date_dt"] = pd.to_datetime(df_work["due_date_dt"])
    if "baseline_date_dt" in df_work.columns and not pd.api.types.is_datetime64_any_dtype(
        df_work["baseline_date_dt"]
    ):
        df_work["baseline_date_dt"] = pd.to_datetime(df_work["baseline_date_dt"])
    elif "baseline_date_dt" not in df_work.columns:
        df_work["baseline_date_dt"] = df_work["posting_date_dt"]

    # Numerical features
    invoice_amount = df_work["total_open_amount"].astype(float)
    log_invoice_amount = np.log1p(np.maximum(invoice_amount, 0.0))
    terms_days = (df_work["due_date_dt"] - df_work["posting_date_dt"]).dt.days
    baseline_to_due_days = (df_work["due_date_dt"] - df_work["baseline_date_dt"]).dt.days

    invoice_month = df_work["posting_date_dt"].dt.month
    invoice_quarter = df_work["posting_date_dt"].dt.quarter
    invoice_dayofweek = df_work["posting_date_dt"].dt.dayofweek
    due_month = df_work["due_date_dt"].dt.month
    due_dayofweek = df_work["due_date_dt"].dt.dayofweek

    # Categorical features
    currency = (
        df_work["invoice_currency"].fillna("USD").astype(str).str.strip().str.upper()
        if "invoice_currency" in df_work.columns
        else pd.Series("USD", index=df_work.index)
    )
    business_code = (
        df_work["business_code"].fillna("U001").astype(str).str.strip()
        if "business_code" in df_work.columns
        else pd.Series("U001", index=df_work.index)
    )
    cust_payment_terms = (
        df_work["cust_payment_terms"].fillna("NAA8").astype(str).str.strip()
        if "cust_payment_terms" in df_work.columns
        else pd.Series("NAA8", index=df_work.index)
    )

    feat_dict = {
        "invoice_amount": invoice_amount,
        "log_invoice_amount": log_invoice_amount,
        "terms_days": terms_days,
        "baseline_to_due_days": baseline_to_due_days,
        "invoice_month": invoice_month,
        "invoice_quarter": invoice_quarter,
        "invoice_dayofweek": invoice_dayofweek,
        "due_month": due_month,
        "due_dayofweek": due_dayofweek,
        "currency": currency,
        "business_code": business_code,
        "cust_payment_terms": cust_payment_terms,
    }

    # Customer historical features
    if include_customer_history:
        if hist_df is None:
            hist_df = compute_offline_customer_history(df_work)
        for col in [
            "cust_prev_invoice_count",
            "cust_prev_late_rate",
            "cust_prev_ontime_rate",
            "cust_prev_avg_delay",
            "cust_prev_max_delay",
            "is_cold_start",
        ]:
            feat_dict[col] = hist_df[col]
    else:
        # Default cold start values
        for col, val in [
            ("cust_prev_invoice_count", 0),
            ("cust_prev_late_rate", 0.0),
            ("cust_prev_ontime_rate", 1.0),
            ("cust_prev_avg_delay", 0.0),
            ("cust_prev_max_delay", 0.0),
            ("is_cold_start", 1),
        ]:
            feat_dict[col] = pd.Series(val, index=df_work.index)

    features = pd.DataFrame(feat_dict, index=df_work.index)
    # Ensure all required features are present in expected order
    return features[ALL_FEATURE_COLUMNS]


def create_feature_pipeline() -> ColumnTransformer:
    """Create sklearn ColumnTransformer for numerical and categorical preprocessing."""
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, NUMERICAL_FEATURES),
            ("cat", categorical_transformer, CATEGORICAL_FEATURES),
        ]
    )

    return preprocessor


def split_dataset_chronologically(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split dataset chronologically by posting_date_dt.

    Default split: 70% train, 15% validation, 15% test.
    """
    df_sorted = df.sort_values(by="posting_date_dt").reset_index(drop=True)
    n = len(df_sorted)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    train_df = df_sorted.iloc[:train_end].copy()
    val_df = df_sorted.iloc[train_end:val_end].copy()
    test_df = df_sorted.iloc[val_end:].copy()

    return train_df, val_df, test_df
