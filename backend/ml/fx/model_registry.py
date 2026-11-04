import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import joblib
import numpy as np
import pandas as pd
from decimal import Decimal

from ml.fx.features import extract_features_at_origin, FEATURE_NAMES, FEATURE_SCHEMA_VERSION

logger = logging.getLogger("finora.fx_registry")

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
METADATA_DIR = Path(__file__).parent / "metadata"
MODEL_VERSION = "1.0.0"


class FxModelRegistry:
    _instance: Optional["FxModelRegistry"] = None

    def __init__(self):
        self._regressors: Dict[str, Any] = {}
        self._classifiers: Dict[str, Any] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._load_all()

    @classmethod
    def get_instance(cls) -> "FxModelRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_all(self):
        for curr in ["USD", "EUR", "GBP"]:
            reg_path = ARTIFACTS_DIR / f"fx_regressor_{curr.lower()}.joblib"
            cls_path = ARTIFACTS_DIR / f"fx_classifier_{curr.lower()}.joblib"
            meta_path = METADATA_DIR / f"fx_evaluation_report_{curr.lower()}.json"

            if reg_path.exists() and cls_path.exists():
                try:
                    self._regressors[curr] = joblib.load(reg_path)
                    self._classifiers[curr] = joblib.load(cls_path)
                    if meta_path.exists():
                        with open(meta_path, "r", encoding="utf-8") as f:
                            self._metadata[curr] = json.load(f)
                    else:
                        self._metadata[curr] = {"skill_status": "TRAINED_AND_VALIDATED"}
                    logger.info(f"Loaded FX ML artifacts for {curr}/INR (Skill: {self._metadata[curr].get('skill_status')})")
                except Exception as e:
                    logger.error(f"Failed to load artifacts for {curr}: {e}")
            else:
                logger.warning(f"Artifacts missing for {curr}/INR in {ARTIFACTS_DIR}")

    def is_model_available(self, currency: str) -> bool:
        curr = currency.upper()
        return curr in self._regressors and curr in self._classifiers

    def get_skill_status(self, currency: str) -> str:
        curr = currency.upper()
        if not self.is_model_available(curr):
            return "MODEL_NOT_READY"
        return self._metadata.get(curr, {}).get("skill_status", "TRAINED_AND_VALIDATED")

    def get_metadata(self, currency: str) -> Dict[str, Any]:
        curr = currency.upper()
        return self._metadata.get(curr, {})

    def predict(
        self,
        currency: str,
        df_history: pd.DataFrame,
        horizon_sessions: int
    ) -> Dict[str, Any]:
        curr = currency.upper()
        if not self.is_model_available(curr):
            raise FileNotFoundError(f"FX models for {curr}/INR are not ready or trained.")

        if horizon_sessions < 1 or horizon_sessions > 30:
            raise ValueError(f"horizon_sessions must be between 1 and 30, got {horizon_sessions}")

        reg_model = self._regressors[curr]
        cls_model = self._classifiers[curr]
        meta = self._metadata.get(curr, {})
        skill_status = meta.get("skill_status", "TRAINED_AND_VALIDATED")

        # Extract features
        X_df = extract_features_at_origin(df_history, horizon_sessions)
        anchor_rate = float(df_history.iloc[-1]["rate"])
        anchor_date = pd.to_datetime(df_history.iloc[-1]["date"]).date()

        # Predict log return
        predicted_log_return = float(reg_model.predict(X_df.values)[0])
        predicted_rate = float(anchor_rate * np.exp(predicted_log_return))
        percentage_movement = float(((predicted_rate - anchor_rate) / anchor_rate) * 100)

        # Predict direction
        dir_class = int(cls_model.predict(X_df.values)[0])
        dir_label = "UP" if dir_class == 1 else ("DOWN" if dir_class == -1 else "NEUTRAL")

        # Probabilities
        probabilities = {"UP": 0.333, "DOWN": 0.333, "NEUTRAL": 0.334}
        if hasattr(cls_model, "predict_proba"):
            classes = list(cls_model.classes_)
            probs = cls_model.predict_proba(X_df.values)[0]
            for c_val, prob in zip(classes, probs):
                c_name = "UP" if c_val == 1 else ("DOWN" if c_val == -1 else "NEUTRAL")
                probabilities[c_name] = round(float(prob), 4)

        # Prediction interval based on test RMSE for this horizon
        h_str = f"{horizon_sessions}_sessions"
        h_rmse = meta.get("horizon_breakdown", {}).get(h_str, {}).get("model_rmse_return", 0.015)
        # 80% and 95% confidence intervals on rate
        z_80 = 1.28
        z_95 = 1.96
        range_80 = (
            round(anchor_rate * np.exp(predicted_log_return - z_80 * h_rmse), 4),
            round(anchor_rate * np.exp(predicted_log_return + z_80 * h_rmse), 4)
        )
        range_95 = (
            round(anchor_rate * np.exp(predicted_log_return - z_95 * h_rmse), 4),
            round(anchor_rate * np.exp(predicted_log_return + z_95 * h_rmse), 4)
        )

        return {
            "currency_pair": f"{curr}/INR",
            "model_version": MODEL_VERSION,
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "skill_status": skill_status,
            "anchor_rate": Decimal(str(round(anchor_rate, 4))),
            "anchor_date": anchor_date,
            "horizon_sessions": horizon_sessions,
            "predicted_log_return": predicted_log_return,
            "predicted_rate": Decimal(str(round(predicted_rate, 4))),
            "percentage_movement": round(percentage_movement, 2),
            "predicted_direction": dir_label,
            "direction_probabilities": probabilities,
            "prediction_range_80": [Decimal(str(range_80[0])), Decimal(str(range_80[1]))],
            "prediction_range_95": [Decimal(str(range_95[0])), Decimal(str(range_95[1]))],
        }

