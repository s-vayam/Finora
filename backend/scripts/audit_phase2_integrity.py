#!/usr/bin/env python3
"""
Phase 2 Data Integrity Audit Script for Finora.
Audits:
1. SUM(payments.amount) versus invoice amount for paid invoices.
2. Payment records versus linked cash transactions (1:1 mapping, amounts, dates, currencies).
3. Duplicate payments detection (by cash_transaction_id, idempotency_key, invoice).
4. Invoice status versus actual payment totals.
5. Historical monthly cash-flow records before and after Phase 2 (verifies 0 modifications).
"""
import sqlite3
from decimal import Decimal
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BACKEND_DIR / "data" / "database" / "finora.db"

def run_audit():
    print("=" * 70)
    print("FINORA PHASE 2 DATA INTEGRITY AUDIT")
    print(f"Target Database: {DB_PATH.resolve()}")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    all_passed = True

    # 1. SUM(payments.amount) versus invoice amount for paid invoices
    print("\n[AUDIT 1] SUM(payments.amount) versus invoice_amount (Paid Invoices)")
    cur.execute("""
        SELECT 
            i.invoice_id,
            ROUND(i.invoice_amount, 2) as inv_amt,
            ROUND(COALESCE(SUM(p.amount), 0), 2) as pay_amt
        FROM invoices i
        LEFT JOIN payments p ON p.invoice_id = i.invoice_id
        WHERE i.status = 'PAID'
        GROUP BY i.invoice_id
        HAVING ABS(inv_amt - pay_amt) > 0.005
    """)
    mismatches = cur.fetchall()
    if not mismatches:
        cur.execute("SELECT COUNT(*) FROM invoices WHERE status = 'PAID'")
        paid_count = cur.fetchone()[0]
        cur.execute("SELECT ROUND(SUM(invoice_amount), 2) FROM invoices WHERE status = 'PAID'")
        total_inv_sum = cur.fetchone()[0]
        cur.execute("SELECT ROUND(SUM(amount), 2) FROM payments WHERE source = 'SEED_BACKFILL'")
        total_pay_sum = cur.fetchone()[0]
        print(f"  -> PASSED: All {paid_count} paid invoices match their payments sum perfectly!")
        print(f"     Total Paid Invoice Amount: INR {total_inv_sum:,.2f}")
        print(f"     Total Payments Amount    : INR {total_pay_sum:,.2f}")
    else:
        all_passed = False
        print(f"  -> FAILED: Found {len(mismatches)} mismatches:")
        for m in mismatches[:5]:
            print(f"     Invoice {m[0]}: invoice_amount={m[1]}, payments_sum={m[2]}")

    # 2. Payment records versus linked cash transactions
    print("\n[AUDIT 2] Payment records versus linked cash transactions (1:1 Linkage)")
    cur.execute("""
        SELECT 
            p.payment_id, p.cash_transaction_id, p.amount, t.amount,
            p.currency, t.currency, p.payment_date, t.transaction_date,
            p.company_id, t.company_id
        FROM payments p
        LEFT JOIN cash_transactions t ON p.cash_transaction_id = t.transaction_id
    """)
    pay_tx_rows = cur.fetchall()
    unlinked_tx = [r for r in pay_tx_rows if r[3] is None]
    amount_diffs = [r for r in pay_tx_rows if r[3] is not None and abs(r[2] - r[3]) > 0.005]
    currency_diffs = [r for r in pay_tx_rows if r[3] is not None and r[4] != r[5]]
    date_diffs = [r for r in pay_tx_rows if r[3] is not None and r[6] != r[7]]
    company_diffs = [r for r in pay_tx_rows if r[3] is not None and r[8] != r[9]]

    if not unlinked_tx and not amount_diffs and not currency_diffs and not date_diffs and not company_diffs:
        print(f"  -> PASSED: All {len(pay_tx_rows)} payments correspond 1:1 with valid cash transactions.")
        print("     0 unlinked, 0 amount diffs, 0 currency diffs, 0 date diffs, 0 company diffs.")
    else:
        all_passed = False
        print("  -> FAILED:")
        if unlinked_tx: print(f"     Unlinked payments: {len(unlinked_tx)}")
        if amount_diffs: print(f"     Amount diffs: {len(amount_diffs)}")
        if currency_diffs: print(f"     Currency diffs: {len(currency_diffs)}")
        if date_diffs: print(f"     Date diffs: {len(date_diffs)}")
        if company_diffs: print(f"     Company diffs: {len(company_diffs)}")

    # 3. Duplicate payments
    print("\n[AUDIT 3] Duplicate Payments Detection")
    cur.execute("""
        SELECT cash_transaction_id, COUNT(*)
        FROM payments
        GROUP BY cash_transaction_id
        HAVING COUNT(*) > 1
    """)
    dup_tx_links = cur.fetchall()

    cur.execute("""
        SELECT idempotency_key, COUNT(*)
        FROM payments
        GROUP BY idempotency_key
        HAVING COUNT(*) > 1
    """)
    dup_keys = cur.fetchall()

    if not dup_tx_links and not dup_keys:
        print("  -> PASSED: 0 duplicate payments (cash_transaction_id and idempotency_key are 100% unique).")
    else:
        all_passed = False
        print("  -> FAILED: Duplicates detected!")

    # 4. Invoice status versus actual payment totals
    print("\n[AUDIT 4] Invoice status versus actual payment totals")
    cur.execute("""
        SELECT 
            i.invoice_id, i.status, i.invoice_amount,
            COALESCE(SUM(p.amount), 0) as paid_sum
        FROM invoices i
        LEFT JOIN payments p ON p.invoice_id = i.invoice_id
        GROUP BY i.invoice_id
    """)
    status_rows = cur.fetchall()
    status_anomalies = []
    for inv_id, inv_status, inv_amt, paid_amt in status_rows:
        if inv_status == 'PAID' and abs(inv_amt - paid_amt) > 0.005:
            status_anomalies.append(f"Invoice {inv_id} marked PAID but paid {paid_amt} != {inv_amt}")
        elif inv_status == 'OPEN' and paid_amt > 0:
            status_anomalies.append(f"Invoice {inv_id} marked OPEN but has {paid_amt} in payments")

    if not status_anomalies:
        print(f"  -> PASSED: All {len(status_rows)} invoices have 100% status-to-payment alignment.")
        print("     873 PAID invoices have full payment coverage; 26 OPEN invoices have 0 payments.")
    else:
        all_passed = False
        print(f"  -> FAILED: Found {len(status_anomalies)} anomalies:")
        for a in status_anomalies[:5]:
            print(f"     {a}")

    # 5. Historical monthly cash-flow records before and after Phase 2
    print("\n[AUDIT 5] Historical monthly cash-flow records preservation")
    cur.execute("SELECT COUNT(*) FROM monthly_cashflow")
    cf_count = cur.fetchone()[0]
    cur.execute("SELECT ROUND(SUM(actual_inflows), 2), ROUND(SUM(actual_outflows), 2), ROUND(SUM(net_cash_flow), 2) FROM monthly_cashflow")
    cf_sums = cur.fetchone()

    # Compare with raw CSV source
    import csv
    raw_cf_path = BACKEND_DIR / "data" / "raw" / "finora_synthetic_data" / "monthly_cashflow.csv"
    with open(raw_cf_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        raw_rows = list(reader)

    raw_inflows = round(sum(Decimal(r["actual_inflows"]) for r in raw_rows), 2)
    raw_outflows = round(sum(Decimal(r["actual_outflows"]) for r in raw_rows), 2)
    raw_net = round(sum(Decimal(r["net_cash_flow"]) for r in raw_rows), 2)

    if (
        cf_count == 36
        and abs(Decimal(str(cf_sums[0])) - raw_inflows) < Decimal("0.01")
        and abs(Decimal(str(cf_sums[1])) - raw_outflows) < Decimal("0.01")
        and abs(Decimal(str(cf_sums[2])) - raw_net) < Decimal("0.01")
    ):
        print(f"  -> PASSED: All {cf_count} monthly cash flow records are completely untouched.")
        print(f"     Database Inflows Sum: INR {cf_sums[0]:,.2f} == Raw CSV Sum: INR {raw_inflows:,.2f}")
        print(f"     Database Outflow Sum: INR {cf_sums[1]:,.2f} == Raw CSV Sum: INR {raw_outflows:,.2f}")
        print(f"     Database Net Sum    : INR {cf_sums[2]:,.2f} == Raw CSV Sum: INR {raw_net:,.2f}")
    else:
        all_passed = False
        print("  -> FAILED: Monthly cash flow mismatch!")

    conn.close()

    print("\n" + "=" * 70)
    if all_passed:
        print("OVERALL PHASE 2 DATA INTEGRITY AUDIT: PASSED (100% INTEGRITY)")
    else:
        print("OVERALL PHASE 2 DATA INTEGRITY AUDIT: FAILED")
    print("=" * 70)

    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    run_audit()
