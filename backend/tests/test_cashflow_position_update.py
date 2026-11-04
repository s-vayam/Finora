"""
Unit and Integration Tests for Cash Balance Position Update & Forecast Reliability.
"""

from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.cash_balance_snapshot import CashBalanceSnapshot


def _setup_demo_company(db: Session):
    co = db.query(Company).filter(Company.company_id == "FINORA_DEMO").first()
    if not co:
        co = Company(
            company_id="FINORA_DEMO",
            company_name="Finora Demo Exports Pvt Ltd",
            base_currency="INR",
        )
        db.add(co)
        db.commit()


def test_update_cash_position_balance_and_threshold(client: TestClient, test_db_session: Session):
    """Test updating opening balance and minimum threshold via PATCH."""
    _setup_demo_company(test_db_session)

    # 1. Establish initial position
    create_res = client.post(
        "/api/v1/cashflow/position",
        json={
            "company_id": "FINORA_DEMO",
            "as_of_date": "2026-11-05",
            "balance_amount": 2500000.0,
            "currency": "INR",
            "minimum_cash_threshold": 500000.0,
            "source": "MANUAL",
            "notes": "Initial opening position",
        },
    )
    assert create_res.status_code == 201
    created = create_res.json()
    snapshot_id = created["snapshot_id"]
    assert float(created["balance_amount"]) == 2500000.0
    assert float(created["minimum_cash_threshold"]) == 500000.0

    # 2. Update balance and threshold
    patch_res = client.patch(
        f"/api/v1/cashflow/position/{snapshot_id}",
        json={
            "balance_amount": 2800000.0,
            "minimum_cash_threshold": 600000.0,
            "notes": "Bank reconciliation adjustment",
        },
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["snapshot_id"] == snapshot_id
    assert float(updated["balance_amount"]) == 2800000.0
    assert float(updated["minimum_cash_threshold"]) == 600000.0
    assert "Updated" in updated["notes"]
    assert "balance: 2500000" in updated["notes"]
    assert "2800000" in updated["notes"]
    assert "Bank reconciliation adjustment" in updated["notes"]

    # 3. Verify latest position reflects update
    latest_res = client.get("/api/v1/cashflow/position/latest?company_id=FINORA_DEMO")
    assert latest_res.status_code == 200
    assert float(latest_res.json()["balance_amount"]) == 2800000.0


def test_update_cash_position_date_conflict(client: TestClient, test_db_session: Session):
    """Test that updating as_of_date to a date that already has a snapshot returns 409 Conflict."""
    _setup_demo_company(test_db_session)

    # Snapshot 1 on Nov 5
    res1 = client.post(
        "/api/v1/cashflow/position",
        json={
            "company_id": "FINORA_DEMO",
            "as_of_date": "2026-11-05",
            "balance_amount": 2500000.0,
            "currency": "INR",
        },
    )
    assert res1.status_code == 201
    snp1_id = res1.json()["snapshot_id"]

    # Snapshot 2 on Nov 6
    res2 = client.post(
        "/api/v1/cashflow/position",
        json={
            "company_id": "FINORA_DEMO",
            "as_of_date": "2026-11-06",
            "balance_amount": 2600000.0,
            "currency": "INR",
        },
    )
    assert res2.status_code == 201

    # Attempt to change snapshot 1 date to Nov 6 (collision)
    conflict_res = client.patch(
        f"/api/v1/cashflow/position/{snp1_id}",
        json={"as_of_date": "2026-11-06"},
    )
    assert conflict_res.status_code == 409
    assert "already exists" in conflict_res.json()["detail"]


def test_update_cash_position_not_found_and_validation(client: TestClient, test_db_session: Session):
    """Test 404 for unknown snapshot and 422 for invalid balance amount."""
    _setup_demo_company(test_db_session)

    # 404
    not_found = client.patch(
        "/api/v1/cashflow/position/SNP-NONEXISTENT",
        json={"balance_amount": 100000.0},
    )
    assert not_found.status_code == 404

    # 422 for non-positive balance
    inv_res = client.patch(
        "/api/v1/cashflow/position/SNP-NONEXISTENT",
        json={"balance_amount": -500.0},
    )
    assert inv_res.status_code == 422


def test_forecast_serialization_and_aliases(client: TestClient, test_db_session: Session):
    """Verify forecast returns both nested summary and top-level convenience fields."""
    _setup_demo_company(test_db_session)

    # Establish position
    client.post(
        "/api/v1/cashflow/position",
        json={
            "company_id": "FINORA_DEMO",
            "as_of_date": "2026-11-05",
            "balance_amount": 2500000.0,
            "currency": "INR",
            "minimum_cash_threshold": 500000.0,
        },
    )

    fc_res = client.get("/api/v1/cashflow/forecast?company_id=FINORA_DEMO&horizon_days=30")
    assert fc_res.status_code == 200
    fc = fc_res.json()

    # Nested summary
    assert "summary" in fc
    assert "expected_inflows" in fc["summary"]
    assert "expected_outflows" in fc["summary"]
    assert "closing_balance" in fc["summary"]

    # Top level aliases
    assert fc["total_inflow"] is not None
    assert fc["total_outflow"] is not None
    assert fc["net_cash_flow"] is not None
    assert fc["closing_balance"] is not None
    assert fc["daily_projections"] is not None
    assert len(fc["daily_projections"]) in (30, 31)

    # Daily item aliases
    d0 = fc["daily_projections"][0]
    assert "expected_inflows" in d0
    assert "inflow" in d0
    assert "expected_outflows" in d0
    assert "outflow" in d0


def test_what_if_scenario_execution(client: TestClient, test_db_session: Session):
    """Verify scenario simulator accepts requests with omitted as_of_date and returns valid numbers."""
    _setup_demo_company(test_db_session)

    client.post(
        "/api/v1/cashflow/position",
        json={
            "company_id": "FINORA_DEMO",
            "as_of_date": "2026-11-05",
            "balance_amount": 2500000.0,
            "currency": "INR",
            "minimum_cash_threshold": 500000.0,
        },
    )

    scen_res = client.post(
        "/api/v1/cashflow/scenario",
        json={
            "company_id": "FINORA_DEMO",
            "horizon_days": 30,
            "payment_delay_days": 15,
            "expense_increase_percentage": 10.0,
        },
    )
    assert scen_res.status_code == 200
    res = scen_res.json()

    assert float(res["baseline_ending_cash"]) is not None
    assert float(res["scenario_ending_cash"]) is not None
    assert float(res["net_cash_difference"]) is not None
    # Nested backward compatibility
    assert res["baseline"]["closing_balance"] is not None
    assert res["scenario"]["closing_balance"] is not None
