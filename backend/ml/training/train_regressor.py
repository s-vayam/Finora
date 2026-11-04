"""
Regression Training and Evaluation Module for Payment Delay.

Trains regressors conditionally on late payments (payment_delay_days > 0).
Evaluates MAE, RMSE, R2, and Median Absolute Error on validation & test sets.
Enforces non-negative predicted delay post-processing.
"""

from __future__ import annotations

from typing import Dict, Any, Tuple
import numpy as np
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    root_mean_squared_error,
    r2_score,
    median_absolute_error,
)

from backend.ml.training.training_config import CONFIG


def evaluate_regressor_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> Dict[str, Any]:
    """Compute regression metrics ensuring predictions are non-negative."""
    # Post-processing guarantee: conditional delay cannot be negative
    y_pred_clipped = np.maximum(y_pred, 0.0)

    mae = float(mean_absolute_error(y_true, y_pred_clipped))
    rmse = float(root_mean_squared_error(y_true, y_pred_clipped))
    r2 = float(r2_score(y_true, y_pred_clipped))
    med_ae = float(median_absolute_error(y_true, y_pred_clipped))

    return {
        "mae": mae,
        "rmse": rmse,
        "r2_score": r2,
        "median_absolute_error": med_ae,
        "min_predicted_delay": float(np.min(y_pred_clipped)),
        "max_predicted_delay": float(np.max(y_pred_clipped)),
    }


def train_and_compare_regressors(
    X_train_late: np.ndarray,
    y_train_late: np.ndarray,
    X_val_late: np.ndarray,
    y_val_late: np.ndarray,
    X_test_late: np.ndarray,
    y_test_late: np.ndarray,
) -> Tuple[Any, Dict[str, Any]]:
    """
    Train DummyRegressor, Ridge, and RandomForestRegressor on late payments.
    Select champion model based on validation MAE.
    
    Returns:
        champion_model: The best performing trained regressor.
        results: Dictionary containing validation & test metrics for all models.
    """
    models = {
        "dummy_mean": DummyRegressor(strategy="mean"),
        "ridge": Ridge(alpha=1.0, random_state=CONFIG.random_state),
        "random_forest": RandomForestRegressor(
            n_estimators=CONFIG.reg_n_estimators,
            max_depth=CONFIG.reg_max_depth,
            min_samples_leaf=CONFIG.reg_min_samples_leaf,
            random_state=CONFIG.random_state,
            n_jobs=-1,
        ),
    }

    comparison = {}
    best_model_name = "random_forest"
    best_val_mae = float("inf")
    trained_models = {}

    for name, model in models.items():
        model.fit(X_train_late, y_train_late)
        trained_models[name] = model

        val_preds = model.predict(X_val_late)
        val_metrics = evaluate_regressor_predictions(y_val_late, val_preds)

        comparison[name] = {
            "validation_metrics": val_metrics,
        }

        if val_metrics["mae"] < best_val_mae:
            best_val_mae = val_metrics["mae"]
            best_model_name = name

    champion_model = trained_models[best_model_name]

    test_preds = champion_model.predict(X_test_late)
    test_metrics = evaluate_regressor_predictions(y_test_late, test_preds)

    summary = {
        "champion_model_name": best_model_name,
        "models_comparison": comparison,
        "champion_test_metrics": test_metrics,
    }

    return champion_model, summary
