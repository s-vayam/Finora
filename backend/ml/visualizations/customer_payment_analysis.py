"""
Plot customer-level payment behaviour from Finora's invoice dataset.

Run from any working directory:
    python backend/ml/visualizations/customer_payment_analysis.py

The script selects three customers with the most paid invoices (minimum 3),
then displays three Matplotlib figures based only on recorded invoice data.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BACKEND_DIR / "data" / "raw" / "finora_synthetic_data" / "invoices.csv"
MIN_PAID_INVOICES = 3


def load_customer_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Invoice dataset not found: {DATA_PATH}\n"
            "Run this script from the repository after checking the dataset path."
        )

    df = pd.read_csv(DATA_PATH)
    required = {
        "customer_id", "customer_name", "invoice_date", "due_date",
        "actual_payment_date", "invoice_amount", "status",
    }
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"invoices.csv is missing required columns: {sorted(missing)}")

    for col in ("invoice_date", "due_date", "actual_payment_date"):
        df[col] = pd.to_datetime(df[col], errors="coerce")

    df["invoice_amount"] = pd.to_numeric(df["invoice_amount"], errors="coerce")
    # Delay is measured against the contractual due date. Positive = late;
    # zero or negative = paid on/before due date.
    df["days_late"] = (df["actual_payment_date"] - df["due_date"]).dt.days
    paid = df[df["actual_payment_date"].notna()].copy()
    return df, paid


def choose_customers(paid: pd.DataFrame) -> list[str]:
    counts = paid.groupby("customer_id").size().sort_values(ascending=False)
    selected = counts[counts >= MIN_PAID_INVOICES].head(3).index.tolist()
    if len(selected) < 3:
        raise ValueError(
            "Could not find three customers with at least "
            f"{MIN_PAID_INVOICES} paid invoices each."
        )
    return selected


def main() -> None:
    _, paid = load_customer_data()
    customer_ids = choose_customers(paid)
    sample = paid[paid["customer_id"].isin(customer_ids)].copy()
    sample = sample.sort_values("invoice_date")

    names = (
        sample[["customer_id", "customer_name"]]
        .drop_duplicates("customer_id")
        .set_index("customer_id")["customer_name"]
        .to_dict()
    )

    print("\nSelected customers (ranked by number of paid invoices):")
    for customer_id in customer_ids:
        count = int((sample["customer_id"] == customer_id).sum())
        print(f"  {customer_id} - {names.get(customer_id, customer_id)}: {count} paid invoices")

    # Graph 1: payment delay over time for the selected customers.
    fig, ax = plt.subplots(figsize=(12, 6))
    for customer_id in customer_ids:
        rows = sample[sample["customer_id"] == customer_id].dropna(
            subset=["invoice_date", "days_late"]
        )
        ax.plot(
            rows["invoice_date"], rows["days_late"],
            marker="o", markersize=3, linewidth=1.5,
            label=f"{names.get(customer_id, customer_id)} ({customer_id})",
        )
    ax.axhline(0, linestyle="--", linewidth=1, label="Due date (0 days)")
    ax.set_title("Customer Payment Delay Over Time")
    ax.set_xlabel("Invoice date")
    ax.set_ylabel("Days relative to due date (positive = late)")
    ax.legend()
    ax.grid(True, alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()

    # Graph 2: invoice amount history for the same customers.
    fig, ax = plt.subplots(figsize=(12, 6))
    for customer_id in customer_ids:
        rows = sample[sample["customer_id"] == customer_id].dropna(
            subset=["invoice_date", "invoice_amount"]
        )
        ax.plot(
            rows["invoice_date"], rows["invoice_amount"],
            marker="o", markersize=3, linewidth=1.5,
            label=f"{names.get(customer_id, customer_id)} ({customer_id})",
        )
    ax.set_title("Customer Invoice Amounts Over Time")
    ax.set_xlabel("Invoice date")
    ax.set_ylabel("Invoice amount")
    ax.legend()
    ax.grid(True, alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()

    # Graph 3: on-time vs late counts. Early payments count as on-time.
    summary = []
    for customer_id in customer_ids:
        rows = sample[sample["customer_id"] == customer_id].dropna(subset=["days_late"])
        summary.append({
            "customer": f"{names.get(customer_id, customer_id)}\n{customer_id}",
            "On time / early": int((rows["days_late"] <= 0).sum()),
            "Late": int((rows["days_late"] > 0).sum()),
        })
    chart = pd.DataFrame(summary).set_index("customer")
    ax = chart.plot(kind="bar", figsize=(10, 6), rot=0)
    ax.set_title("On-time vs Late Payments by Customer")
    ax.set_xlabel("Customer")
    ax.set_ylabel("Number of paid invoices")
    ax.legend(title="Payment outcome")
    ax.grid(axis="y", alpha=0.25)
    plt.tight_layout()

    plt.show()


if __name__ == "__main__":
    main()
