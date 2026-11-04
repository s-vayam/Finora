import json
import sys
from pathlib import Path
from typing import Tuple, Dict, Any

backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import numpy as np
import pandas as pd
from sqlalchemy import select
from app.database import SessionLocal
from app.models.fx_rate_observation import FxRateObservation
from ml.fx.features import compute_historical_features, FEATURE_NAMES

PROCESSED_DIR = Path(__file__).parent / "processed"
NEUTRAL_THRESHOLD_BPS = 0.0010  # 10 basis points (0.10%)
MAX_HORIZON = 30


def load_pair_series(currency: str) -> pd.DataFrame:
    session = SessionLocal()
    try:
        query = select(
            FxRateObservation.observation_date,
            FxRateObservation.rate_value
        ).where(
            FxRateObservation.base_currency == currency.upper(),
            FxRateObservation.quote_currency == "INR",
            FxRateObservation.rate_type == "REFERENCE_DAILY"
        ).order_by(FxRateObservation.observation_date.asc())

        rows = session.execute(query).all()
        df = pd.DataFrame(rows, columns=["date", "rate"])
        df["date"] = pd.to_datetime(df["date"])
        df["rate"] = df["rate"].astype(float)
        return df
    finally:
        session.close()


def build_multi_horizon_dataset(currency: str) -> pd.DataFrame:
    """
    Builds a multi-horizon dataset with leakage-free features and target returns.
    For each trading day t and horizon h in [1, 30]:
      future_log_return = log(rate[t+h] / rate[t])
      direction = UP (1), DOWN (-1), NEUTRAL (0)
    """
    df_raw = load_pair_series(currency)
    if len(df_raw) < 100:
        raise ValueError(f"Insufficient historical data for {currency}: {len(df_raw)} rows")

    # Compute base technical features
    df_feat = compute_historical_features(df_raw)
    # Drop warm-up rows (first 20 rows due to 20-day rolling windows)
    df_feat = df_feat.iloc[20:].reset_index(drop=True)

    n_samples = len(df_feat)
    rates = df_feat["rate"].values
    dates = df_feat["date"].values

    feat_dicts = df_feat[[col for col in df_feat.columns if col in FEATURE_NAMES]].to_dict('records')
    records = []
    # For each origin day t (up to n_samples - MAX_HORIZON)
    for t in range(n_samples - MAX_HORIZON):
        origin_rate = rates[t]
        origin_date = dates[t]
        base_features = feat_dicts[t]

        for h in range(1, MAX_HORIZON + 1):
            future_rate = rates[t + h]
            log_ret = float(np.log(future_rate / origin_rate))

            if log_ret > NEUTRAL_THRESHOLD_BPS:
                direction = 1  # UP
            elif log_ret < -NEUTRAL_THRESHOLD_BPS:
                direction = -1  # DOWN
            else:
                direction = 0  # NEUTRAL

            row_data = base_features.copy()
            row_data["horizon_sessions"] = h
            row_data["origin_date"] = origin_date
            row_data["origin_rate"] = origin_rate
            row_data["future_date"] = dates[t + h]
            row_data["future_rate"] = future_rate
            row_data["target_log_return"] = log_ret
            row_data["target_direction"] = direction
            records.append(row_data)

    df_out = pd.DataFrame(records)
    return df_out


def create_purged_chronological_splits(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    purge_gap_days: int = 30
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Partitions the dataset chronologically with a purge gap around partition boundaries
    to prevent target return overlap leakage.
    """
    unique_dates = np.sort(df["origin_date"].unique())
    n_dates = len(unique_dates)

    train_end_idx = int(n_dates * train_ratio)
    val_end_idx = int(n_dates * (train_ratio + val_ratio))

    train_cut_date = unique_dates[train_end_idx]
    # Purge gap: validation set starts purge_gap_days after train_cut_date
    val_start_idx = min(train_end_idx + purge_gap_days, val_end_idx - 1)
    val_start_date = unique_dates[val_start_idx]
    val_cut_date = unique_dates[val_end_idx]

    # Purge gap before test set
    test_start_idx = min(val_end_idx + purge_gap_days, n_dates - 1)
    test_start_date = unique_dates[test_start_idx]

    df_train = df[df["origin_date"] < train_cut_date].copy().reset_index(drop=True)
    df_val = df[(df["origin_date"] >= val_start_date) & (df["origin_date"] < val_cut_date)].copy().reset_index(drop=True)
    df_test = df[df["origin_date"] >= test_start_date].copy().reset_index(drop=True)

    return df_train, df_val, df_test


def load_split(currency: str, split_name: str) -> pd.DataFrame:
    file_path = PROCESSED_DIR / f"{currency}_{split_name}.csv.gz"
    if not file_path.exists():
        raise FileNotFoundError(f"Split file not found: {file_path}")
    return pd.read_csv(file_path, compression="gzip")


def prepare_and_save_all_splits():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    summaries = {}

    for currency in ["USD", "EUR", "GBP"]:
        print(f"Building processed multi-horizon dataset for {currency}/INR...")
        df_pair = build_multi_horizon_dataset(currency)
        df_train, df_val, df_test = create_purged_chronological_splits(df_pair)

        train_file = PROCESSED_DIR / f"{currency}_train.csv.gz"
        val_file = PROCESSED_DIR / f"{currency}_val.csv.gz"
        test_file = PROCESSED_DIR / f"{currency}_test.csv.gz"

        df_train.to_csv(train_file, index=False, compression="gzip")
        df_val.to_csv(val_file, index=False, compression="gzip")
        df_test.to_csv(test_file, index=False, compression="gzip")

        summaries[currency] = {
            "total_samples": len(df_pair),
            "train_samples": len(df_train),
            "val_samples": len(df_val),
            "test_samples": len(df_test),
            "train_range": f"{df_train['origin_date'].min()} to {df_train['origin_date'].max()}",
            "val_range": f"{df_val['origin_date'].min()} to {df_val['origin_date'].max()}",
            "test_range": f"{df_test['origin_date'].min()} to {df_test['origin_date'].max()}",
        }
        print(f"  {currency} splits: Train={len(df_train):,}, Val={len(df_val):,}, Test={len(df_test):,}")

    meta_file = Path(__file__).parent / "metadata" / "splits_summary.json"
    meta_file.parent.mkdir(parents=True, exist_ok=True)
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(summaries, f, indent=2, default=str)

    print("Splits successfully saved to parquet.")
    return summaries


if __name__ == "__main__":
    prepare_and_save_all_splits()
