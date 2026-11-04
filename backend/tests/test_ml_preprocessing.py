"""
Tests for ML preprocessing module (Stage 3A).
"""

from pathlib import Path
import json
import pytest
import pandas as pd
import numpy as np

from backend.ml.preprocessing import (
    load_raw_dataset,
    clean_and_parse_dataset,
    RAW_DATA_PATH,
    PROCESSED_DIR,
    METADATA_DIR,
)


def test_load_raw_dataset_missing_file(tmp_path: Path):
    non_existent = tmp_path / "does_not_exist.csv"
    with pytest.raises(FileNotFoundError):
        load_raw_dataset(non_existent)


def test_clean_and_parse_dataset_synthetic():
    data = {
        "business_code": ["U001", "U001", "U001", "CA02", "U001"],
        "cust_number": ["C1", "C1", "C2", "C3", "C1"],
        "name_customer": ["Cust 1", "Cust 1", "Cust 2", "Cust 3", "Cust 1"],
        "clear_date": [
            "2020-02-15 00:00:00",
            "2020-02-15 00:00:00",  # Duplicate row
            "2020-01-20 00:00:00",  # Early payment
            None,                    # Open invoice
            "2020-03-10 00:00:00",  # Late payment
        ],
        "buisness_year": [2020, 2020, 2020, 2020, 2020],
        "doc_id": [101, 101, 102, 103, 104],
        "posting_date": ["1/1/2020", "1/1/2020", "1/5/2020", "2/1/2020", "2/5/2020"],
        "document_create_date": [20200101, 20200101, 20200105, 20200201, 20200205],
        "document_create_date.1": [20200101, 20200101, 20200105, 20200201, 20200205],
        "due_in_date": [20200201, 20200201, 20200125, 20200220, 20200220],
        "invoice_currency": ["USD", "USD", "USD", "CAD", "USD"],
        "document type": ["RV", "RV", "RV", "RV", "RV"],
        "posting_id": [1, 1, 1, 1, 1],
        "area_business": [np.nan, np.nan, np.nan, np.nan, np.nan],
        "total_open_amount": [1000.0, 1000.0, 2500.0, 500.0, 1200.0],
        "baseline_create_date": [20200101, 20200101, 20200105, 20200201, 20200205],
        "cust_payment_terms": ["NAA8", "NAA8", "NAA8", "CA10", "NAA8"],
        "invoice_id": [101, 101, 102, np.nan, 104],  # Row 3 has NaN invoice_id
        "isOpen": [0, 0, 0, 1, 0],
    }
    df = pd.DataFrame(data)
    cleared_df, open_df, stats = clean_and_parse_dataset(df)

    # 1 duplicate dropped -> 4 rows remaining (3 cleared, 1 open)
    assert stats["duplicate_rows_dropped"] == 1
    assert stats["cleared_count"] == 3
    assert stats["open_count"] == 1

    # Check invoice_id filled from doc_id for open invoice
    assert open_df["invoice_id"].iloc[0] == 103

    # Check area_business dropped
    assert "area_business" not in cleared_df.columns
    assert "area_business" not in open_df.columns

    # Cleared checks:
    # Row 101: clear 2020-02-15, due 2020-02-01 -> delay = +14 -> is_late = 1
    # Row 102: clear 2020-01-20, due 2020-01-25 -> delay = -5  -> is_late = 0
    # Row 104: clear 2020-03-10, due 2020-02-20 -> delay = +19 -> is_late = 1
    r101 = cleared_df[cleared_df["doc_id"] == 101].iloc[0]
    assert r101["payment_delay_days"] == 14
    assert r101["is_late"] == 1
    assert r101["late_delay_days"] == 14

    r102 = cleared_df[cleared_df["doc_id"] == 102].iloc[0]
    assert r102["payment_delay_days"] == -5
    assert r102["is_late"] == 0
    assert np.isnan(r102["late_delay_days"])

    r104 = cleared_df[cleared_df["doc_id"] == 104].iloc[0]
    assert r104["payment_delay_days"] == 19
    assert r104["is_late"] == 1

    assert stats["late_count"] == 2
    assert stats["on_time_count"] == 1


def test_processed_files_exist_and_schema():
    cleared_file = PROCESSED_DIR / "cleared_invoices.csv"
    open_file = PROCESSED_DIR / "open_invoices.csv"
    prov_file = METADATA_DIR / "dataset_provenance.json"

    assert cleared_file.exists(), "cleared_invoices.csv must exist"
    assert open_file.exists(), "open_invoices.csv must exist"
    assert prov_file.exists(), "dataset_provenance.json must exist"

    df_cleared = pd.read_csv(cleared_file, nrows=50)
    assert "payment_delay_days" in df_cleared.columns
    assert "is_late" in df_cleared.columns
    assert "late_delay_days" in df_cleared.columns
    assert (df_cleared["isOpen"] == 0).all()

    df_open = pd.read_csv(open_file, nrows=50)
    assert (df_open["isOpen"] == 1).all()

    with open(prov_file, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["stats"]["cleared_count"] == 39158
    assert meta["stats"]["open_count"] == 9681
