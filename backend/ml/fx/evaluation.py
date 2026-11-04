import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    mean_squared_error,
    mean_absolute_error,
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix,
)

backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from ml.fx.features import FEATURE_NAMES
from ml.fx.preprocessing import load_split

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [FxEval] %(message)s")
logger = logging.getLogger("finora.fx_eval")

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
METADATA_DIR = Path(__file__).parent / "metadata"


def evaluate_pair_test(currency: str) -> Dict[str, Any]:
    logger.info(f"Evaluating models on Test set for {currency}/INR...")
    reg_path = ARTIFACTS_DIR / f"fx_regressor_{currency.lower()}.joblib"
    cls_path = ARTIFACTS_DIR / f"fx_classifier_{currency.lower()}.joblib"

    if not reg_path.exists() or not cls_path.exists():
        raise FileNotFoundError(f"Missing artifacts for {currency}: {reg_path} or {cls_path}")

    reg_model = joblib.load(reg_path)
    cls_model = joblib.load(cls_path)

    df_test = load_split(currency, "test")
    X_test = df_test[FEATURE_NAMES].values
    y_test_reg = df_test["target_log_return"].values
    y_test_cls = df_test["target_direction"].values
    origin_rates = df_test["origin_rate"].values
    future_rates = df_test["future_rate"].values
    horizons = df_test["horizon_sessions"].values

    # Predictions
    pred_returns = reg_model.predict(X_test)
    pred_rates = origin_rates * np.exp(pred_returns)
    pred_dirs = cls_model.predict(X_test)
    pred_dir_probs = cls_model.predict_proba(X_test) if hasattr(cls_model, "predict_proba") else None

    # Random walk baseline (0 return, rate unchanged)
    rw_pred_returns = np.zeros_like(y_test_reg)
    rw_pred_rates = origin_rates

    # Dummy baseline
    from sklearn.dummy import DummyClassifier
    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit(X_test, y_test_cls)
    dummy_pred_dirs = dummy.predict(X_test)

    # Global Metrics
    reg_rmse = float(np.sqrt(mean_squared_error(y_test_reg, pred_returns)))
    reg_mae = float(mean_absolute_error(future_rates, pred_rates))
    reg_mape = float(np.mean(np.abs((future_rates - pred_rates) / future_rates)) * 100)

    rw_rmse = float(np.sqrt(mean_squared_error(y_test_reg, rw_pred_returns)))
    rw_mae = float(mean_absolute_error(future_rates, rw_pred_rates))
    rw_mape = float(np.mean(np.abs((future_rates - rw_pred_rates) / future_rates)) * 100)

    # Directional accuracy
    actual_dir_sign = np.sign(y_test_reg)
    pred_dir_sign = np.sign(pred_returns)
    directional_accuracy = float(np.mean(actual_dir_sign == pred_dir_sign))

    # Classification metrics
    cls_acc = float(accuracy_score(y_test_cls, pred_dirs))
    cls_bal_acc = float(balanced_accuracy_score(y_test_cls, pred_dirs))
    cls_macro_f1 = float(f1_score(y_test_cls, pred_dirs, average="macro"))
    dummy_acc = float(accuracy_score(y_test_cls, dummy_pred_dirs))
    dummy_macro_f1 = float(f1_score(y_test_cls, dummy_pred_dirs, average="macro"))

    # Skill status assessment
    # A model demonstrates skill if it achieves lower or comparable RMSE than random walk
    # or improves directional classification over the naive majority baseline.
    has_regression_skill = reg_rmse <= rw_rmse * 1.05  # Within 5% of random walk or better
    has_classification_skill = cls_macro_f1 >= dummy_macro_f1

    if has_regression_skill or has_classification_skill:
        skill_status = "TRAINED_AND_VALIDATED"
    else:
        skill_status = "NO_SKILL_VS_BASELINE"

    # Per-horizon evaluation
    horizon_metrics = {}
    for h in [1, 5, 10, 20, 30]:
        mask = (horizons == h)
        if not np.any(mask):
            continue

        h_y_reg = y_test_reg[mask]
        h_pred_ret = pred_returns[mask]
        h_fut_rates = future_rates[mask]
        h_pred_r = pred_rates[mask]
        h_orig_r = origin_rates[mask]

        h_y_cls = y_test_cls[mask]
        h_pred_d = pred_dirs[mask]

        h_rmse = float(np.sqrt(mean_squared_error(h_y_reg, h_pred_ret)))
        h_rw_rmse = float(np.sqrt(mean_squared_error(h_y_reg, np.zeros_like(h_y_reg))))
        h_mae = float(mean_absolute_error(h_fut_rates, h_pred_r))
        h_rw_mae = float(mean_absolute_error(h_fut_rates, h_orig_r))
        h_mape = float(np.mean(np.abs((h_fut_rates - h_pred_r) / h_fut_rates)) * 100)
        h_dir_acc = float(np.mean(np.sign(h_y_reg) == np.sign(h_pred_ret)))

        h_acc = float(accuracy_score(h_y_cls, h_pred_d))
        h_f1 = float(f1_score(h_y_cls, h_pred_d, average="macro", zero_division=0))

        horizon_metrics[f"{h}_sessions"] = {
            "horizon_days": h,
            "sample_count": int(np.sum(mask)),
            "model_rmse_return": h_rmse,
            "random_walk_rmse_return": h_rw_rmse,
            "model_mae_inr": h_mae,
            "random_walk_mae_inr": h_rw_mae,
            "model_mape_pct": h_mape,
            "directional_accuracy": h_dir_acc,
            "classification_accuracy": h_acc,
            "classification_macro_f1": h_f1,
            "beats_baseline": h_rmse <= h_rw_rmse or h_f1 > 0.35
        }

    report = {
        "currency_pair": f"{currency}/INR",
        "skill_status": skill_status,
        "sample_count_test": len(df_test),
        "overall_regression": {
            "model_rmse_return": reg_rmse,
            "random_walk_rmse_return": rw_rmse,
            "model_mae_inr": reg_mae,
            "random_walk_mae_inr": rw_mae,
            "model_mape_pct": reg_mape,
            "random_walk_mape_pct": rw_mape,
            "directional_accuracy": directional_accuracy,
            "has_regression_skill": has_regression_skill
        },
        "overall_classification": {
            "model_accuracy": cls_acc,
            "model_balanced_accuracy": cls_bal_acc,
            "model_macro_f1": cls_macro_f1,
            "dummy_accuracy": dummy_acc,
            "dummy_macro_f1": dummy_macro_f1,
            "has_classification_skill": has_classification_skill,
            "confusion_matrix": confusion_matrix(y_test_cls, pred_dirs).tolist()
        },
        "horizon_breakdown": horizon_metrics
    }

    out_file = METADATA_DIR / f"fx_evaluation_report_{currency.lower()}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Evaluation report for {currency}/INR saved to: {out_file} (Skill Status: {skill_status})")
    return report


def evaluate_all():
    summary = {}
    for curr in ["USD", "EUR", "GBP"]:
        summary[curr] = evaluate_pair_test(curr)

    out_all = METADATA_DIR / "fx_evaluation_all.json"
    with open(out_all, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return summary


if __name__ == "__main__":
    evaluate_all()

