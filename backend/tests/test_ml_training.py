"""
Tests for ML Training and Metric Evaluation Functions (Stage 3C).
"""

import numpy as np
import pytest
from backend.ml.training.train_classifier import (
    evaluate_classifier_predictions,
    find_optimal_threshold,
)
from backend.ml.training.train_regressor import evaluate_regressor_predictions


def test_evaluate_classifier_predictions():
    y_true = np.array([0, 1, 1, 0, 1, 0])
    y_prob = np.array([0.1, 0.8, 0.9, 0.2, 0.6, 0.3])

    metrics = evaluate_classifier_predictions(y_true, y_prob, threshold=0.5)

    assert 0.0 <= metrics["roc_auc"] <= 1.0
    assert metrics["roc_auc"] == 1.0  # Perfect ranking in this toy sample
    assert metrics["f1_score"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert 0.0 <= metrics["brier_score"] <= 1.0
    assert metrics["confusion_matrix"]["tp"] == 3
    assert metrics["confusion_matrix"]["tn"] == 3


def test_find_optimal_threshold():
    y_true = np.array([0, 0, 0, 1, 1, 1])
    y_prob = np.array([0.1, 0.2, 0.35, 0.38, 0.7, 0.9])

    # Default 0.5 would miss y_prob=0.38 (TP=2, FP=0, FN=1 -> F1=0.80)
    # Threshold 0.36 captures all 3 with 0 FP -> F1=1.0
    opt_thresh = find_optimal_threshold(y_true, y_prob)
    assert 0.30 <= opt_thresh <= 0.40


def test_evaluate_regressor_predictions_non_negative_clipping():
    y_true = np.array([5.0, 10.0, 2.0])
    # Model mistakenly predicts a negative value for the last sample
    y_pred = np.array([4.0, 12.0, -3.0])

    metrics = evaluate_regressor_predictions(y_true, y_pred)

    assert metrics["min_predicted_delay"] >= 0.0
    # Clipped predictions: [4.0, 12.0, 0.0] -> errors: |5-4|=1, |10-12|=2, |2-0|=2 -> MAE = 5/3 = 1.666...
    assert pytest.approx(metrics["mae"], 0.01) == 5.0 / 3.0
    assert metrics["median_absolute_error"] == 2.0
