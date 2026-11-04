#!/usr/bin/env python3
"""
Stage 3A: Dataset Inspection and Profiling for Finora ML Engine.
Profiles the raw Kaggle Payment Date Dataset and generates structured reports.
"""
import hashlib
import json
from pathlib import Path
from typing import Dict, Any
import numpy as np
import pandas as pd

def compute_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()

def inspect_dataset(data_path: Path) -> Dict[str, Any]:
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset file not found at: {data_path.resolve()}")

    file_hash = compute_sha256(data_path)
    df = pd.read_csv(data_path)

    total_records = len(df)
    total_columns = len(df.columns)

    # Missing value analysis
    missing_counts = df.isnull().sum().to_dict()
    missing_pcts = (df.isnull().sum() / total_records * 100).round(2).to_dict()

    # Duplicate analysis
    exact_duplicates = int(df.duplicated().sum())
    dup_doc_ids = int(df.duplicated(subset=["doc_id"]).sum()) if "doc_id" in df.columns else 0
    dup_invoice_ids = int(df.duplicated(subset=["invoice_id"]).sum()) if "invoice_id" in df.columns else 0

    # Unique entities
    unique_customers = int(df["cust_number"].nunique()) if "cust_number" in df.columns else 0
    unique_invoices = int(df["invoice_id"].nunique()) if "invoice_id" in df.columns else 0

    # Categorical distributions (top 10)
    currency_dist = df["invoice_currency"].value_counts(dropna=False).head(10).to_dict() if "invoice_currency" in df.columns else {}
    terms_dist = df["cust_payment_terms"].value_counts(dropna=False).head(10).to_dict() if "cust_payment_terms" in df.columns else {}
    business_dist = df["business_code"].value_counts(dropna=False).head(10).to_dict() if "business_code" in df.columns else {}

    # Amount statistics
    amount_col = "total_open_amount"
    amount_stats = {}
    if amount_col in df.columns:
        valid_amounts = pd.to_numeric(df[amount_col], errors="coerce").dropna()
        amount_stats = {
            "min": float(valid_amounts.min()),
            "max": float(valid_amounts.max()),
            "mean": float(round(valid_amounts.mean(), 2)),
            "median": float(round(valid_amounts.median(), 2)),
            "std": float(round(valid_amounts.std(), 2)),
            "negative_counts": int((valid_amounts < 0).sum()),
            "zero_counts": int((valid_amounts == 0).sum()),
        }

    # Date parsing exploration
    date_ranges = {}
    # posting_date
    if "posting_date" in df.columns:
        p_dates = pd.to_datetime(df["posting_date"], errors="coerce").dropna()
        if len(p_dates) > 0:
            date_ranges["posting_date"] = {
                "min": str(p_dates.min().date()),
                "max": str(p_dates.max().date()),
            }

    # due_in_date (usually YYYYMMDD numeric)
    if "due_in_date" in df.columns:
        d_dates = pd.to_datetime(df["due_in_date"].astype(str).str.split(".").str[0], format="%Y%m%d", errors="coerce").dropna()
        if len(d_dates) > 0:
            date_ranges["due_in_date"] = {
                "min": str(d_dates.min().date()),
                "max": str(d_dates.max().date()),
            }

    # clear_date
    if "clear_date" in df.columns:
        c_dates = pd.to_datetime(df["clear_date"], errors="coerce").dropna()
        if len(c_dates) > 0:
            date_ranges["clear_date"] = {
                "min": str(c_dates.min().date()),
                "max": str(c_dates.max().date()),
                "non_null_count": int(len(c_dates)),
                "null_count": int(df["clear_date"].isnull().sum()),
            }

    # Paid vs Open counts
    open_status = {}
    if "isOpen" in df.columns:
        open_status = {str(k): int(v) for k, v in df["isOpen"].value_counts(dropna=False).items()}

    profile = {
        "dataset_filename": data_path.name,
        "sha256_hash": file_hash,
        "total_records": total_records,
        "total_columns": total_columns,
        "columns": df.columns.tolist(),
        "column_dtypes": {k: str(v) for k, v in df.dtypes.items()},
        "missing_counts": missing_counts,
        "missing_percentages": missing_pcts,
        "exact_duplicates": exact_duplicates,
        "duplicate_doc_ids": dup_doc_ids,
        "duplicate_invoice_ids": dup_invoice_ids,
        "unique_customers": unique_customers,
        "unique_invoices": unique_invoices,
        "currency_distribution": currency_dist,
        "payment_terms_top10": terms_dist,
        "business_code_top10": business_dist,
        "amount_statistics": amount_stats,
        "date_ranges": date_ranges,
        "isOpen_distribution": open_status,
    }

    return profile

