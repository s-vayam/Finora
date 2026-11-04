import shutil
import sqlite3
from pathlib import Path
from alembic.config import Config
from alembic import command

def test_migration_on_copy():
    src_db = Path("data/database/finora.db")
    test_db = Path("data/database/test_migration_004.db")
    
    if test_db.exists():
        test_db.unlink()
        
    shutil.copy2(src_db, test_db)
    print(f"Copied {src_db} to {test_db}")
    
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{test_db.as_posix()}")
    
    print("Testing Alembic upgrade to head...")
    command.upgrade(alembic_cfg, "head")
    
    # Check tables in test_db
    conn = sqlite3.connect(test_db)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in c.fetchall()]
    print("Tables after upgrade:", tables)
    assert "fx_rate_observations" in tables
    assert "fx_fetch_runs" in tables
    
    print("Testing Alembic downgrade to 003...")
    command.downgrade(alembic_cfg, "003_create_cashflow_forecasting_tables")
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables_after = [r[0] for r in c.fetchall()]
    assert "fx_rate_observations" not in tables_after
    assert "fx_fetch_runs" not in tables_after
    print("Downgrade verified successfully!")
    
    conn.close()
    test_db.unlink()
    print("Scratch test database cleaned up.")

if __name__ == "__main__":
    test_migration_on_copy()

