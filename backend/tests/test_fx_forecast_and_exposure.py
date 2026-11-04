import datetime
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal, get_db
from app.main import app
from app.models.fx_forecast import FxForecast
from app.models.fx_rate_observation import FxRateObservation


@pytest.fixture(scope="module")
def fx_client():
    """Test client using operational database SessionLocal for FX tests."""
    with TestClient(app) as client:
        yield client


def test_list_supported_pairs(fx_client: TestClient):
    response = fx_client.get("/api/v1/fx/pairs")
    assert response.status_code == 200
    data = response.json()
    assert data["base_currency"] == "INR"
    pairs = [p["pair"] for p in data["supported_pairs"]]
    assert "USD/INR" in pairs
    assert "EUR/INR" in pairs
    assert "GBP/INR" in pairs
    assert "attribution_notice" in data
    assert "Reserve Bank of India" in data["attribution_notice"]


def test_get_current_rates(fx_client: TestClient):
    response = fx_client.get("/api/v1/fx/rates/current")
    assert response.status_code == 200
    rates = response.json()
    assert isinstance(rates, list)
    if rates:
        first = rates[0]
        assert "currency_pair" in first
        assert "rate_value" in first
        assert "freshness_status" in first
        assert "is_derived" in first

    # Filtered test
    filtered_res = fx_client.get("/api/v1/fx/rates/current?pairs=USD/INR")
    assert filtered_res.status_code == 200
    filtered_rates = filtered_res.json()
    for r in filtered_rates:
        assert r["currency_pair"] == "USD/INR"


