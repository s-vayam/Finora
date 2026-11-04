#!/usr/bin/env python3
"""
Seed Data Validation Script for Finora.
Performs data integrity, accounting balance reconciliation, and foreign key audits.
Generates a structured validation report.
"""
import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
from typing import Dict, Any

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

EXPECTED_BENCHMARKS = {
    "customers.csv": 60,
    "invoices.csv": 899,
    "expenses.csv": 872,
    "cash_transactions.csv": 1722,
    "monthly_cashflow.csv": 36,
    "invoice_ml_training.csv": 873,
}

def validate_dataset(data_dir: Path) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data_directory": str(data_dir.resolve()),
        "file_existence": {},
        "row_counts": {},
        "duplicate_ids": {},
        "foreign_key_violations": [],
        "monetary_validations": {"errors": []},
        "balance_reconciliations": {"passed": True, "details": []},
        "transaction_reconciliations": {"passed": True, "details": []},
        "all_passed": True,
    }

    # 1. Check existence and benchmark counts
    for filename, expected_count in EXPECTED_BENCHMARKS.items():
        file_path = data_dir / filename
        exists = file_path.is_file()
        report["file_existence"][filename] = exists
        if not exists:
            report["all_passed"] = False
            report["row_counts"][filename] = {"actual": 0, "expected": expected_count, "matched": False}
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            actual_count = sum(1 for _ in reader)
            report["row_counts"][filename] = {
                "actual": actual_count,
                "expected": expected_count,
                "matched": (actual_count == expected_count),
            }
            if actual_count != expected_count:
                report["all_passed"] = False

    if not all(report["file_existence"].values()):
        return report

    # 2. Check Customers
    cust_path = data_dir / "customers.csv"
    customer_ids = set()
    with open(cust_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            cid = row["customer_id"].strip()
            if cid in customer_ids:
                report["duplicate_ids"].setdefault("customers", []).append(cid)
                report["all_passed"] = False
            customer_ids.add(cid)

    # 3. Check Invoices
    inv_path = data_dir / "invoices.csv"
    invoice_ids = set()
    with open(inv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            inv_id = row["invoice_id"].strip()
            if inv_id in invoice_ids:
                report["duplicate_ids"].setdefault("invoices", []).append(inv_id)
                report["all_passed"] = False
            invoice_ids.add(inv_id)

            cid = row["customer_id"].strip()
            if cid not in customer_ids:
                report["foreign_key_violations"].append(f"Invoice '{inv_id}' references non-existent customer '{cid}'")
                report["all_passed"] = False

            # Check monetary value
            try:
                amt = Decimal(row["invoice_amount"].strip())
                if amt <= 0:
                    report["monetary_validations"]["errors"].append(f"Invoice '{inv_id}' non-positive amount {amt}")
                    report["all_passed"] = False
            except Exception as e:
                report["monetary_validations"]["errors"].append(f"Invoice '{inv_id}' invalid decimal: {e}")
                report["all_passed"] = False

    # 4. Check Expenses
    exp_path = data_dir / "expenses.csv"
    expense_ids = set()
    with open(exp_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            exp_id = row["expense_id"].strip()
            if exp_id in expense_ids:
                report["duplicate_ids"].setdefault("expenses", []).append(exp_id)
                report["all_passed"] = False
            expense_ids.add(exp_id)

            linked = row.get("linked_invoice_id", "").strip()
            if linked and linked not in invoice_ids:
                report["foreign_key_violations"].append(f"Expense '{exp_id}' linked invoice '{linked}' not found")
                report["all_passed"] = False

            try:
                amt = Decimal(row["amount"].strip())
                if amt <= 0:
                    report["monetary_validations"]["errors"].append(f"Expense '{exp_id}' non-positive amount {amt}")
                    report["all_passed"] = False
            except Exception as e:
                report["monetary_validations"]["errors"].append(f"Expense '{exp_id}' invalid decimal: {e}")
                report["all_passed"] = False

    # 5. Check Cash Transactions & Aggregate by Month
    tx_path = data_dir / "cash_transactions.csv"
    tx_ids = set()
    tx_monthly_agg: Dict[str, Dict[str, Any]] = {}
    with open(tx_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            tx_id = row["transaction_id"].strip()
            if tx_id in tx_ids:
                report["duplicate_ids"].setdefault("cash_transactions", []).append(tx_id)
                report["all_passed"] = False
            tx_ids.add(tx_id)

            company = row.get("company_id", "").strip()
            if not company:
                report["foreign_key_violations"].append(f"Transaction '{tx_id}' missing company_id")
                report["all_passed"] = False

            linked = row.get("linked_invoice_id", "").strip()
            if linked and linked not in invoice_ids:
                report["foreign_key_violations"].append(f"Transaction '{tx_id}' linked invoice '{linked}' not found")
                report["all_passed"] = False

            try:
                amt = Decimal(row["amount"].strip())
                if amt <= 0:
                    report["monetary_validations"]["errors"].append(f"Transaction '{tx_id}' non-positive amount {amt}")
                    report["all_passed"] = False
            except Exception as e:
                report["monetary_validations"]["errors"].append(f"Transaction '{tx_id}' invalid decimal: {e}")
                report["all_passed"] = False
                continue

            # Monthly aggregation for cross-reconciliation
            month = row["transaction_date"].strip()[:7]
            if month not in tx_monthly_agg:
                tx_monthly_agg[month] = {
                    "inflows": Decimal("0"),
                    "outflows": Decimal("0"),
                    "inflow_count": 0,
                    "outflow_count": 0,
                }
            ttype = row["transaction_type"].strip()
            if ttype == "INFLOW":
                tx_monthly_agg[month]["inflows"] += amt
                tx_monthly_agg[month]["inflow_count"] += 1
            elif ttype == "OUTFLOW":
                tx_monthly_agg[month]["outflows"] += amt
                tx_monthly_agg[month]["outflow_count"] += 1
            else:
                report["monetary_validations"]["errors"].append(f"Transaction '{tx_id}' unknown type '{ttype}'")
                report["all_passed"] = False

    # 6. Check Monthly Cash Flow Reconciliations
    cf_path = data_dir / "monthly_cashflow.csv"
    with open(cf_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cf_rows = list(reader)

    prev_closing = None
    for idx, row in enumerate(cf_rows):
        m = row["month"].strip()
        opening = Decimal(row["opening_balance"].strip())
        inflows = Decimal(row["actual_inflows"].strip())
        outflows = Decimal(row["actual_outflows"].strip())
        net = Decimal(row["net_cash_flow"].strip())
        closing = Decimal(row["closing_balance"].strip())
        in_cnt = int(row["inflow_transactions"].strip())
        out_cnt = int(row["outflow_transactions"].strip())

        # Net balance arithmetic check: net = inflows - outflows
        if inflows - outflows != net:
            report["balance_reconciliations"]["passed"] = False
            report["balance_reconciliations"]["details"].append(
                f"Month {m}: Net mismatch. Inflows ({inflows}) - Outflows ({outflows}) != Net ({net})"
            )
            report["all_passed"] = False

        # Closing balance arithmetic check: closing = opening + net
        if opening + net != closing:
            report["balance_reconciliations"]["passed"] = False
            report["balance_reconciliations"]["details"].append(
                f"Month {m}: Closing mismatch. Opening ({opening}) + Net ({net}) != Closing ({closing})"
            )
            report["all_passed"] = False

        # Carryover check: Month N opening == Month N-1 closing
        if prev_closing is not None and prev_closing != opening:
            report["balance_reconciliations"]["passed"] = False
            report["balance_reconciliations"]["details"].append(
                f"Month {m}: Opening balance ({opening}) does not match prior month closing ({prev_closing})"
            )
            report["all_passed"] = False
        prev_closing = closing

        # Reconcile against underlying transactions
        tx_data = tx_monthly_agg.get(m, {
            "inflows": Decimal("0"),
            "outflows": Decimal("0"),
            "inflow_count": 0,
            "outflow_count": 0,
        })
        if abs(inflows - tx_data["inflows"]) > Decimal("0.01") or abs(outflows - tx_data["outflows"]) > Decimal("0.01"):
            report["transaction_reconciliations"]["passed"] = False
            report["transaction_reconciliations"]["details"].append(
                f"Month {m}: Amount mismatch. Cashflow (In: {inflows}, Out: {outflows}) vs Txns (In: {tx_data['inflows']}, Out: {tx_data['outflows']})"
            )
            report["all_passed"] = False

        if in_cnt != tx_data["inflow_count"] or out_cnt != tx_data["outflow_count"]:
            report["transaction_reconciliations"]["passed"] = False
            report["transaction_reconciliations"]["details"].append(
                f"Month {m}: Count mismatch. Cashflow (In: {in_cnt}, Out: {out_cnt}) vs Txns (In: {tx_data['inflow_count']}, Out: {tx_data['outflow_count']})"
            )
            report["all_passed"] = False

    return report

def main():
    parser = argparse.ArgumentParser(description="Validate Finora synthetic dataset files.")
    parser.add_argument(
        "--data-dir",
        type=str,
        default=str(BACKEND_DIR / "data" / "raw" / "finora_synthetic_data"),
        help="Path to folder containing raw synthetic CSV files",
    )
    args = parser.parse_args()
    data_dir = Path(args.data_dir)

    print("=" * 70)
    print("FINORA SYNTHETIC DATASET VALIDATION REPORT")
    print("=" * 70)
    print(f"Data Directory: {data_dir.resolve()}\n")

    report = validate_dataset(data_dir)

    print("1. RECORD COUNT BENCHMARKS:")
    print(f"  {'Filename':<28} {'Actual':<10} {'Expected':<10} {'Status':<10}")
    print("  " + "-" * 58)
    for fname, cnt_info in report["row_counts"].items():
        status_str = "MATCH" if cnt_info["matched"] else "FAIL"
        print(f"  {fname:<28} {cnt_info['actual']:<10} {cnt_info['expected']:<10} {status_str:<10}")

    print("\n2. PRIMARY KEY INTEGRITY:")
    if not report["duplicate_ids"]:
        print("  All primary keys unique across all tables (0 duplicates).")
    else:
        for tbl, dups in report["duplicate_ids"].items():
            print(f"  [FAIL] {tbl}: {len(dups)} duplicate IDs found!")

    print("\n3. FOREIGN KEY INTEGRITY:")
    if not report["foreign_key_violations"]:
        print("  All customer, invoice, and company relationships are 100% valid.")
    else:
        for viol in report["foreign_key_violations"][:10]:
            print(f"  [FAIL] {viol}")

    print("\n4. BALANCE RECONCILIATION (36 MONTHS):")
    if report["balance_reconciliations"]["passed"]:
        print("  Opening + Inflow - Outflow = Closing balance verified for all 36 months.")
    else:
        for err in report["balance_reconciliations"]["details"]:
            print(f"  [FAIL] {err}")

    print("\n5. TRANSACTION-TO-CASHFLOW RECONCILIATION:")
    if report["transaction_reconciliations"]["passed"]:
        print("  Transaction amounts and counts match monthly cashflow records perfectly.")
    else:
        for err in report["transaction_reconciliations"]["details"]:
            print(f"  [FAIL] {err}")

    print("\n" + "=" * 70)
    if report["all_passed"]:
        print("OVERALL RESULT: PASSED ALL SANITY CHECKS")
        print("=" * 70)
        sys.exit(0)
    else:
        print("OVERALL RESULT: FAILED VALIDATION CHECKS")
        print("=" * 70)
        sys.exit(1)

if __name__ == "__main__":
    main()
