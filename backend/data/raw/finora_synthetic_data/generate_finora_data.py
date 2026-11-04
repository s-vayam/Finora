#!/usr/bin/env python3
"""Generate a coherent synthetic financial history for a demo Finora company.

Outputs:
  customers.csv
  invoices.csv
  invoice_ml_training.csv   (only invoices with observed payment outcomes)
  expenses.csv
  cash_transactions.csv    (actual cash events only)
  monthly_cashflow.csv     (36 aligned calendar months)

All records belong to one simulated company, FINORA_DEMO, and use INR so the
cash-flow ledger can be aggregated without mixing currencies. This is demo /
engineering data, not real company data and not evidence of model accuracy.
"""

from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean

COMPANY_ID = "FINORA_DEMO"
CURRENCY = "INR"


def month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def add_months(d: date, months: int) -> date:
    idx = d.year * 12 + (d.month - 1) + months
    year, month0 = divmod(idx, 12)
    return date(year, month0 + 1, 1)


def daterange_months(start: date, months: int):
    for i in range(months):
        yield add_months(start, i)


def random_date_in_month(rng: random.Random, month: date) -> date:
    next_month = add_months(month, 1)
    days = (next_month - month).days
    return month + timedelta(days=rng.randrange(days))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def money(x: float) -> float:
    return round(max(0.0, x), 2)


