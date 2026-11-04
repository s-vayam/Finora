"""
Tests for ML Serialized Artifacts and Metadata (Stage 3D).
"""

import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

from backend.ml.training.training_config import CONFIG
from backend.ml.feature_schema import ALL_FEATURE_COLUMNS


def test_artifacts_exist():
    assert CONFIG.classifier_artifact.exists(), "Classifier artifact missing"
    assert CONFIG.regressor_artifact.exists(), "Regressor artifact missing"
    assert CONFIG.feature_pipeline_artifact.exists(), "Feature pipeline artifact missing"
    assert CONFIG.model_metadata_file.exists(), "Model metadata file missing"
    assert CONFIG.evaluation_metrics_file.exists(), "Evaluation metrics file missing"
    assert CONFIG.feature_importance_file.exists(), "Feature importance file missing"


def test_artifacts_load_and_predict():
    pipeline = joblib.load(CONFIG.feature_pipeline_artifact)
    classifier = joblib.load(CONFIG.classifier_artifact)
    regressor = joblib.load(CONFIG.regressor_artifact)

    # Sample input DataFrame conforming to feature schema
    sample_df = pd.DataFrame([{
        "invoice_amount": 15000.0,
        "log_invoice_amount": np.log1p(15000.0),
        "terms_days": 30,
        "baseline_to_due_days": 30,
        "invoice_month": 3,
        "invoice_quarter": 1,
        "invoice_dayofweek": 1,
        "due_month": 4,
        "due_dayofweek": 3,
        "cust_prev_invoice_count": 5,
        "cust_prev_late_rate": 0.2,
        "cust_prev_ontime_rate": 0.8,
        "cust_prev_avg_delay": 1.2,
        "cust_prev_max_delay": 4.0,
        "is_cold_start": 0,
        "currency": "USD",
        "business_code": "U001",
        "cust_payment_terms": "NAA8",
    }])

    X_trans = pipeline.transform(sample_df[ALL_FEATURE_COLUMNS])
    assert X_trans.shape[0] == 1

    # Probability prediction
    probs = classifier.predict_proba(X_trans)
    assert probs.shape == (1, 2)
    late_prob = probs[0, 1]
    assert 0.0 <= late_prob <= 1.0

    # Delay prediction
    delay_pred = regressor.predict(X_trans)
    assert len(delay_pred) == 1
    clipped_delay = max(0.0, float(delay_pred[0]))
    assert clipped_delay >= 0.0


def test_metadata_and_metrics_integrity():
    with open(CONFIG.model_metadata_file, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["model_version"] == "v1.0.0"
    assert "classifier" in meta
    assert "regressor" in meta
    assert meta["classifier"]["optimal_threshold"] > 0

    with open(CONFIG.evaluation_metrics_file, "r", encoding="utf-8") as f:
        metrics = json.load(f)
    test_roc = metrics["classification"]["champion_test_at_default_threshold"]["roc_auc"]
    assert test_roc >= 0.70, f"Expected test ROC-AUC >= 0.70, got {test_roc}"

    test_mae = metrics["regression"]["champion_test_metrics"]["mae"]
    assert test_mae < 10.0, f"Expected test MAE < 10 days, got {test_mae}"