def generate_quality_report(profile: Dict[str, Any], output_path: Path):
    md = f"""# Data Quality and Profiling Report — Kaggle Payment Date Dataset

## 1. File Metadata
- **Filename**: `{profile['dataset_filename']}`
- **SHA-256 Hash**: `{profile['sha256_hash']}`
- **Total Records**: {profile['total_records']:,}
- **Total Columns**: {profile['total_columns']}

## 2. Records and Open/Closed Distribution
- **Closed Invoices (`isOpen=0`)**: {profile['isOpen_distribution'].get('0', 0):,}
- **Open Invoices (`isOpen=1`)**: {profile['isOpen_distribution'].get('1', 0):,}
- **Clear Date Non-null**: {profile['date_ranges'].get('clear_date', {}).get('non_null_count', 0):,}
- **Clear Date Null**: {profile['date_ranges'].get('clear_date', {}).get('null_count', 0):,}

## 3. Entity Counts & Duplicates
- **Unique Customers (`cust_number`)**: {profile['unique_customers']:,}
- **Unique Invoices (`invoice_id`)**: {profile['unique_invoices']:,}
- **Exact Duplicate Rows**: {profile['exact_duplicates']:,}
- **Duplicate Document IDs (`doc_id`)**: {profile['duplicate_doc_ids']:,}
- **Duplicate Invoice IDs (`invoice_id`)**: {profile['duplicate_invoice_ids']:,}

## 4. Invoice Amount Statistics (`total_open_amount`)
- **Min**: {profile['amount_stats']['min']:,.2f}
- **Max**: {profile['amount_stats']['max']:,.2f}
- **Mean**: {profile['amount_stats']['mean']:,.2f}
- **Median**: {profile['amount_stats']['median']:,.2f}
- **Standard Deviation**: {profile['amount_stats']['std']:,.2f}
- **Negative Amounts**: {profile['amount_stats']['negative_counts']}
- **Zero Amounts**: {profile['amount_stats']['zero_counts']}

## 5. Date Ranges
- **Posting Date Range**: {profile['date_ranges'].get('posting_date', {}).get('min', 'N/A')} to {profile['date_ranges'].get('posting_date', {}).get('max', 'N/A')}
- **Due Date Range**: {profile['date_ranges'].get('due_in_date', {}).get('min', 'N/A')} to {profile['date_ranges'].get('due_in_date', {}).get('max', 'N/A')}
- **Clear Date Range**: {profile['date_ranges'].get('clear_date', {}).get('min', 'N/A')} to {profile['date_ranges'].get('clear_date', {}).get('max', 'N/A')}

## 6. Currency Distribution (Top 10)
"""
    for curr, count in profile["currency_distribution"].items():
        md += f"- **{curr}**: {count:,}\n"

    md += "\n## 7. Missing Value Summary\n"
    for col, cnt in profile["missing_counts"].items():
        pct = profile["missing_percentages"][col]
        if cnt > 0:
            md += f"- **`{col}`**: {cnt:,} missing ({pct}%)\n"

    output_path.write_text(md, encoding="utf-8")

def main():
    backend_dir = Path(__file__).resolve().parent.parent
    raw_csv = backend_dir / "data" / "raw" / "payment_date_dataset" / "dataset.csv"
    ml_dir = backend_dir / "ml"
    ml_dir.mkdir(parents=True, exist_ok=True)

    print(f"Profiling dataset at: {raw_csv} ...")
    profile = inspect_dataset(raw_csv)
    # Fix key access for report
    profile["amount_stats"] = profile["amount_statistics"]

    profile_json_path = ml_dir / "dataset_profile.json"
    with open(profile_json_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)
    print(f"Saved profile to: {profile_json_path}")

    report_md_path = ml_dir / "data_quality_report.md"
    generate_quality_report(profile, report_md_path)
    print(f"Saved markdown quality report to: {report_md_path}")

    print("\nSummary:")
    print(f"  Total Records: {profile['total_records']:,}")
    print(f"  Closed (Cleared): {profile['isOpen_distribution'].get('0', 0):,}")
    print(f"  Open (Uncleared): {profile['isOpen_distribution'].get('1', 0):,}")
    print(f"  Exact Duplicates: {profile['exact_duplicates']:,}")

if __name__ == "__main__":
    main()
