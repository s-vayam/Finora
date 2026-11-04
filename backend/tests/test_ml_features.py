"""
Tests for ML Feature Engineering and Leakage Safety (Stage 3B).
"""

import pandas as pd
import numpy as np
from datetime import date

from backend.ml.feature_schema import (
    ALL_FEATURE_COLUMNS,
    NUMERICAL_FEATURES,
    CATEGORICAL_FEATURES,
    DEFAULT_CUSTOMER_HISTORY,
)
from backend.ml.customer_history_features import (
    compute_offline_customer_history,
    compute_live_customer_history,
)
from backend.ml.features import (
    extract_raw_features,
    create_feature_pipeline,
    split_dataset_chronologically,
)


def test_customer_history_leakage_safety():
    """Verify that an invoice posted at T cannot see any payments cleared after T."""
    # Customer C1 has two invoices:
    # Inv 1: posted 2020-01-01, due 2020-01-20, cleared 2020-01-25 (late, delay=5)
    # Inv 2: posted 2020-01-10, due 2020-01-30, cleared 2020-02-05 (late, delay=6)
    # At Inv 2's posting date (2020-01-10), Inv 1 has NOT yet cleared (clear_date is 2020-01-25)!
    # Therefore, Inv 2 MUST be cold-start with count=0!
    df = pd.DataFrame({
        "doc_id": [1, 2],
        "cust_number": ["C1", "C1"],
        "posting_date_dt": [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-01-10")],
        "due_date_dt": [pd.Timestamp("2020-01-20"), pd.Timestamp("2020-01-30")],
        "clear_date_dt": [pd.Timestamp("2020-01-25"), pd.Timestamp("2020-02-05")],
        "is_late": [1, 1],
        "payment_delay_days": [5, 6],
    })

    hist = compute_offline_customer_history(df)

    # For Inv 1 (posted 2020-01-01), history must be cold start
    assert hist.iloc[0]["is_cold_start"] == 1
    assert hist.iloc[0]["cust_prev_invoice_count"] == 0

    # For Inv 2 (posted 2020-01-10), Inv 1 cleared 2020-01-25 > 2020-01-10, so NO look-ahead!
    assert hist.iloc[1]["is_cold_start"] == 1
    assert hist.iloc[1]["cust_prev_invoice_count"] == 0

    # Now add Inv 3 posted 2020-02-10 (after both Inv 1 & 2 cleared!)
    df3 = pd.concat([
        df,
        pd.DataFrame({
            "doc_id": [3],
            "cust_number": ["C1"],
            "posting_date_dt": [pd.Timestamp("2020-02-10")],
            "due_date_dt": [pd.Timestamp("2020-02-28")],
            "clear_date_dt": [pd.Timestamp("2020-02-28")],
            "is_late": [0],
            "payment_delay_days": [0],
        })
    ], ignore_index=True)

    hist3 = compute_offline_customer_history(df3)
    # Inv 3 should see exactly 2 prior invoices (Inv 1 & 2), both late
    assert hist3.iloc[2]["is_cold_start"] == 0
    assert hist3.iloc[2]["cust_prev_invoice_count"] == 2
    assert hist3.iloc[2]["cust_prev_late_rate"] == 1.0
    assert hist3.iloc[2]["cust_prev_avg_delay"] == 5.5
    assert hist3.iloc[2]["cust_prev_max_delay"] == 6.0


def test_live_customer_history():
    """Verify live customer history calculation with date cutoff."""
    prior = [
        {"payment_date": date(2025, 1, 15), "due_date": date(2025, 1, 10)},  # late by 5
        {"payment_date": date(2025, 2, 10), "due_date": date(2025, 2, 15)},  # early by -5
        {"payment_date": date(2025, 3, 20), "due_date": date(2025, 3, 10)},  # late by 10
    ]

    # As of 2025-02-12, only first 2 are eligible
    h = compute_live_customer_history(prior, as_of_date=date(2025, 2, 12))
    assert h["cust_prev_invoice_count"] == 2
    assert h["cust_prev_late_rate"] == 0.5
    assert h["cust_prev_ontime_rate"] == 0.5
    assert h["cust_prev_avg_delay"] == 0.0
    assert h["cust_prev_max_delay"] == 5.0
    assert h["is_cold_start"] == 0

    # Cold start check
    empty_h = compute_live_customer_history([])
    assert empty_h == DEFAULT_CUSTOMER_HISTORY


def test_feature_pipeline_transformation():
    """Verify ColumnTransformer fits and transforms without errors or NaNs."""
    df = pd.DataFrame({
        "total_open_amount": [1000.0, 5000.0, 250.0, 12000.0],
        "posting_date_dt": [
            pd.Timestamp("2020-01-01"),
            pd.Timestamp("2020-01-05"),
            pd.Timestamp("2020-01-10"),
            pd.Timestamp("2020-01-15"),
        ],
        "due_date_dt": [
            pd.Timestamp("2020-01-20"),
            pd.Timestamp("2020-01-25"),
            pd.Timestamp("2020-01-30"),
            pd.Timestamp("2020-02-15"),
        ],
        "baseline_date_dt": [
            pd.Timestamp("2020-01-01"),
            pd.Timestamp("2020-01-05"),
            pd.Timestamp("2020-01-10"),
            pd.Timestamp("2020-01-15"),
        ],
        "invoice_currency": ["USD", "CAD", "USD", "USD"],
        "business_code": ["U001", "CA02", "U001", "U001"],
        "cust_payment_terms": ["NAA8", "CA10", "NAA8", "NAH4"],
    })

    X_raw = extract_raw_features(df, include_customer_history=False)
    assert list(X_raw.columns) == ALL_FEATURE_COLUMNS

    pipeline = create_feature_pipeline()
    X_trans = pipeline.fit_transform(X_raw)

    assert X_trans.shape[0] == 4
    assert not np.isnan(X_trans).any()


def test_split_dataset_chronological():
    """Verify chronological split guarantees non-overlapping temporal windows."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    df = pd.DataFrame({
        "doc_id": range(100),
        "posting_date_dt": dates,
    })

    train_df, val_df, test_df = split_dataset_chronologically(df, 0.7, 0.15)
    assert len(train_df) == 70
    assert len(val_df) == 15
    assert len(test_df) == 15

    assert train_df["posting_date_dt"].max() <= val_df["posting_date_dt"].min()
    assert val_df["posting_date_dt"].max() <= test_df["posting_date_dt"].min()
