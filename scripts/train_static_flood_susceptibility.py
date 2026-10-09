"""Fit and persist the selected historical mapped-flood susceptibility pipeline.

Run from the repository root with:
    .venv/Scripts/python.exe scripts/train_static_flood_susceptibility.py

This fits the already selected configuration on the available labeled dataset;
it does not tune the model or report evaluation quality.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "ml_ready" / "ml_master_spatial_features.csv"
CONFIG_PATH = ROOT / "reports" / "ml_model_improvement_dev_folds_0_3" / "selected_configuration.json"
FEATURES_PATH = ROOT / "reports" / "ml_model_improvement_dev_folds_0_3" / "feature_lists.json"
ARTIFACT_PATH = ROOT / "models" / "artifacts" / "static_flood_susceptibility_lr_v1.joblib"
EXPECTED_FEATURES = [
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
]
TARGET = "flood_label"
ARTIFACT_VERSION = 1
RANDOM_SEED = 20261009


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not DATASET_PATH.is_file() or not CONFIG_PATH.is_file() or not FEATURES_PATH.is_file():
        raise FileNotFoundError("ML dataset or selected model metadata is missing")

    selected = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["selected_model"]
    feature_metadata = json.loads(FEATURES_PATH.read_text(encoding="utf-8"))
    if (
        selected["model"] != "logistic_regression"
        or selected["config_id"] != "logistic_regression_C_0.1"
        or selected["feature_set"] != "static_geographic"
        or selected["parameters"].get("C") != 0.1
        or selected["parameters"].get("class_weight") != "balanced"
    ):
        raise ValueError("Selected configuration no longer matches Logistic Regression C=0.1 geographic baseline")
    if feature_metadata["selected_predictors"] != EXPECTED_FEATURES:
        raise ValueError("Selected feature metadata differs from the required ordered 13-feature schema")
    if feature_metadata.get("selected_config_id") != selected["config_id"]:
        raise ValueError("Feature metadata and selected model configuration IDs differ")

    threshold_metadata = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["operating_threshold"]
    threshold = float(threshold_metadata["threshold"])

    frame = pd.read_csv(DATASET_PATH, usecols=EXPECTED_FEATURES + [TARGET])
    if frame.empty:
        raise ValueError("Training dataset contains no rows")
    missing = [feature for feature in EXPECTED_FEATURES if feature not in frame.columns]
    if missing:
        raise ValueError(f"Missing required model features: {missing}")
    frame[EXPECTED_FEATURES] = frame[EXPECTED_FEATURES].apply(pd.to_numeric, errors="coerce")
    labels = pd.to_numeric(frame[TARGET], errors="raise").astype(int)
    if not set(labels.unique()).issubset({0, 1}) or labels.nunique() != 2:
        raise ValueError("Training target must contain both binary classes 0 and 1")

    preprocessing = ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline([
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scaler", StandardScaler()),
                ]),
                EXPECTED_FEATURES,
            )
        ],
        remainder="drop",
    )
    pipeline = Pipeline([
        ("preprocess", preprocessing),
        (
            "classifier",
            LogisticRegression(
                C=0.1,
                class_weight="balanced",
                max_iter=2000,
                random_state=RANDOM_SEED,
            ),
        ),
    ])
    pipeline.fit(frame[EXPECTED_FEATURES], labels)
    if list(pipeline.named_steps["classifier"].classes_) != [0, 1]:
        raise ValueError("Fitted model class order is not [0, 1]")

    metadata = {
        "artifact_name": "static_flood_susceptibility_lr_v1",
        "artifact_version": ARTIFACT_VERSION,
        "target": TARGET,
        "target_interpretation": "historical mapped-flood susceptibility; not future-event forecasting",
        "feature_names_in_order": EXPECTED_FEATURES,
        "selected_configuration_id": selected["config_id"],
        "model_parameters": {
            "model": "LogisticRegression",
            "C": 0.1,
            "class_weight": "balanced",
            "max_iter": 2000,
            "random_state": RANDOM_SEED,
        },
        "preprocessing": {
            "numeric_imputation": "median, fitted on the full available labeled dataset",
            "scaling": "StandardScaler, fitted on the full available labeled dataset",
        },
        "decision_threshold": threshold,
        "decision_threshold_source": "selected development OOF F2 threshold from selected_configuration.json; not calibrated",
        "score_semantics": "predict_proba class-1 score from Logistic Regression; not a calibrated flood probability",
        "training_rows": int(len(frame)),
        "training_positive_rows": int(labels.sum()),
        "training_positive_rate": float(labels.mean()),
        "dataset_path": str(DATASET_PATH.relative_to(ROOT)),
        "dataset_sha256": _sha256(DATASET_PATH),
        "feature_metadata_path": str(FEATURES_PATH.relative_to(ROOT)),
        "selected_configuration_path": str(CONFIG_PATH.relative_to(ROOT)),
        "scikit_learn_version": sklearn.__version__,
        "limitations": [
            "Unlabelled cells are not confirmed non-flood observations.",
            "The target is historical mapped-flood susceptibility, not event-specific forecasting.",
            "The operating threshold is an OOF development choice and is not calibrated.",
        ],
    }

    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipeline, "metadata": metadata}, ARTIFACT_PATH, compress=3)
    print(f"Saved inference artifact: {ARTIFACT_PATH}")
    print(f"Rows used: {len(frame)}; positive labels: {int(labels.sum())}")
    print(f"Features: {len(EXPECTED_FEATURES)}; threshold: {threshold:.12f}")


if __name__ == "__main__":
    main()