def generate(out_dir: Path, start: date, months: int, seed: int) -> dict[str, int]:
    rng = random.Random(seed)
    end_exclusive = add_months(start, months)
    end_date = end_exclusive - timedelta(days=1)

    # Customer-level behavioural tendencies are latent properties used to
    # simulate payment behaviour. They are NOT included as model input fields.
    customers: list[dict] = []
    profiles = [
        ("reliable", 0.10, -2.0),
        ("average", 0.30, 4.0),
        ("slow_payer", 0.58, 12.0),
        ("high_risk", 0.78, 20.0),
    ]
    for i in range(1, 61):
        profile = rng.choices(profiles, weights=[35, 40, 18, 7], k=1)[0]
        customers.append({
            "customer_id": f"CUST{i:03d}",
            "company_id": COMPANY_ID,
            "customer_name": f"Customer {i:03d}",
            "country": rng.choice(["India", "UAE", "Singapore", "Germany", "UK"]),
            "industry": rng.choice(["Textiles", "Electronics", "Machinery", "Chemicals", "Food"]),
            "default_payment_terms_days": rng.choice([15, 30, 30, 45, 60]),
            "_profile": profile[0],
            "_late_probability": profile[1],
            "_mean_delay": profile[2],
        })

    # Generate invoice issue events over the full period.
    invoice_events = []
    invoice_counter = 1
    for month in daterange_months(start, months):
        # Mild business seasonality: higher volume around quarter/year end.
        seasonal = 1.18 if month.month in (3, 6, 9, 12) else 1.0
        n_invoices = max(8, int(rng.randint(18, 29) * seasonal))
        for _ in range(n_invoices):
            issue_date = random_date_in_month(rng, month)
            customer = rng.choice(customers)
            terms = customer["default_payment_terms_days"]
            # Log-normal amounts give a realistic skew: many modest invoices,
            # a smaller number of larger ones.
            amount = min(900000.0, max(18000.0, rng.lognormvariate(11.65, 0.62)))
            invoice_events.append((issue_date, invoice_counter, customer, terms, money(amount)))
            invoice_counter += 1
    invoice_events.sort(key=lambda x: (x[0], x[1]))

    invoices: list[dict] = []
    invoice_ml_rows: list[dict] = []
    paid_invoice_payments: list[dict] = []
    generated_for_customer: dict[str, list[dict]] = defaultdict(list)

    for issue_date, seq, customer, terms, amount in invoice_events:
        due_date = issue_date + timedelta(days=terms)
        prior_paid = [r for r in generated_for_customer[customer["customer_id"]]
                      if r["actual_payment_date"] and r["actual_payment_date"] < issue_date]
        if prior_paid:
            prior_delays = [r["days_late"] for r in prior_paid]
            hist_late_rate = sum(1 for d in prior_delays if d > 0) / len(prior_delays)
            hist_avg_delay = mean(prior_delays)
            hist_avg_amount = mean(r["amount"] for r in prior_paid)
            hist_count = len(prior_paid)
        else:
            # Cold-start prior: neutral defaults, not a fabricated customer score.
            hist_late_rate = 0.30
            hist_avg_delay = 3.0
            hist_avg_amount = amount
            hist_count = 0

        # Latent payment outcome: customer tendency + moderate amount/season effects.
        amount_effect = 0.06 if amount > 350000 else 0.0
        quarter_end_effect = 0.04 if issue_date.month in (3, 6, 9, 12) else 0.0
        p_late = min(0.94, max(0.03, customer["_late_probability"] + amount_effect + quarter_end_effect))
        is_late = rng.random() < p_late
        if is_late:
            delay_days = max(1, int(rng.gauss(customer["_mean_delay"] + 5, 7)))
        else:
            delay_days = int(rng.gauss(-1.5, 2.2))
        delay_days = max(-7, min(60, delay_days))
        payment_date = due_date + timedelta(days=delay_days)

        # If settlement would occur after the simulated window, right-censor it:
        # keep the invoice OPEN and do not invent a label or cash receipt.
        is_observed_paid = payment_date <= end_date
        invoice_id = f"INV-{seq:06d}"
        status = "PAID" if is_observed_paid else "OPEN"
        actual_payment_date = payment_date.isoformat() if is_observed_paid else ""
        days_late = delay_days if is_observed_paid else ""

        invoice_row = {
            "invoice_id": invoice_id,
            "company_id": COMPANY_ID,
            "customer_id": customer["customer_id"],
            "customer_name": customer["customer_name"],
            "country": customer["country"],
            "industry": customer["industry"],
            "invoice_date": issue_date.isoformat(),
            "due_date": due_date.isoformat(),
            "actual_payment_date": actual_payment_date,
            "payment_terms_days": terms,
            "invoice_amount": amount,
            "currency": CURRENCY,
            "status": status,
            "historical_invoice_count": hist_count,
            "historical_late_rate": round(hist_late_rate, 4),
            "historical_avg_days_late": round(hist_avg_delay, 2),
            "historical_avg_invoice_amount": round(hist_avg_amount, 2),
            "amount_vs_customer_avg": round(amount / hist_avg_amount, 4) if hist_avg_amount else 1.0,
        }
        invoices.append(invoice_row)

        if is_observed_paid:
            ml_row = {
                "invoice_id": invoice_id,
                "invoice_amount": amount,
                "payment_terms_days": terms,
                "customer_country": customer["country"],
                "customer_industry": customer["industry"],
                "invoice_month": issue_date.month,
                "invoice_quarter": (issue_date.month - 1) // 3 + 1,
                "historical_invoice_count": hist_count,
                "historical_late_rate": round(hist_late_rate, 4),
                "historical_avg_days_late": round(hist_avg_delay, 2),
                "amount_vs_customer_avg": round(amount / hist_avg_amount, 4) if hist_avg_amount else 1.0,
                "target_late_payment": 1 if delay_days > 0 else 0,
                "target_days_late": delay_days,
            }
            invoice_ml_rows.append(ml_row)
            paid_invoice_payments.append({
                "transaction_id": f"TXN-IN-{seq:06d}",
                "company_id": COMPANY_ID,
                "transaction_date": payment_date.isoformat(),
                "transaction_type": "INFLOW",
                "category": "CUSTOMER_PAYMENT",
                "amount": amount,
                "currency": CURRENCY,
                "linked_invoice_id": invoice_id,
                "counterparty_id": customer["customer_id"],
                "description": f"Payment received for {invoice_id}",
            })

        generated_for_customer[customer["customer_id"]].append({
            "actual_payment_date": payment_date if is_observed_paid else None,
            "days_late": delay_days if is_observed_paid else None,
            "amount": amount,
        })

    # Expenses share the exact same company and calendar window. Recurring
    # operating bills + variable supplier/production bills are generated.
    expenses: list[dict] = []
    cash_outflows: list[dict] = []
    expense_counter = 1

    for month in daterange_months(start, months):
        # Recurring costs in INR (moderate scale for a small/mid-sized exporter).
        recurring = [
            ("SALARIES", rng.uniform(360000, 470000), 5),
            ("RENT", rng.uniform(105000, 135000), 3),
            ("UTILITIES", rng.uniform(35000, 65000), 12),
            ("SOFTWARE_ADMIN", rng.uniform(45000, 80000), 18),
            ("INSURANCE_COMPLIANCE", rng.uniform(25000, 55000), 22),
        ]
        for category, amount, day in recurring:
            bill_date = date(month.year, month.month, min(day, (add_months(month, 1) - timedelta(days=1)).day))
            due = bill_date + timedelta(days=7)
            paid = due + timedelta(days=rng.choice([-1, 0, 0, 1, 2]))
            expense_id = f"EXP-{expense_counter:06d}"
            expense_counter += 1
            row = {
                "expense_id": expense_id,
                "company_id": COMPANY_ID,
                "expense_date": bill_date.isoformat(),
                "due_date": due.isoformat(),
                "actual_payment_date": paid.isoformat() if paid <= end_date else "",
                "category": category,
                "amount": money(amount),
                "currency": CURRENCY,
                "status": "PAID" if paid <= end_date else "OPEN",
                "linked_invoice_id": "",
            }
            expenses.append(row)
            if paid <= end_date:
                cash_outflows.append({
                    "transaction_id": f"TXN-OUT-{expense_counter:06d}",
                    "company_id": COMPANY_ID,
                    "transaction_date": paid.isoformat(),
                    "transaction_type": "OUTFLOW",
                    "category": category,
                    "amount": money(amount),
                    "currency": CURRENCY,
                    "linked_invoice_id": "",
                    "counterparty_id": "",
                    "description": f"{category} expense {expense_id}",
                })

    # Variable production/procurement costs tied to invoices. These are paid
    # after the invoice date and therefore create correlated outflows.
    for inv in invoices:
        inv_date = date.fromisoformat(inv["invoice_date"])
        if rng.random() < 0.78:
            ratio = rng.uniform(0.42, 0.62)
            amount = money(inv["invoice_amount"] * ratio)
            bill_date = inv_date + timedelta(days=rng.randint(1, 5))
            due = bill_date + timedelta(days=rng.choice([15, 30, 30, 45]))
            paid = due + timedelta(days=max(-2, int(rng.gauss(2, 3))))
            expense_id = f"EXP-{expense_counter:06d}"
            expense_counter += 1
            is_paid = paid <= end_date
            row = {
                "expense_id": expense_id,
                "company_id": COMPANY_ID,
                "expense_date": bill_date.isoformat(),
                "due_date": due.isoformat(),
                "actual_payment_date": paid.isoformat() if is_paid else "",
                "category": "PRODUCTION_AND_SUPPLIER_COST",
                "amount": amount,
                "currency": CURRENCY,
                "status": "PAID" if is_paid else "OPEN",
                "linked_invoice_id": inv["invoice_id"],
            }
            expenses.append(row)
            if is_paid:
                cash_outflows.append({
                    "transaction_id": f"TXN-OUT-{expense_counter:06d}",
                    "company_id": COMPANY_ID,
                    "transaction_date": paid.isoformat(),
                    "transaction_type": "OUTFLOW",
                    "category": "PRODUCTION_AND_SUPPLIER_COST",
                    "amount": amount,
                    "currency": CURRENCY,
                    "linked_invoice_id": inv["invoice_id"],
                    "counterparty_id": "SUPPLIER_POOL",
                    "description": f"Supplier cost linked to {inv['invoice_id']}",
                })

    transactions = paid_invoice_payments + cash_outflows
    transactions.sort(key=lambda r: (r["transaction_date"], r["transaction_id"]))

    # Aggregate all actual cash events on one monthly calendar.
    monthly_totals = defaultdict(lambda: {"inflows": 0.0, "outflows": 0.0, "inflow_count": 0, "outflow_count": 0})
    for txn in transactions:
        dt = date.fromisoformat(txn["transaction_date"])
        key = f"{dt.year:04d}-{dt.month:02d}"
        typ = txn["transaction_type"]
        if typ == "INFLOW":
            monthly_totals[key]["inflows"] += float(txn["amount"])
            monthly_totals[key]["inflow_count"] += 1
        else:
            monthly_totals[key]["outflows"] += float(txn["amount"])
            monthly_totals[key]["outflow_count"] += 1

    opening_balance = 2500000.0
    monthly_cashflow = []
    for month in daterange_months(start, months):
        key = f"{month.year:04d}-{month.month:02d}"
        vals = monthly_totals[key]
        inflows = round(vals["inflows"], 2)
        outflows = round(vals["outflows"], 2)
        net = round(inflows - outflows, 2)
        closing = round(opening_balance + net, 2)
        monthly_cashflow.append({
            "company_id": COMPANY_ID,
            "month": key,
            "opening_balance": round(opening_balance, 2),
            "actual_inflows": inflows,
            "actual_outflows": outflows,
            "net_cash_flow": net,
            "closing_balance": closing,
            "inflow_transactions": vals["inflow_count"],
            "outflow_transactions": vals["outflow_count"],
            "currency": CURRENCY,
        })
        opening_balance = closing

    customers_out = [{k: v for k, v in c.items() if not k.startswith("_")} for c in customers]

    write_csv(out_dir / "customers.csv", customers_out, list(customers_out[0].keys()))
    write_csv(out_dir / "invoices.csv", invoices, list(invoices[0].keys()))
    write_csv(out_dir / "invoice_ml_training.csv", invoice_ml_rows, list(invoice_ml_rows[0].keys()))
    write_csv(out_dir / "expenses.csv", expenses, list(expenses[0].keys()))
    write_csv(out_dir / "cash_transactions.csv", transactions, list(transactions[0].keys()))
    write_csv(out_dir / "monthly_cashflow.csv", monthly_cashflow, list(monthly_cashflow[0].keys()))

    readme = f"""FINORA SYNTHETIC DATA PACKAGE\n\nCompany: {COMPANY_ID}\nPeriod: {start.isoformat()} to {end_date.isoformat()} ({months} calendar months)\nCurrency: INR\nRandom seed: {seed}\n\nFiles:\n- customers.csv: simulated customer master data\n- invoices.csv: invoices, observed payments and still-open invoices\n- invoice_ml_training.csv: paid invoices only, with historical-as-of-invoice features and target labels\n- expenses.csv: recurring and invoice-linked expenses\n- cash_transactions.csv: actual cash receipts and payments only\n- monthly_cashflow.csv: monthly aggregation of the same cash_transactions ledger\n\nImportant modelling notes:\n1. All files belong to the same simulated company and calendar period.\n2. Cash inflows use actual simulated payment dates, not invoice issue dates.\n3. Cash outflows use simulated expense payment dates.\n4. Open invoices have blank actual_payment_date and are NOT assigned fake training labels.\n5. invoice_ml_training.csv contains only invoices whose payment outcome is observable within the simulation window.\n6. Customer historical features are calculated only from payments settled before the current invoice date.\n7. This is synthetic demonstration data, not real company data. Do not claim real-world model accuracy from it.\n8. Use the public 50K Payment Date dataset for primary payment-model training if its licence/terms permit your intended use; use this package to test the Finora integration and cash-flow timeline.\n\nRegenerate:\n  python generate_finora_data.py --out data/finora --start 2023-01-01 --months 36 --seed 42\n"""
    (out_dir / "README.txt").write_text(readme, encoding="utf-8")

    return {
        "customers": len(customers_out),
        "invoices": len(invoices),
        "paid_training_rows": len(invoice_ml_rows),
        "expenses": len(expenses),
        "cash_transactions": len(transactions),
        "monthly_rows": len(monthly_cashflow),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate aligned synthetic Finora financial data.")
    parser.add_argument("--out", default="data/finora", help="Output directory")
    parser.add_argument("--start", default="2023-01-01", help="Start month/date (YYYY-MM-DD)")
    parser.add_argument("--months", type=int, default=36, help="Number of calendar months")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()
    if args.months < 3:
        parser.error("--months must be at least 3")
    start = date.fromisoformat(args.start)
    out_dir = Path(args.out)
    counts = generate(out_dir, start, args.months, args.seed)
    print(f"Generated Finora synthetic data in: {out_dir.resolve()}")
    for name, count in counts.items():
        print(f"  {name}: {count:,}")
    print("\nAll cash events are aligned to one company, one currency, and one calendar timeline.")
    print("Reminder: synthetic data is for prototype/demo validation, not real-world accuracy claims.")


if __name__ == "__main__":
    main()
