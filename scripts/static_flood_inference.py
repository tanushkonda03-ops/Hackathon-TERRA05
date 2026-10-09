"""Load and call the persisted historical mapped-flood susceptibility model.

The returned score is an uncalibrated model score, not a calibrated flood
probability. Extra input fields are ignored; all 13 model fields are required.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT_PATH = ROOT / "models" / "artifacts" / "static_flood_susceptibility_lr_v1.joblib"
FEATURES = (
    "elevation_mean",
    "slope_mean",
    "built_up_fraction",
    "vegetation_fraction",
    "water_fraction",
    "mangrove_fraction",
    "distance_to_water",
    "building_count",
    "building_density",
    "road_length_m",
    "has_railway",
    "has_hospital",
    "is_critical_asset_cell",
)


class StaticFloodPredictor:
    """A loaded predictor for one cell's 13 ordered geographic features."""

    def __init__(self, artifact_path: str | Path = DEFAULT_ARTIFACT_PATH):
        path = Path(artifact_path)
        if not path.is_file():
            raise FileNotFoundError(f"Trained inference artifact not found: {path}")
        artifact = joblib.load(path)
        if not isinstance(artifact, dict) or "pipeline" not in artifact or "metadata" not in artifact:
            raise ValueError("Artifact must contain a fitted pipeline and metadata")
        metadata = artifact["metadata"]
        if metadata.get("artifact_version") != 1:
            raise ValueError(f"Unsupported artifact version: {metadata.get('artifact_version')}")
        if tuple(metadata.get("feature_names_in_order", ())) != FEATURES:
            raise ValueError("Artifact feature order does not match this predictor schema")
        if metadata.get("target") != "flood_label":
            raise ValueError("Artifact target is not flood_label")
        if not hasattr(artifact["pipeline"], "predict_proba"):
            raise ValueError("Artifact pipeline does not support predict_proba")
        self.pipeline = artifact["pipeline"]
        self.metadata = metadata

    @staticmethod
    def _validate_record(features: Mapping[str, Any]) -> pd.DataFrame:
        if not isinstance(features, Mapping):
            raise TypeError("features must be a mapping of feature name to value")
        missing = [name for name in FEATURES if name not in features]
        if missing:
            raise ValueError(f"Missing required features: {', '.join(missing)}")

        values = {}
        invalid = []
        for name in FEATURES:
            value = features[name]
            if value is None:
                values[name] = np.nan
                continue
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                invalid.append(name)
                continue
            if np.isinf(numeric):
                invalid.append(name)
                continue
            values[name] = numeric
        if invalid:
            raise ValueError(f"Features must be numeric or null; invalid: {', '.join(invalid)}")
        return pd.DataFrame([[values[name] for name in FEATURES]], columns=FEATURES)

    def predict(self, features: Mapping[str, Any]) -> dict[str, Any]:
        """Return score and selected-threshold class for one cell record."""
        frame = self._validate_record(features)
        probabilities = self.pipeline.predict_proba(frame)
        classes = list(self.pipeline.named_steps["classifier"].classes_)
        try:
            positive_index = classes.index(1)
        except ValueError as exc:
            raise ValueError("Loaded model has no positive class 1") from exc
        score = float(probabilities[0, positive_index])
        threshold = float(self.metadata["decision_threshold"])
        return {
            "model_score": score,
            "predicted_class_at_selected_development_threshold": int(score >= threshold),
            "decision_threshold": threshold,
            "score_interpretation": "uncalibrated Logistic Regression model score; not a calibrated flood probability",
            "target_interpretation": self.metadata["target_interpretation"],
        }


def predict(features: Mapping[str, Any], artifact_path: str | Path = DEFAULT_ARTIFACT_PATH) -> dict[str, Any]:
    """Convenience function that loads the artifact and predicts one record."""
    return StaticFloodPredictor(artifact_path).predict(features)