"""
Data Preprocessing Module for Finora ML Payment Risk Engine.

Handles raw dataset loading, deduplication, cleaning, date parsing,
target definition, and train/open dataset segregation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Tuple
import pandas as pd
import numpy as np


RAW_DATA_PATH = Path("backend/data/raw/payment_date_dataset/dataset.csv")
PROCESSED_DIR = Path("backend/ml/processed")
METADATA_DIR = Path("backend/ml/metadata")


def load_raw_dataset(csv_path: Path | str) -> pd.DataFrame:
    """Load the raw payment date dataset from CSV."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Raw dataset not found at {path}")
    df = pd.read_csv(path)
    return df


def clean_and_parse_dataset(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Clean, parse dates, compute targets, and separate cleared and open invoices.
    
    Returns:
        cleared_df: Invoices with isOpen == 0 and clear_date present.
        open_df: Invoices with isOpen == 1 and clear_date absent.
        stats: Summary statistics dictionary.
    """
    total_raw_rows = len(df)
    
    # 1. Deduplication
    df_dedup = df.drop_duplicates().copy()
    duplicate_rows_dropped = total_raw_rows - len(df_dedup)
    
    # 2. Fill missing invoice_id from doc_id if needed
    if "invoice_id" in df_dedup.columns and "doc_id" in df_dedup.columns:
        df_dedup["invoice_id"] = df_dedup["invoice_id"].fillna(df_dedup["doc_id"])

    # 3. Drop unneeded 100% missing columns
    if "area_business" in df_dedup.columns:
        df_dedup = df_dedup.drop(columns=["area_business"])

    # 4. Standardize and parse dates
    # posting_date: mixed string format e.g. 1/26/2020 or YYYY-MM-DD
    df_dedup["posting_date_dt"] = pd.to_datetime(df_dedup["posting_date"], format="mixed")
    
    # due_in_date: float/int YYYYMMDD e.g. 20200210
    df_dedup["due_date_dt"] = pd.to_datetime(
        df_dedup["due_in_date"].astype(int).astype(str), format="%Y%m%d"
    )
    
    # baseline_create_date: float/int YYYYMMDD
    if "baseline_create_date" in df_dedup.columns:
        df_dedup["baseline_date_dt"] = pd.to_datetime(
            df_dedup["baseline_create_date"].astype(int).astype(str), format="%Y%m%d"
        )
    else:
        df_dedup["baseline_date_dt"] = df_dedup["posting_date_dt"]

    # 5. Split cleared vs open
    is_open_mask = df_dedup["isOpen"].astype(int) == 1
    open_df = df_dedup[is_open_mask].copy()
    cleared_df = df_dedup[~is_open_mask].copy()

    # 6. Parse clear_date on cleared_df and compute targets
    cleared_df["clear_date_dt"] = pd.to_datetime(cleared_df["clear_date"], format="mixed").dt.normalize()
    
    # payment_delay_days = clear_date - due_date
    cleared_df["payment_delay_days"] = (cleared_df["clear_date_dt"] - cleared_df["due_date_dt"]).dt.days
    
    # Binary classification target: 1 if delayed past due date, 0 if on-time or early
    cleared_df["is_late"] = (cleared_df["payment_delay_days"] > 0).astype(int)
    
    # Regression target: delay days conditional on being late (payment_delay_days > 0)
    cleared_df["late_delay_days"] = np.where(
        cleared_df["payment_delay_days"] > 0,
        cleared_df["payment_delay_days"],
        np.nan
    )

    # For open_df, targets are not yet known
    open_df["clear_date_dt"] = pd.NaT
    open_df["payment_delay_days"] = np.nan
    open_df["is_late"] = np.nan
    open_df["late_delay_days"] = np.nan

    stats = {
        "raw_total_rows": total_raw_rows,
        "duplicate_rows_dropped": duplicate_rows_dropped,
        "unique_rows": len(df_dedup),
        "cleared_count": len(cleared_df),
        "open_count": len(open_df),
        "late_count": int(cleared_df["is_late"].sum()),
        "on_time_count": int((cleared_df["is_late"] == 0).sum()),
        "late_rate": float(cleared_df["is_late"].mean()),
        "avg_late_delay_days": float(cleared_df.loc[cleared_df["is_late"] == 1, "payment_delay_days"].mean()),
        "median_late_delay_days": float(cleared_df.loc[cleared_df["is_late"] == 1, "payment_delay_days"].median()),
        "min_delay_days": int(cleared_df["payment_delay_days"].min()),
        "max_delay_days": int(cleared_df["payment_delay_days"].max()),
    }
    
    return cleared_df, open_df, stats


def run_preprocessing(
    raw_path: Path | str = RAW_DATA_PATH,
    output_dir: Path | str = PROCESSED_DIR,
    metadata_dir: Path | str = METADATA_DIR,
) -> Dict[str, Any]:
    """Execute complete preprocessing pipeline and persist processed datasets and metadata."""
    raw_path = Path(raw_path)
    output_dir = Path(output_dir)
    metadata_dir = Path(metadata_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    df_raw = load_raw_dataset(raw_path)
    cleared_df, open_df, stats = clean_and_parse_dataset(df_raw)

    cleared_out = output_dir / "cleared_invoices.csv"
    open_out = output_dir / "open_invoices.csv"

    cleared_df.to_csv(cleared_out, index=False)
    open_df.to_csv(open_out, index=False)

    provenance = {
        "source_dataset": str(raw_path),
        "source_sha256": "139482bdc3325a734474d08f48ceee71ab67c84b106f2a0c0fe9479d71be8431",
        "processed_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "stats": stats,
        "target_definitions": {
            "payment_delay_days": "clear_date - due_date in integer days",
            "is_late": "1 if payment_delay_days > 0 else 0 (binary classification target)",
            "late_delay_days": "payment_delay_days strictly for rows where payment_delay_days > 0 (regression target)",
        },
        "output_files": {
            "cleared_invoices": str(cleared_out),
            "open_invoices": str(open_out),
        }
    }

    with open(metadata_dir / "dataset_provenance.json", "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2)

    return provenance


if __name__ == "__main__":
    prov = run_preprocessing()
    print("Preprocessing completed successfully:")
    print(json.dumps(prov["stats"], indent=2))
