"""
Classification Training and Evaluation Module.

Trains baseline and candidate classifiers (Dummy, LogisticRegression, RandomForest),
evaluates metrics on validation and test splits, tunes classification threshold,
and identifies the champion model.
"""

from __future__ import annotations

from typing import Dict, Any, Tuple
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    brier_score_loss,
    confusion_matrix,
)

from backend.ml.training.training_config import CONFIG


def evaluate_classifier_predictions(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """Compute comprehensive classification performance metrics."""
    y_pred = (y_prob >= threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel() if cm.shape == (2, 2) else (0, 0, 0, 0)

    try:
        roc_auc = float(roc_auc_score(y_true, y_prob))
    except Exception:
        roc_auc = 0.5

    try:
        pr_auc = float(average_precision_score(y_true, y_prob))
    except Exception:
        pr_auc = 0.0

    return {
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "brier_score": float(brier_score_loss(y_true, y_prob)),
        "threshold": float(threshold),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
    }


def find_optimal_threshold(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    step: float = 0.02,
) -> float:
    """Find the threshold in [0.2, 0.8] that maximizes the F1-score on validation set."""
    best_thresh = 0.50
    best_f1 = -1.0
    for thresh in np.arange(0.20, 0.81, step):
        y_pred = (y_prob >= thresh).astype(int)
        score = f1_score(y_true, y_pred, zero_division=0)
        if score > best_f1:
            best_f1 = score
            best_thresh = float(thresh)
    return best_thresh


def train_and_compare_classifiers(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
) -> Tuple[Any, Dict[str, Any], float]:
    """
    Train Dummy, LogisticRegression, and RandomForest classifiers.
    Select champion model based on validation ROC-AUC and PR-AUC.
    
    Returns:
        champion_model: The best performing trained classifier.
        results: Dictionary containing validation & test metrics for all models.
        optimal_threshold: Best classification threshold determined on val set.
    """
    models = {
        "dummy": DummyClassifier(strategy="prior"),
        "logistic_regression": LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=CONFIG.random_state,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=CONFIG.rf_n_estimators,
            max_depth=CONFIG.rf_max_depth,
            min_samples_leaf=CONFIG.rf_min_samples_leaf,
            class_weight=CONFIG.rf_class_weight,
            random_state=CONFIG.random_state,
            n_jobs=-1,
        ),
    }

    comparison = {}
    best_model_name = "random_forest"
    best_val_score = -1.0

    trained_models = {}

    for name, model in models.items():
        model.fit(X_train, y_train)
        trained_models[name] = model

        # Val predictions
        val_prob = model.predict_proba(X_val)[:, 1] if hasattr(model, "predict_proba") else np.full(len(X_val), 0.5)
        val_metrics = evaluate_classifier_predictions(y_val, val_prob, threshold=0.50)

        # Composite score for model selection: 0.5 * ROC-AUC + 0.5 * PR-AUC
        composite = 0.5 * val_metrics["roc_auc"] + 0.5 * val_metrics["pr_auc"]

        comparison[name] = {
            "validation_metrics": val_metrics,
            "composite_score": composite,
        }

        if composite > best_val_score:
            best_val_score = composite
            best_model_name = name

    champion_model = trained_models[best_model_name]

    # Find optimal threshold on validation set for champion model
    champ_val_prob = champion_model.predict_proba(X_val)[:, 1]
    optimal_thresh = find_optimal_threshold(y_val, champ_val_prob)
    champ_val_optimal_metrics = evaluate_classifier_predictions(y_val, champ_val_prob, threshold=optimal_thresh)

    # Test set evaluation of champion model
    champ_test_prob = champion_model.predict_proba(X_test)[:, 1]
    champ_test_default_metrics = evaluate_classifier_predictions(y_test, champ_test_prob, threshold=0.50)
    champ_test_optimal_metrics = evaluate_classifier_predictions(y_test, champ_test_prob, threshold=optimal_thresh)

    summary = {
        "champion_model_name": best_model_name,
        "optimal_threshold": optimal_thresh,
        "models_comparison": comparison,
        "champion_val_at_optimal_threshold": champ_val_optimal_metrics,
        "champion_test_at_default_threshold": champ_test_default_metrics,
        "champion_test_at_optimal_threshold": champ_test_optimal_metrics,
    }

    return champion_model, summary, optimal_thresh
