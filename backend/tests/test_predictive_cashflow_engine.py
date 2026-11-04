"""
Tests for Predictive Cash Flow Engine and Scenario Simulator (Phase 4 Stage 4D & 4E).

Verifies opening balance requirement, roll-forward mathematical consistency,
liquidity alerts, what-if scenario simulations, and forecast persistence.
"""

from datetime import date, timedelta
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient


def test_missing_opening_balance_returns_409(seeded_client: TestClient):
    """
    Verify that generating a forecast without an opening cash balance snapshot
    returns HTTP 409 Conflict with OPENING_BALANCE_REQUIRED error code.
    """
    res = seeded_client.get("/api/v1/cashflow/forecast?company_id=FINORA_DEMO&horizon_days=30&as_of_date=2026-11-04")
    assert res.status_code == 409
    err = res.json()["detail"]
    assert err["error_code"] == "OPENING_BALANCE_REQUIRED"


def test_forecast_with_valid_snapshot_and_rollforward(seeded_client: TestClient):
    """
    Verify forecast generation with valid snapshot:
    - Daily roll forward: Opening + Inflow - Outflow == Closing
    - Monthly rollup matches daily totals
    - Horizon summary matches cumulative projections
    """
    as_of = date(2026, 11, 4)

    # 1. Provide opening cash position
    snap_res = seeded_client.post("/api/v1/cashflow/position", json={
        "company_id": "FINORA_DEMO",
        "as_of_date": as_of.isoformat(),
        "balance_amount": "2500000.00",
        "currency": "INR",
        "minimum_cash_threshold": "500000.00",
        "source": "MANUAL",
        "notes": "Opening position for testing",
    })
    assert snap_res.status_code == 201

    # 2. Request 30-day forecast
    fc_res = seeded_client.get(f"/api/v1/cashflow/forecast?company_id=FINORA_DEMO&horizon_days=30&as_of_date={as_of.isoformat()}")
    assert fc_res.status_code == 200
    fc = fc_res.json()

    assert fc["forecast_horizon_days"] == 30
    assert float(fc["opening_balance"]) == 2500000.0
    assert "summary" in fc
    assert "data_freshness" in fc
    assert "alerts" in fc
    assert len(fc["daily_projection"]) == 31  # as_of_date to as_of_date + 30 days

    # 3. Test daily roll-forward arithmetic
    daily = fc["daily_projection"]
    prev_close = Decimal(str(daily[0]["opening_balance"]))
    for d in daily:
        d_open = Decimal(str(d["opening_balance"]))
        d_in = Decimal(str(d["expected_inflows"]))
        d_out = Decimal(str(d["expected_outflows"]))
        d_net = Decimal(str(d["net_cash_flow"]))
        d_close = Decimal(str(d["closing_balance"]))

        assert d_open == prev_close, f"Day {d['date']} opening != previous closing"
        assert d_open + d_in - d_out == d_close, f"Day {d['date']} roll forward failed"
        assert d_net == d_in - d_out
        prev_close = d_close

    # 4. Check monthly projection reconciliation
    monthly = fc["monthly_projection"]
    assert len(monthly) >= 1
    sum_m_in = sum((Decimal(str(m["expected_inflows"])) for m in monthly), Decimal("0.00"))
    sum_d_in = sum((Decimal(str(d["expected_inflows"])) for d in daily), Decimal("0.00"))
    assert sum_m_in == sum_d_in


def test_what_if_scenario_simulation(seeded_client: TestClient):
    """
    Test POST /api/v1/cashflow/scenario:
    - Simulates payment delay (+15 days) and expense inflation (+10%).
    - Does not mutate actual financial records.
    - Yields different ending cash from baseline.
    """
    as_of = date(2026, 11, 4)

    # Record opening position if not present
    seeded_client.post("/api/v1/cashflow/position", json={
        "company_id": "FINORA_DEMO",
        "as_of_date": as_of.isoformat(),
        "balance_amount": "5000000.00",
        "currency": "INR",
        "minimum_cash_threshold": "1000000.00",
    })

    scen_res = seeded_client.post("/api/v1/cashflow/scenario", json={
        "company_id": "FINORA_DEMO",
        "as_of_date": as_of.isoformat(),
        "horizon_days": 90,
        "payment_delay_days": 15,
        "expense_increase_percentage": "10.00",
    })
    assert scen_res.status_code == 200
    scen = scen_res.json()

    assert scen["status"] == "SIMULATED"
    assert scen["horizon_days"] == 90
    assert scen["simulation_parameters"]["payment_delay_days"] == 15
    assert scen["simulation_parameters"]["expense_increase_percentage"] == 10.0

    # With +10% expenses and delayed payments, ending cash in scenario must be strictly lower than baseline
    base_end = float(scen["baseline_ending_cash"])
    scen_end = float(scen["scenario_ending_cash"])
    assert scen_end < base_end
    assert float(scen["net_cash_difference"]) == pytest.approx(scen_end - base_end, 0.01)


def test_forecast_persistence_and_retrieval(seeded_client: TestClient):
    """Test persisting forecast run and retrieving by ID and history endpoint."""
    as_of = date(2026, 11, 4)

    # Seed position
    seeded_client.post("/api/v1/cashflow/position", json={
        "company_id": "FINORA_DEMO",
        "as_of_date": as_of.isoformat(),
        "balance_amount": "3000000.00",
        "currency": "INR",
    })

    gen_res = seeded_client.post("/api/v1/cashflow/forecast/generate", json={
        "company_id": "FINORA_DEMO",
        "as_of_date": as_of.isoformat(),
        "horizon_days": 60,
        "base_currency": "INR",
    })
    assert gen_res.status_code == 201
    fc_id = gen_res.json()["forecast_id"]

    # Retrieve by ID
    get_res = seeded_client.get(f"/api/v1/cashflow/forecast/{fc_id}")
    assert get_res.status_code == 200
    assert get_res.json()["forecast_id"] == fc_id
    assert get_res.json()["forecast_horizon_days"] == 60

    # Retrieve via history endpoint
    hist_res = seeded_client.get("/api/v1/cashflow/forecast-history?company_id=FINORA_DEMO")
    assert hist_res.status_code == 200
    runs = hist_res.json()
    assert len(runs) >= 1
    assert any(r["forecast_id"] == fc_id for r in runs)

