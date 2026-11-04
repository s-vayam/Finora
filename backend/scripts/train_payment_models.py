"""
Training Pipeline Orchestrator for Finora ML Payment Risk Engine.

Loads processed dataset, constructs leakage-safe features, splits data
chronologically, fits feature pipelines, trains and evaluates classifiers
and regressors, and serializes production-grade artifacts and metadata.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
import time

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
    create_feature_pipeline,
    split_dataset_chronologically,
)
from backend.ml.training.train_classifier import train_and_compare_classifiers
from backend.ml.training.train_regressor import train_and_compare_regressors


def run_training() -> dict:
    """Execute complete model training and serialization pipeline."""
    start_time = time.time()
    CONFIG.artifacts_dir.mkdir(parents=True, exist_ok=True)

    cleared_file = CONFIG.processed_dir / "cleared_invoices.csv"
    if not cleared_file.exists():
        raise FileNotFoundError(f"Processed dataset not found at {cleared_file}. Run preprocessing first.")

    print(f"Loading processed cleared invoices from {cleared_file}...")
    df = pd.read_csv(cleared_file)
    print(f"Loaded {len(df)} cleared invoices.")

    # 1. Chronological dataset split FIRST to guarantee pure temporal ordering
    print("Splitting dataset chronologically (70% train, 15% val, 15% test)...")
    train_df, val_df, test_df = split_dataset_chronologically(
        df,
        train_ratio=CONFIG.train_ratio,
        val_ratio=CONFIG.val_ratio,
    )
    print(f"Split sizes: Train={len(train_df)}, Val={len(val_df)}, Test={len(test_df)}")

    # 2. Extract raw features for all splits
    print("Extracting features with leakage-safe customer historical metrics...")
    X_train_raw = extract_raw_features(train_df, include_customer_history=True)
    X_val_raw = extract_raw_features(val_df, include_customer_history=True)
    X_test_raw = extract_raw_features(test_df, include_customer_history=True)

    # 3. Fit feature pipeline on TRAINING split ONLY
    print("Fitting feature pipeline on training split...")
    pipeline = create_feature_pipeline()
    X_train = pipeline.fit_transform(X_train_raw)
    X_val = pipeline.transform(X_val_raw)
    X_test = pipeline.transform(X_test_raw)

    feature_names = []
    if hasattr(pipeline, "get_feature_names_out"):
        try:
            feature_names = list(pipeline.get_feature_names_out())
        except Exception:
            feature_names = [f"f_{i}" for i in range(X_train.shape[1])]
    else:
        feature_names = [f"f_{i}" for i in range(X_train.shape[1])]

    print(f"Total features after encoding: {X_train.shape[1]}")

    # Targets
    y_train_cls = train_df["is_late"].astype(int).values
    y_val_cls = val_df["is_late"].astype(int).values
    y_test_cls = test_df["is_late"].astype(int).values

    # 4. Train and compare classifiers
    print("\n=== Training Classifiers ===")
    champion_cls, cls_summary, optimal_threshold = train_and_compare_classifiers(
        X_train, y_train_cls, X_val, y_val_cls, X_test, y_test_cls
    )
    print(f"Selected Champion Classifier: {cls_summary['champion_model_name']}")
    print(f"Optimal Classification Threshold: {optimal_threshold:.2f}")
    print(f"Test ROC-AUC: {cls_summary['champion_test_at_default_threshold']['roc_auc']:.4f}")
    print(f"Test PR-AUC: {cls_summary['champion_test_at_default_threshold']['pr_auc']:.4f}")
    print(f"Test F1 (optimal thresh): {cls_summary['champion_test_at_optimal_threshold']['f1_score']:.4f}")

    # 5. Late subsets for regression
    train_late_mask = y_train_cls == 1
    val_late_mask = y_val_cls == 1
    test_late_mask = y_test_cls == 1

    X_train_late = X_train[train_late_mask]
    y_train_late = train_df.loc[train_late_mask, "late_delay_days"].astype(float).values

    X_val_late = X_val[val_late_mask]
    y_val_late = val_df.loc[val_late_mask, "late_delay_days"].astype(float).values

    X_test_late = X_test[test_late_mask]
    y_test_late = test_df.loc[test_late_mask, "late_delay_days"].astype(float).values

    print(f"\nLate subsets for regression: Train={len(y_train_late)}, Val={len(y_val_late)}, Test={len(y_test_late)}")

    # 6. Train and compare regressors
    print("\n=== Training Regressors ===")
    champion_reg, reg_summary = train_and_compare_regressors(
        X_train_late, y_train_late, X_val_late, y_val_late, X_test_late, y_test_late
    )
    print(f"Selected Champion Regressor: {reg_summary['champion_model_name']}")
    print(f"Test MAE: {reg_summary['champion_test_metrics']['mae']:.2f} days")
    print(f"Test RMSE: {reg_summary['champion_test_metrics']['rmse']:.2f} days")

    # 7. Extract feature importances
    feature_importance = {}
    if hasattr(champion_cls, "feature_importances_"):
        cls_imp = dict(zip(feature_names, [float(x) for x in champion_cls.feature_importances_]))
        sorted_cls = sorted(cls_imp.items(), key=lambda kv: kv[1], reverse=True)
        feature_importance["classifier_top_20"] = sorted_cls[:20]

    if hasattr(champion_reg, "feature_importances_"):
        reg_imp = dict(zip(feature_names, [float(x) for x in champion_reg.feature_importances_]))
        sorted_reg = sorted(reg_imp.items(), key=lambda kv: kv[1], reverse=True)
        feature_importance["regressor_top_20"] = sorted_reg[:20]

    # 8. Serialize artifacts
    print("\nSerializing artifacts...")
    joblib.dump(pipeline, CONFIG.feature_pipeline_artifact)
    joblib.dump(champion_cls, CONFIG.classifier_artifact)
    joblib.dump(champion_reg, CONFIG.regressor_artifact)

    model_metadata = {
        "model_version": "v1.0.0",
        "trained_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "training_time_seconds": round(time.time() - start_time, 2),
        "split_sizes": {
            "total_cleared_records": len(df),
            "train": len(train_df),
            "validation": len(val_df),
            "test": len(test_df),
        },
        "classifier": {
            "model_type": champion_cls.__class__.__name__,
            "champion_model_name": cls_summary["champion_model_name"],
            "optimal_threshold": optimal_threshold,
            "hyperparameters": {
                "n_estimators": CONFIG.rf_n_estimators,
                "max_depth": CONFIG.rf_max_depth,
                "min_samples_leaf": CONFIG.rf_min_samples_leaf,
                "class_weight": CONFIG.rf_class_weight,
            },
        },
        "regressor": {
            "model_type": champion_reg.__class__.__name__,
            "champion_model_name": reg_summary["champion_model_name"],
            "hyperparameters": {
                "n_estimators": CONFIG.reg_n_estimators,
                "max_depth": CONFIG.reg_max_depth,
                "min_samples_leaf": CONFIG.reg_min_samples_leaf,
            },
        },
        "artifacts": {
            "feature_pipeline": str(CONFIG.feature_pipeline_artifact),
            "classifier": str(CONFIG.classifier_artifact),
            "regressor": str(CONFIG.regressor_artifact),
        },
    }

    metrics_data = {
        "classification": cls_summary,
        "regression": reg_summary,
    }

    with open(CONFIG.model_metadata_file, "w", encoding="utf-8") as f:
        json.dump(model_metadata, f, indent=2)

    with open(CONFIG.evaluation_metrics_file, "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)

    with open(CONFIG.feature_importance_file, "w", encoding="utf-8") as f:
        json.dump(feature_importance, f, indent=2)

    print("All artifacts successfully saved to:", CONFIG.artifacts_dir)
    return model_metadata


if __name__ == "__main__":
    run_training()