def test_get_rate_history(fx_client: TestClient):
    response = fx_client.get("/api/v1/fx/rates/history?pair=USD/INR&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["currency_pair"] == "USD/INR"
    assert data["total"] > 6000
    assert len(data["items"]) == 10

    # Test date range
    range_res = fx_client.get(
        "/api/v1/fx/rates/history?pair=USD/INR&start_date=2024-01-01&end_date=2024-01-31"
    )
    assert range_res.status_code == 200
    range_data = range_res.json()
    assert range_data["total"] > 0
    for item in range_data["items"]:
        assert "2024-01-01" <= item["observation_date"] <= "2024-01-31"


def test_models_status_and_metrics(fx_client: TestClient):
    # Models status
    status_res = fx_client.get("/api/v1/fx/models/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["model_version"] == "1.0.0"
    for pair in ["USD/INR", "EUR/INR", "GBP/INR"]:
        assert pair in status_data["currencies"]
        pair_info = status_data["currencies"][pair]
        assert pair_info["model_ready"] is True
        assert pair_info["skill_status"] in ["TRAINED_AND_VALIDATED", "NO_SKILL_VS_BASELINE"]
        assert pair_info["test_sample_count"] > 900

    # Models metrics
    metrics_res = fx_client.get("/api/v1/fx/models/metrics?pair=USD/INR")
    assert metrics_res.status_code == 200
    metrics_data = metrics_res.json()
    assert metrics_data["currency_pair"] == "USD/INR"
    assert "horizon_breakdown" in metrics_data

    # Invalid pair metrics
    inv_res = fx_client.get("/api/v1/fx/models/metrics?pair=XYZ/INR")
    assert inv_res.status_code == 404


def test_generate_fx_forecast_sessions(fx_client: TestClient):
    payload = {
        "company_id": "FINORA_DEMO",
        "currency_pair": "USD/INR",
        "horizon_sessions": 10
    }
    response = fx_client.post("/api/v1/fx/forecast", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["company_id"] == "FINORA_DEMO"
    assert data["currency_pair"] == "USD/INR"
    assert data["horizon_sessions"] == 10
    assert float(data["anchor_rate"]) > 0
    assert float(data["predicted_rate"]) > 0
    assert data["predicted_direction"] in ["UP", "DOWN", "NEUTRAL"]
    assert "UP" in data["direction_probabilities"]
    assert "DOWN" in data["direction_probabilities"]
    assert "NEUTRAL" in data["direction_probabilities"]
    assert len(data["prediction_range_80"]) == 2
    assert len(data["prediction_range_95"]) == 2

    # Confidence interval nesting
    r80 = [float(x) for x in data["prediction_range_80"]]
    r95 = [float(x) for x in data["prediction_range_95"]]
    pred_rate = float(data["predicted_rate"])
    assert r95[0] <= r80[0]
    assert r80[1] <= r95[1]
    assert r80[0] <= pred_rate <= r80[1]

    # Verify persistence
    forecast_id = data["forecast_id"]
    get_res = fx_client.get(f"/api/v1/fx/forecasts/{forecast_id}")
    assert get_res.status_code == 200
    saved = get_res.json()
    assert saved["forecast_id"] == forecast_id
    assert saved["currency_pair"] == "USD/INR"
    assert float(saved["predicted_rate"]) == float(data["predicted_rate"])


def test_generate_fx_forecast_target_date(fx_client: TestClient):
    # Retrieve anchor date from history to compute a valid forward date
    db = SessionLocal()
    try:
        latest = db.scalars(
            select(FxRateObservation).where(
                FxRateObservation.base_currency == "EUR",
                FxRateObservation.rate_type == "REFERENCE_DAILY"
            ).order_by(FxRateObservation.observation_date.desc()).limit(1)
        ).first()
        anchor_date = latest.observation_date
    finally:
        db.close()

    target_date = anchor_date + datetime.timedelta(days=14)
    payload = {
        "company_id": "FINORA_DEMO",
        "currency_pair": "EUR/INR",
        "target_date": target_date.isoformat()
    }
    response = fx_client.post("/api/v1/fx/forecast", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["currency_pair"] == "EUR/INR"
    assert data["target_date"] == target_date.isoformat()
    assert 1 <= data["horizon_sessions"] <= 30


def test_forecast_validation_errors(fx_client: TestClient):
    # Horizon exceeds max 30
    res_horizon = fx_client.post("/api/v1/fx/forecast", json={
        "company_id": "FINORA_DEMO",
        "currency_pair": "USD/INR",
        "horizon_sessions": 35
    })
    assert res_horizon.status_code == 422

    # Unsupported currency pair
    res_pair = fx_client.post("/api/v1/fx/forecast", json={
        "company_id": "FINORA_DEMO",
        "currency_pair": "JPY/INR",
        "horizon_sessions": 5
    })
    assert res_pair.status_code == 422

    # Target date before anchor date
    res_past = fx_client.post("/api/v1/fx/forecast", json={
        "company_id": "FINORA_DEMO",
        "currency_pair": "USD/INR",
        "target_date": "2020-01-01"
    })
    assert res_past.status_code == 422


def test_forecast_history_endpoint(fx_client: TestClient):
    response = fx_client.get("/api/v1/fx/forecasts/history?company_id=FINORA_DEMO&limit=10")
    assert response.status_code == 200
    history = response.json()
    assert isinstance(history, list)
    assert len(history) >= 1
    assert history[0]["company_id"] == "FINORA_DEMO"


def test_fx_exposure_calculation(fx_client: TestClient):
    response = fx_client.get("/api/v1/fx/exposure?company_id=FINORA_DEMO")
    assert response.status_code == 200
    data = response.json()

    assert data["company_id"] == "FINORA_DEMO"
    assert data["base_currency"] == "INR"
    assert "supported_exposures" in data
    assert "unsupported_exposures" in data
    assert "total_net_estimated_impact" in data

    # Check supported exposures structure
    for exp in data["supported_exposures"]:
        assert exp["currency"] in ["USD", "EUR", "GBP"]
        assert exp["receivable_amount"] >= 0
        assert exp["payable_amount"] >= 0
        assert exp["benchmark_rate"] > 0
        assert exp["predicted_rate"] > 0
        # Check impact signs:
        delta = exp["predicted_rate"] - exp["benchmark_rate"]
        expected_rec = round(exp["receivable_amount"] * delta, 2)
        expected_pay = round(-exp["payable_amount"] * delta, 2)
        assert abs(exp["estimated_receivable_impact"] - expected_rec) < 0.1
        assert abs(exp["estimated_payable_impact"] - expected_pay) < 0.1
        assert abs(exp["net_estimated_impact"] - (expected_rec + expected_pay)) < 0.1
