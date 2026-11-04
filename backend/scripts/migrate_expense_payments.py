import sqlite3

def run_migration():
    con = sqlite3.connect('data/database/finora.db')
    cur = con.cursor()

    # 1. Update expenses table
    cols_exp = [c[1] for c in cur.execute('PRAGMA table_info(expenses)').fetchall()]
    print('Expenses cols before:', cols_exp)
    if 'amount_paid' not in cols_exp:
        cur.execute('ALTER TABLE expenses ADD COLUMN amount_paid NUMERIC(15, 2) DEFAULT 0.00')
        print('Added amount_paid to expenses')

    # Backfill amount_paid for historical expenses
    cur.execute("UPDATE expenses SET amount_paid = amount WHERE status = 'PAID'")
    cur.execute("UPDATE expenses SET amount_paid = 0.00 WHERE status != 'PAID'")

    # 2. Update cash_transactions table
    cols_tx = [c[1] for c in cur.execute('PRAGMA table_info(cash_transactions)').fetchall()]
    print('Cash transactions cols before:', cols_tx)
    if 'linked_expense_id' not in cols_tx:
        cur.execute('ALTER TABLE cash_transactions ADD COLUMN linked_expense_id VARCHAR(50)')
        print('Added linked_expense_id to cash_transactions')

    # 3. Create expense_payments table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS expense_payments (
        payment_id VARCHAR(50) PRIMARY KEY,
        company_id VARCHAR(50) NOT NULL REFERENCES companies(company_id),
        expense_id VARCHAR(50) NOT NULL REFERENCES expenses(expense_id),
        payment_date DATE NOT NULL,
        amount NUMERIC(15, 2) NOT NULL,
        currency VARCHAR(10) NOT NULL DEFAULT 'INR',
        payment_method VARCHAR(50) NOT NULL DEFAULT 'BANK_TRANSFER',
        reference_number VARCHAR(100),
        notes VARCHAR(500),
        cash_transaction_id VARCHAR(50) REFERENCES cash_transactions(transaction_id),
        idempotency_key VARCHAR(100) UNIQUE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_expense_payments_expense ON expense_payments(expense_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_expense_payments_company ON expense_payments(company_id)')

    con.commit()
    print('Migration complete!')
    sample = cur.execute('SELECT expense_id, amount, amount_paid, status FROM expenses LIMIT 3').fetchall()
    print('Sample expenses after migration:', sample)
    con.close()

if __name__ == '__main__':
    run_migration()

