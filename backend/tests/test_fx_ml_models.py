from decimal import Decimal
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from ml.fx.features import FEATURE_NAMES, compute_historical_features, extract_features_at_origin
from ml.fx.preprocessing import load_pair_series, build_multi_horizon_dataset, create_purged_chronological_splits
from ml.fx.model_registry import FxModelRegistry, ARTIFACTS_DIR, METADATA_DIR


def test_fx_ml_artifacts_exist():
    for curr in ["usd", "eur", "gbp"]:
        reg_file = ARTIFACTS_DIR / f"fx_regressor_{curr}.joblib"
        cls_file = ARTIFACTS_DIR / f"fx_classifier_{curr}.joblib"
        meta_file = METADATA_DIR / f"fx_evaluation_report_{curr}.json"

        assert reg_file.exists(), f"Missing regressor artifact: {reg_file}"
        assert cls_file.exists(), f"Missing classifier artifact: {cls_file}"
        assert meta_file.exists(), f"Missing evaluation metadata: {meta_file}"


def test_fx_evaluation_metrics_and_skill_status():
    registry = FxModelRegistry.get_instance()
    for curr in ["USD", "EUR", "GBP"]:
        assert registry.is_model_available(curr) is True
        status = registry.get_skill_status(curr)
        assert status in ["TRAINED_AND_VALIDATED", "NO_SKILL_VS_BASELINE"]

        meta = registry.get_metadata(curr)
        assert "overall_regression" in meta
        assert "overall_classification" in meta
        assert "horizon_breakdown" in meta
        assert meta["sample_count_test"] > 1000

        # Check horizon metrics
        for h in [1, 5, 10, 20, 30]:
            h_key = f"{h}_sessions"
            assert h_key in meta["horizon_breakdown"]
            h_metrics = meta["horizon_breakdown"][h_key]
            assert "model_rmse_return" in h_metrics
            assert "random_walk_rmse_return" in h_metrics
            assert "model_mae_inr" in h_metrics
            assert "directional_accuracy" in h_metrics


def test_feature_engineering_leakage_safety():
    # Synthetic time series
    dates = pd.date_range("2025-01-01", periods=50, freq="B")
    rates = np.linspace(80.0, 90.0, 50) + np.random.normal(0, 0.2, 50)
    df = pd.DataFrame({"date": dates, "rate": rates})

    df_feat = compute_historical_features(df)
    assert len(df_feat) == 50

    # Ensure all feature names are in output
    for col in FEATURE_NAMES:
        if col != "horizon_sessions":
            assert col in df_feat.columns, f"Feature {col} missing from output"

    # Verify origin extraction
    feat_origin = extract_features_at_origin(df, horizon_sessions=14)
    assert feat_origin.shape == (1, len(FEATURE_NAMES))
    assert feat_origin["horizon_sessions"].iloc[0] == 14
    assert not feat_origin.isnull().any().any()


def test_fx_model_inference_pipeline():
    registry = FxModelRegistry.get_instance()
    df_raw = load_pair_series("USD")

    # Predict for horizon = 10 trading sessions
    pred = registry.predict("USD", df_raw, horizon_sessions=10)

    assert pred["currency_pair"] == "USD/INR"
    assert pred["horizon_sessions"] == 10
    assert pred["anchor_rate"] > Decimal("30.0")
    assert pred["predicted_rate"] > Decimal("30.0")
    assert pred["predicted_direction"] in ["UP", "DOWN", "NEUTRAL"]
    assert "UP" in pred["direction_probabilities"]
    assert "DOWN" in pred["direction_probabilities"]
    assert "NEUTRAL" in pred["direction_probabilities"]
    assert len(pred["prediction_range_80"]) == 2
    assert len(pred["prediction_range_95"]) == 2
    assert pred["prediction_range_80"][0] <= pred["prediction_range_80"][1]
    assert pred["prediction_range_95"][0] <= pred["prediction_range_95"][1]


def test_fx_model_invalid_inputs():
    registry = FxModelRegistry.get_instance()
    df_raw = load_pair_series("USD")

    # Invalid horizon
    with pytest.raises(ValueError):
        registry.predict("USD", df_raw, horizon_sessions=0)

    with pytest.raises(ValueError):
        registry.predict("USD", df_raw, horizon_sessions=35)

    # Invalid currency
    with pytest.raises(FileNotFoundError):
        registry.predict("XYZ", df_raw, horizon_sessions=10)

