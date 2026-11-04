"""
Training Configuration for Finora ML Payment Risk Engine.
"""

from dataclasses import dataclass
from pathlib import Path

_BASE_ML_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class TrainingConfig:
    # Random seed for reproducibility
    random_state: int = 42

    # Chronological dataset splits
    train_ratio: float = 0.70
    val_ratio: float = 0.15
    test_ratio: float = 0.15

    # Classifier hyperparameters
    rf_n_estimators: int = 100
    rf_max_depth: int = 12
    rf_min_samples_leaf: int = 5
    rf_class_weight: str = "balanced"

    # Regressor hyperparameters
    reg_n_estimators: int = 100
    reg_max_depth: int = 10
    reg_min_samples_leaf: int = 5

    # Default threshold for late payment classification
    default_classification_threshold: float = 0.50

    # Paths (dynamically resolved to absolute paths relative to ml/ directory)
    artifacts_dir: Path = _BASE_ML_DIR / "artifacts"
    metadata_dir: Path = _BASE_ML_DIR / "metadata"
    processed_dir: Path = _BASE_ML_DIR / "processed"

    classifier_artifact: Path = _BASE_ML_DIR / "artifacts" / "payment_classifier.joblib"
    regressor_artifact: Path = _BASE_ML_DIR / "artifacts" / "payment_delay_regressor.joblib"
    feature_pipeline_artifact: Path = _BASE_ML_DIR / "artifacts" / "feature_pipeline.joblib"
    model_metadata_file: Path = _BASE_ML_DIR / "artifacts" / "model_metadata.json"
    evaluation_metrics_file: Path = _BASE_ML_DIR / "artifacts" / "evaluation_metrics.json"
    feature_importance_file: Path = _BASE_ML_DIR / "artifacts" / "feature_importance.json"


CONFIG = TrainingConfig()
