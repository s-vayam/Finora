"""
Tests for Cash Flow Data Foundation (Phase 4 Stage 4A).

Verifies cash balance snapshots, collection forecast overrides,
expense forecast assumptions, uniqueness constraints, and migration schemas.
"""

from datetime import date, timedelta
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from app.database import engine


def test_migration_003_tables_and_columns():
    """Verify that migration 003 created all 4 tables with correct columns."""
    insp = inspect(engine)
    table_names = insp.get_table_names()

    assert "cash_balance_snapshots" in table_names
    assert "collection_forecast_overrides" in table_names
    assert "expense_forecast_assumptions" in table_names
    assert "cashflow_forecast_runs" in table_names

    snap_cols = {c["name"] for c in insp.get_columns("cash_balance_snapshots")}
    assert {"snapshot_id", "company_id", "as_of_date", "balance_amount", "currency", "minimum_cash_threshold", "source"}.issubset(snap_cols)

    ovr_cols = {c["name"] for c in insp.get_columns("collection_forecast_overrides")}
    assert {"override_id", "company_id", "invoice_id", "expected_collection_date", "is_active"}.issubset(ovr_cols)

    asm_cols = {c["name"] for c in insp.get_columns("expense_forecast_assumptions")}
    assert {"assumption_id", "company_id", "category", "monthly_amount", "currency", "effective_start_date", "is_active"}.issubset(asm_cols)

    run_cols = {c["name"] for c in insp.get_columns("cashflow_forecast_runs")}
    assert {"forecast_id", "company_id", "as_of_date", "horizon_days", "base_currency", "opening_balance", "forecast_payload"}.issubset(run_cols)


def test_cash_balance_snapshot_lifecycle(seeded_client: TestClient):
    """Test creating, duplicate rejection, and retrieving cash balance snapshots."""
    today = date(2026, 11, 4)

    # 1. Create opening cash snapshot
    res = seeded_client.post("/api/v1/cashflow/position", json={
        "company_id": "FINORA_DEMO",
        "as_of_date": today.isoformat(),
        "balance_amount": "2500000.00",
        "currency": "INR",
        "minimum_cash_threshold": "500000.00",
        "source": "MANUAL",
        "notes": "Q4 opening position",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["company_id"] == "FINORA_DEMO"
    assert data["as_of_date"] == today.isoformat()
    assert float(data["balance_amount"]) == 2500000.0
    assert float(data["minimum_cash_threshold"]) == 500000.0
    assert data["source"] == "MANUAL"

    # 2. Duplicate snapshot for same company, date, and currency -> 409 Conflict
    dup_res = seeded_client.post("/api/v1/cashflow/position", json={
        "company_id": "FINORA_DEMO",
        "as_of_date": today.isoformat(),
        "balance_amount": "3000000.00",
        "currency": "INR",
    })
    assert dup_res.status_code == 409
    assert "already exists" in dup_res.json()["detail"]

    # 3. Retrieve latest position
    latest_res = seeded_client.get("/api/v1/cashflow/position/latest?company_id=FINORA_DEMO&currency=INR")
    assert latest_res.status_code == 200
    assert latest_res.json()["snapshot_id"] == data["snapshot_id"]

    # 4. Unknown company -> 404
    unk_res = seeded_client.post("/api/v1/cashflow/position", json={
        "company_id": "NON_EXISTENT_CO",
        "as_of_date": today.isoformat(),
        "balance_amount": "100000.00",
        "currency": "INR",
    })
    assert unk_res.status_code == 404


def test_collection_overrides_crud(seeded_client: TestClient):
    """Test creating, listing, and deactivating manual collection overrides."""
    # Find an open invoice
    inv_res = seeded_client.get("/api/v1/invoices?status=OPEN&page_size=1")
    inv_id = inv_res.json()["items"][0]["invoice_id"]

    override_date = date(2026, 11, 25)

    # 1. Create override
    create_res = seeded_client.post("/api/v1/cashflow/collection-overrides", json={
        "company_id": "FINORA_DEMO",
        "invoice_id": inv_id,
        "expected_collection_date": override_date.isoformat(),
        "notes": "Confirmed with client finance VP",
    })
    assert create_res.status_code == 201
    ovr_data = create_res.json()
    ovr_id = ovr_data["override_id"]
    assert ovr_data["invoice_id"] == inv_id
    assert ovr_data["expected_collection_date"] == override_date.isoformat()
    assert ovr_data["is_active"] is True

    # 2. List overrides
    list_res = seeded_client.get(f"/api/v1/cashflow/collection-overrides?company_id=FINORA_DEMO&invoice_id={inv_id}")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 3. Deactivate override
    del_res = seeded_client.delete(f"/api/v1/cashflow/collection-overrides/{ovr_id}")
    assert del_res.status_code == 200
    assert del_res.json()["is_active"] is False

    # Check active filter returns 0 active
    active_res = seeded_client.get(f"/api/v1/cashflow/collection-overrides?company_id=FINORA_DEMO&invoice_id={inv_id}&is_active=true")
    assert len(active_res.json()) == 0


def test_expense_assumptions_crud(seeded_client: TestClient):
    """Test creating, overlap validation, patching, and deactivating expense assumptions."""
    start_date = date(2026, 11, 1)
    end_date = date(2026, 12, 31)

    # 1. Create assumption for SALARIES
    create_res = seeded_client.post("/api/v1/cashflow/expense-assumptions", json={
        "company_id": "FINORA_DEMO",
        "category": "SALARIES",
        "monthly_amount": "450000.00",
        "currency": "INR",
        "effective_start_date": start_date.isoformat(),
        "effective_end_date": end_date.isoformat(),
        "description": "Adjusted Q4 payroll budget",
    })
    assert create_res.status_code == 201
    asm_data = create_res.json()
    asm_id = asm_data["assumption_id"]
    assert asm_data["category"] == "SALARIES"
    assert float(asm_data["monthly_amount"]) == 450000.0

    # 2. Overlapping active assumption for same company, category, and currency -> 409 Conflict
    overlap_res = seeded_client.post("/api/v1/cashflow/expense-assumptions", json={
        "company_id": "FINORA_DEMO",
        "category": "SALARIES",
        "monthly_amount": "500000.00",
        "currency": "INR",
        "effective_start_date": date(2026, 11, 15).isoformat(),
        "effective_end_date": date(2027, 1, 15).isoformat(),
    })
    assert overlap_res.status_code == 409
    assert "Overlapping active expense assumption" in overlap_res.json()["detail"]

    # 3. Patch amount
    patch_res = seeded_client.patch(f"/api/v1/cashflow/expense-assumptions/{asm_id}", json={
        "monthly_amount": "480000.00",
    })
    assert patch_res.status_code == 200
    assert float(patch_res.json()["monthly_amount"]) == 480000.0

    # 4. Deactivate assumption
    del_res = seeded_client.delete(f"/api/v1/cashflow/expense-assumptions/{asm_id}")
    assert del_res.status_code == 200
    assert del_res.json()["is_active"] is False

