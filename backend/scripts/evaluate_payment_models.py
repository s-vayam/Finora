"""
Model Evaluation Script for Finora ML Payment Risk Engine.

Loads trained artifacts, evaluates performance on test split and open invoices,
and outputs a comprehensive evaluation report.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import joblib
import numpy as np
import pandas as pd

from backend.ml.training.training_config import CONFIG
from backend.ml.features import (
    extract_raw_features,
    split_dataset_chronologically,
)
from backend.ml.training.train_classifier import evaluate_classifier_predictions
from backend.ml.training.train_regressor import evaluate_regressor_predictions


def run_evaluation() -> dict:
    """Evaluate serialized models on test split and open invoices."""
    print("Loading serialized artifacts...")
    pipeline = joblib.load(CONFIG.feature_pipeline_artifact)
    classifier = joblib.load(CONFIG.classifier_artifact)
    regressor = joblib.load(CONFIG.regressor_artifact)

    with open(CONFIG.model_metadata_file, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    optimal_threshold = metadata["classifier"]["optimal_threshold"]

    # 1. Evaluate on test split of cleared invoices
    cleared_file = CONFIG.processed_dir / "cleared_invoices.csv"
    df_cleared = pd.read_csv(cleared_file)
    _, _, test_df = split_dataset_chronologically(
        df_cleared,
        train_ratio=CONFIG.train_ratio,
        val_ratio=CONFIG.val_ratio,
    )

    X_test_raw = extract_raw_features(test_df, include_customer_history=True)
    X_test = pipeline.transform(X_test_raw)
    y_test_cls = test_df["is_late"].astype(int).values

    test_prob = classifier.predict_proba(X_test)[:, 1]
    cls_eval_default = evaluate_classifier_predictions(y_test_cls, test_prob, threshold=0.50)
    cls_eval_optimal = evaluate_classifier_predictions(y_test_cls, test_prob, threshold=optimal_threshold)

    # Regressor evaluation on late subset
    test_late_mask = y_test_cls == 1
    X_test_late = X_test[test_late_mask]
    y_test_late = test_df.loc[test_late_mask, "late_delay_days"].astype(float).values

    test_delay_preds = np.maximum(regressor.predict(X_test_late), 0.0)
    reg_eval = evaluate_regressor_predictions(y_test_late, test_delay_preds)

    # 2. Evaluate inference on open invoices
    open_file = CONFIG.processed_dir / "open_invoices.csv"
    open_summary = {}
    if open_file.exists():
        df_open = pd.read_csv(open_file)
        X_open_raw = extract_raw_features(df_open, include_customer_history=False)
        X_open = pipeline.transform(X_open_raw)

        open_probs = classifier.predict_proba(X_open)[:, 1]
        open_delays = np.maximum(regressor.predict(X_open), 0.0)

        # Risk categories: LOW (< 0.35), MEDIUM (0.35 - 0.65), HIGH (> 0.65)
        low_count = int(np.sum(open_probs < 0.35))
        med_count = int(np.sum((open_probs >= 0.35) & (open_probs <= 0.65)))
        high_count = int(np.sum(open_probs > 0.65))

        open_summary = {
            "total_open_evaluated": len(df_open),
            "predicted_late_count_default": int(np.sum(open_probs >= 0.50)),
            "predicted_late_count_optimal": int(np.sum(open_probs >= optimal_threshold)),
            "risk_categories": {
                "low": low_count,
                "medium": med_count,
                "high": high_count,
            },
            "mean_predicted_probability": float(np.mean(open_probs)),
            "mean_predicted_delay_days": float(np.mean(open_delays)),
            "median_predicted_delay_days": float(np.median(open_delays)),
        }

    report = {
        "evaluation_timestamp": pd.Timestamp.now(tz="UTC").isoformat(),
        "test_split_evaluation": {
            "total_test_samples": len(test_df),
            "late_test_samples": int(np.sum(test_late_mask)),
            "classification_metrics_default_threshold": cls_eval_default,
            "classification_metrics_optimal_threshold": cls_eval_optimal,
            "regression_metrics": reg_eval,
        },
        "open_invoices_inference": open_summary,
    }

    report_path = CONFIG.artifacts_dir / "test_evaluation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("Evaluation completed successfully:")
    print(f"Test ROC-AUC: {cls_eval_default['roc_auc']:.4f}")
    print(f"Test PR-AUC: {cls_eval_default['pr_auc']:.4f}")
    print(f"Test Regressor MAE: {reg_eval['mae']:.2f} days")
    print(f"Open Invoices Evaluated: {open_summary.get('total_open_evaluated', 0)}")
    return report


if __name__ == "__main__":
    run_evaluation()
