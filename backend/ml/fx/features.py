from typing import List, Dict, Any
import numpy as np
import pandas as pd

FEATURE_SCHEMA_VERSION = "1.0.0"

FEATURE_NAMES = [
    "log_return_1d",
    "log_return_2d",
    "log_return_3d",
    "log_return_5d",
    "log_return_10d",
    "log_return_20d",
    "ma_5d",
    "ma_10d",
    "ma_20d",
    "ma_dist_5d",
    "ma_dist_10d",
    "ma_dist_20d",
    "vol_5d",
    "vol_10d",
    "vol_20d",
    "momentum_10d",
    "month",
    "quarter",
    "day_of_week",
    "horizon_sessions",
]


def compute_historical_features(df_series: pd.DataFrame) -> pd.DataFrame:
    """
    Computes leakage-free technical and calendar features on a chronological time series.
    Requires columns: ['date', 'rate'] sorted ascending by date.
    All rolling windows look strictly backward.
    """
    df = df_series.copy().sort_values("date").reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    df["rate"] = df["rate"].astype(float)

    # Returns (log returns from t-k to t)
    for k in [1, 2, 3, 5, 10, 20]:
        df[f"log_return_{k}d"] = np.log(df["rate"] / df["rate"].shift(k))

    # Moving averages (inclusive of t, looking back k days)
    for k in [5, 10, 20]:
        df[f"ma_{k}d"] = df["rate"].rolling(window=k).mean()
        df[f"ma_dist_{k}d"] = (df["rate"] - df[f"ma_{k}d"]) / df[f"ma_{k}d"]

    # Volatilities (rolling std of 1-day log returns)
    for k in [5, 10, 20]:
        df[f"vol_{k}d"] = df["log_return_1d"].rolling(window=k).std()

    # Momentum
    df["momentum_10d"] = df["rate"] - df["rate"].shift(10)

    # Calendar features
    df["month"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    df["day_of_week"] = df["date"].dt.dayofweek

    return df


def extract_features_at_origin(df_history: pd.DataFrame, horizon_sessions: int) -> pd.DataFrame:
    """
    Extracts the feature vector at the latest available observation date in history
    for a given forecast horizon h in [1, 30].
    """
    df_feat = compute_historical_features(df_history)
    latest_row = df_feat.iloc[-1:].copy()
    latest_row["horizon_sessions"] = int(horizon_sessions)

    # Ensure all feature columns exist and are finite
    missing = [c for c in FEATURE_NAMES if c not in latest_row.columns]
    if missing:
        raise ValueError(f"Missing features: {missing}")

    return latest_row[FEATURE_NAMES]

