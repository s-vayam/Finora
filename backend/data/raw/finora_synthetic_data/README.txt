FINORA SYNTHETIC DATA PACKAGE

Company: FINORA_DEMO
Period: 2023-01-01 to 2025-12-31 (36 calendar months)
Currency: INR
Random seed: 42

Files:
- customers.csv: simulated customer master data
- invoices.csv: invoices, observed payments and still-open invoices
- invoice_ml_training.csv: paid invoices only, with historical-as-of-invoice features and target labels
- expenses.csv: recurring and invoice-linked expenses
- cash_transactions.csv: actual cash receipts and payments only
- monthly_cashflow.csv: monthly aggregation of the same cash_transactions ledger

Important modelling notes:
1. All files belong to the same simulated company and calendar period.
2. Cash inflows use actual simulated payment dates, not invoice issue dates.
3. Cash outflows use simulated expense payment dates.
4. Open invoices have blank actual_payment_date and are NOT assigned fake training labels.
5. invoice_ml_training.csv contains only invoices whose payment outcome is observable within the simulation window.
6. Customer historical features are calculated only from payments settled before the current invoice date.
7. This is synthetic demonstration data, not real company data. Do not claim real-world model accuracy from it.
8. Use the public 50K Payment Date dataset for primary payment-model training if its licence/terms permit your intended use; use this package to test the Finora integration and cash-flow timeline.

Regenerate:
  python generate_finora_data.py --out data/finora --start 2023-01-01 --months 36 --seed 42
