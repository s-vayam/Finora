import sqlite3
import datetime
from pathlib import Path

def backup_sqlite():
    db_path = Path("backend/data/database/finora.db")
    if not db_path.exists():
        db_path = Path("data/database/finora.db")
    
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"finora_pre_phase6_{now_str}.db"
    
    print(f"Backing up database from {db_path} to {backup_path}...")
    source_conn = sqlite3.connect(db_path)
    dest_conn = sqlite3.connect(backup_path)
    
    with dest_conn:
        source_conn.backup(dest_conn)
        
    source_conn.close()
    dest_conn.close()
    
    print(f"Backup created successfully: {backup_path.stat().st_size} bytes")
    
    # Validation
    verify_conn = sqlite3.connect(backup_path)
    cursor = verify_conn.cursor()
    cursor.execute("PRAGMA integrity_check;")
    integrity = cursor.fetchall()
    print("Integrity check:", integrity)
    assert integrity == [("ok",)], f"Integrity check failed: {integrity}"
    
    tables = [
        "companies", "customers", "invoices", "payments", "expenses",
        "cash_transactions", "monthly_cashflow", "cash_balance_snapshots",
        "collection_forecast_overrides", "expense_forecast_assumptions",
        "cashflow_forecast_runs", "fx_rate_observations", "fx_fetch_runs",
        "fx_forecasts", "fx_scenario_runs"
    ]
    
    print("\nValidating table row counts:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count}")
        
    cursor.execute("SELECT SUM(amount) FROM payments")
    total_payments = cursor.fetchone()[0]
    print(f"\nTotal payments: {total_payments}")
    
    verify_conn.close()
    print("\nBackup verification completed successfully!")
    return backup_path

if __name__ == "__main__":
    backup_sqlite()

