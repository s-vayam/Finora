import datetime
import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Tuple
import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier, RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import mean_squared_error, mean_absolute_error, accuracy_score, f1_score

backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from ml.fx.features import FEATURE_NAMES, FEATURE_SCHEMA_VERSION
from ml.fx.preprocessing import load_split, PROCESSED_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [FxTrain] %(message)s")
logger = logging.getLogger("finora.fx_train")

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
METADATA_DIR = Path(__file__).parent / "metadata"
MODEL_VERSION = "1.0.0"


def evaluate_regressors_on_val(
    X_train: np.ndarray, y_train: np.ndarray,
    X_val: np.ndarray, y_val: np.ndarray,
    origin_rates_val: np.ndarray, future_rates_val: np.ndarray,
    horizons_val: np.ndarray
) -> Tuple[str, Any, Dict[str, Any]]:
    # Baseline: Random Walk (predicts log return = 0.0)
    rw_pred_return = np.zeros_like(y_val)
    rw_pred_rate = origin_rates_val
    rw_rmse_return = float(np.sqrt(mean_squared_error(y_val, rw_pred_return)))
    rw_mae_rate = float(mean_absolute_error(future_rates_val, rw_pred_rate))

    candidates = {
        "ridge": Ridge(alpha=10.0, random_state=42),
        "hist_gradient_boosting": HistGradientBoostingRegressor(max_iter=100, max_depth=6, random_state=42),
    }

    best_name = "random_walk"
    best_model = None
    best_rmse = rw_rmse_return
    comparison = {
        "random_walk_baseline": {
            "rmse_return": rw_rmse_return,
            "mae_rate": rw_mae_rate
        }
    }

    for name, model in candidates.items():
        logger.info(f"Training regressor candidate: {name}...")
        model.fit(X_train, y_train)
        pred_return = model.predict(X_val)
        pred_rate = origin_rates_val * np.exp(pred_return)

        rmse_ret = float(np.sqrt(mean_squared_error(y_val, pred_return)))
        mae_rate = float(mean_absolute_error(future_rates_val, pred_rate))

        comparison[name] = {
            "rmse_return": rmse_ret,
            "mae_rate": mae_rate,
            "rmse_improvement_vs_baseline": float(rw_rmse_return - rmse_ret)
        }
        logger.info(f"  {name} -> Val RMSE Return: {rmse_ret:.6f} (Baseline: {rw_rmse_return:.6f})")

        if rmse_ret < best_rmse:
            best_rmse = rmse_ret
            best_name = name
            best_model = model

    if best_model is None:
        # If baseline was best, keep best performing ML model for deployment but mark comparison
        best_name = "hist_gradient_boosting"
        best_model = candidates["hist_gradient_boosting"]

    return best_name, best_model, comparison


def evaluate_classifiers_on_val(
    X_train: np.ndarray, y_train: np.ndarray,
    X_val: np.ndarray, y_val: np.ndarray
) -> Tuple[str, Any, Dict[str, Any]]:
    # Baseline: Dummy most frequent
    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit(X_train, y_train)
    dummy_pred = dummy.predict(X_val)
    dummy_acc = float(accuracy_score(y_val, dummy_pred))
    dummy_f1 = float(f1_score(y_val, dummy_pred, average="macro"))

    candidates = {
        "logistic_regression": LogisticRegression(max_iter=1000, random_state=42),
        "hist_gradient_boosting": HistGradientBoostingClassifier(max_iter=100, max_depth=6, random_state=42),
    }

    best_name = "dummy"
    best_model = None
    best_f1 = dummy_f1
    comparison = {
        "dummy_baseline": {
            "accuracy": dummy_acc,
            "macro_f1": dummy_f1
        }
    }

    for name, model in candidates.items():
        logger.info(f"Training classifier candidate: {name}...")
        model.fit(X_train, y_train)
        pred = model.predict(X_val)

        acc = float(accuracy_score(y_val, pred))
        f1 = float(f1_score(y_val, pred, average="macro"))

        comparison[name] = {
            "accuracy": acc,
            "macro_f1": f1,
            "f1_improvement_vs_baseline": float(f1 - dummy_f1)
        }
        logger.info(f"  {name} -> Val Macro F1: {f1:.4f}, Acc: {acc:.4f} (Baseline F1: {dummy_f1:.4f})")

        if f1 > best_f1:
            best_f1 = f1
            best_name = name
            best_model = model

    if best_model is None:
        best_name = "hist_gradient_boosting"
        best_model = candidates["hist_gradient_boosting"]

    return best_name, best_model, comparison


def train_pair_models(currency: str) -> Dict[str, Any]:
    logger.info(f"==================================================")
    logger.info(f"Starting model training pipeline for {currency}/INR")
    logger.info(f"==================================================")

    df_train = load_split(currency, "train")
    df_val = load_split(currency, "val")
    df_test = load_split(currency, "test")

    X_train = df_train[FEATURE_NAMES].values
    y_train_reg = df_train["target_log_return"].values
    y_train_cls = df_train["target_direction"].values

    X_val = df_val[FEATURE_NAMES].values
    y_val_reg = df_val["target_log_return"].values
    y_val_cls = df_val["target_direction"].values
    origin_rates_val = df_val["origin_rate"].values
    future_rates_val = df_val["future_rate"].values
    horizons_val = df_val["horizon_sessions"].values

    # 1. Regressor Selection & Training
    best_reg_name, reg_model, reg_comparison = evaluate_regressors_on_val(
        X_train, y_train_reg, X_val, y_val_reg,
        origin_rates_val, future_rates_val, horizons_val
    )

    # 2. Classifier Selection & Training
    best_cls_name, cls_model, cls_comparison = evaluate_classifiers_on_val(
        X_train, y_train_cls, X_val, y_val_cls
    )

    # Re-fit selected models on Train + Val combined for maximum statistical power
    logger.info(f"Refitting best models on combined Train+Val data ({len(X_train) + len(X_val):,} samples)...")
    X_train_val = np.vstack([X_train, X_val])
    y_train_val_reg = np.concatenate([y_train_reg, y_val_reg])
    y_train_val_cls = np.concatenate([y_train_cls, y_val_cls])

    reg_model.fit(X_train_val, y_train_val_reg)
    cls_model.fit(X_train_val, y_train_val_cls)

    # Save artifacts
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    reg_artifact_path = ARTIFACTS_DIR / f"fx_regressor_{currency.lower()}.joblib"
    cls_artifact_path = ARTIFACTS_DIR / f"fx_classifier_{currency.lower()}.joblib"

    joblib.dump(reg_model, reg_artifact_path)
    joblib.dump(cls_model, cls_artifact_path)
    logger.info(f"Saved regressor artifact to: {reg_artifact_path}")
    logger.info(f"Saved classifier artifact to: {cls_artifact_path}")

    return {
        "currency": currency,
        "selected_regressor": best_reg_name,
        "selected_classifier": best_cls_name,
        "regressor_comparison": reg_comparison,
        "classifier_comparison": cls_comparison,
        "regressor_artifact": str(reg_artifact_path),
        "classifier_artifact": str(cls_artifact_path),
    }


def train_all_supported_pairs():
    results = {}
    for curr in ["USD", "EUR", "GBP"]:
        res = train_pair_models(curr)
        results[curr] = res

    meta_file = METADATA_DIR / "training_summary.json"
    meta_file.parent.mkdir(parents=True, exist_ok=True)
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    logger.info("All currency pair models successfully trained and serialized.")
    return results


if __name__ == "__main__":
    train_all_supported_pairs()

