import os
import shutil
import tempfile
import sqlite3
from pathlib import Path
from alembic.config import Config
from alembic import command

BACKEND_DIR = Path(__file__).resolve().parent.parent

def test_migration_on_phase1_database():
    """Verify that Alembic migration upgrades a Phase 1 database without altering existing data."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        tmp_db_path = tmp_file.name

    try:
        # Use development database as base
        shutil.copyfile(BACKEND_DIR / "data" / "database" / "finora.db", tmp_db_path)

        conn = sqlite3.connect(tmp_db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM invoices")
        original_invoices = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM cash_transactions")
        original_txns = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM customers")
        original_customers = cur.fetchone()[0]
        conn.close()

        # Run Alembic upgrade head
        cfg = Config(str(BACKEND_DIR / "alembic.ini"))
        cfg.set_main_option("sqlalchemy.url", f"sqlite:///{tmp_db_path}")
        cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))

        command.upgrade(cfg, "head")

        # Verify payments table exists and data is untouched
        conn = sqlite3.connect(tmp_db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        assert "payments" in tables
        assert "alembic_version" in tables

        cur.execute("SELECT COUNT(*) FROM invoices")
        assert cur.fetchone()[0] == original_invoices
        cur.execute("SELECT COUNT(*) FROM cash_transactions")
        assert cur.fetchone()[0] == original_txns
        cur.execute("SELECT COUNT(*) FROM customers")
        assert cur.fetchone()[0] == original_customers
        conn.close()

    finally:
        if os.path.exists(tmp_db_path):
            try:
                os.remove(tmp_db_path)
            except PermissionError:
                pass
