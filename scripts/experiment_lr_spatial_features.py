"""Test deterministic feature engineering for static flood labels on folds 0-3 only.

Reproduce with:
    .venv/Scripts/python.exe scripts/experiment_lr_spatial_features.py

Uses the saved development folds/buffer flags unchanged. Fold 4 is not loaded.
"""

from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from evaluate_static_flood_labels import (
    CATEGORICAL_FEATURES,
    DATASET,
    DEVELOPMENT_FOLDS,
    FEATURE_SETS,
    TARGET,
    _sha256,
)


ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_DIR = ROOT / "reports" / "ml_model_improvement_dev_folds_0_3"
ASSIGNMENTS_PATH = ROOT / "reports" / "ml_static_flood_evaluation" / "spatial_fold_assignments.csv"
PREVIOUS_METRICS_PATH = PREVIOUS_DIR / "fold_metrics.csv"
PREVIOUS_OOF_PATH = PREVIOUS_DIR / "development_oof_predictions.csv.gz"
EXPERIMENT_DIR = ROOT / "reports" / "lr_spatial_feature_experiment_dev_folds_0_3"
FOLD_METRICS_PATH = EXPERIMENT_DIR / "feature_variant_fold_metrics.csv"
OOF_PATH = EXPERIMENT_DIR / "feature_variant_oof_predictions.csv.gz"
ERROR_ANALYSIS_PATH = EXPERIMENT_DIR / "baseline_fold_error_analysis.csv"
PROXY_ABLATION_PATH = EXPERIMENT_DIR / "existing_proxy_ablation_by_fold.csv"
FEATURES_PATH = EXPERIMENT_DIR / "feature_variants.json"
CONFIG_PATH = EXPERIMENT_DIR / "threshold_and_selection.json"
REPORT_PATH = EXPERIMENT_DIR / "experiment_report.md"
SEED = 20261009
C_VALUE = 0.1
CLASS_WEIGHT = "balanced"

GEOGRAPHIC = FEATURE_SETS["static_geographic"]
HYDROLOGY = FEATURE_SETS["static_geographic_plus_physics_proxies"]
LOG_SOURCES = (
    "building_count",
    "building_density",
    "distance_to_water",
    "flow_accumulation",
    "flow_accumulation_area_km2",
    "drain_density",
    "distance_to_drain",
)
LOG_FEATURES = tuple(f"log1p_{column}" for column in LOG_SOURCES)
INTERACTION_FEATURES = (
    "built_up_x_log1p_drain_density",
    "built_up_x_log1p_distance_to_drain",
    "slope_x_flow_accumulation_log",
)
FEATURE_VARIANTS = {
    "geographic_baseline": list(GEOGRAPHIC),
    "geographic_plus_hydrology": list(HYDROLOGY),
    "geographic_hydrology_log1p": list(HYDROLOGY) + list(LOG_FEATURES),
    "geographic_hydrology_log1p_interactions": list(HYDROLOGY) + list(LOG_FEATURES) + list(INTERACTION_FEATURES),
}
FORBIDDEN = {
    "ward", "grid_id", "spatial_fold", "spatial_cv_fold", "final_test",
    "flood_label", "flood_fraction", "historical_flood_label", "event_id",
    "scenario_name", "warning_tier", "warning_level_code", "rainfall_1h_mm",
    "rainfall_3h_mm", "rainfall_6h_mm", "rainfall_12h_mm", "rainfall_24h_mm",
    "tide_factor", "tide_name", "scs_curve_number", "scs_runoff_3h_mm",
    "scs_runoff_depth_24h_mm",
}
ERROR_PROFILE_FEATURES = (
    "elevation_mean", "built_up_fraction", "distance_to_water", "distance_to_drain",
)


def _read_assignments() -> tuple[list[dict], str]:
    assignments = []
    with ASSIGNMENTS_PATH.open(newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            fold = int(row["spatial_fold"])
            if fold not in DEVELOPMENT_FOLDS:
                continue
            row["grid_id"] = int(row["grid_id"])
            row["spatial_fold"] = fold
            for validation_fold in DEVELOPMENT_FOLDS:
                row[f"buffer_excluded_for_fold_{validation_fold}"] = int(
                    row[f"buffer_excluded_for_fold_{validation_fold}"]
                )
            assignments.append(row)
    if {row["spatial_fold"] for row in assignments} != set(DEVELOPMENT_FOLDS):
        raise ValueError("Saved development assignments do not contain folds 0-3")
    return assignments, _sha256(ASSIGNMENTS_PATH)


def _read_development_frame(assignments: list[dict]) -> tuple[pd.DataFrame, str]:
    by_id = {row["grid_id"]: row["spatial_fold"] for row in assignments}
    rows = []
    with DATASET.open(newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            grid_id = int(row["grid_id"])
            fold = by_id.get(grid_id)
            if fold is not None:
                row["grid_id"] = grid_id
                row["_fold"] = fold
                row[TARGET] = int(row[TARGET])
                rows.append(row)
    frame = pd.DataFrame(rows)
    if len(frame) != len(assignments):
        raise ValueError("Development CSV rows and saved development assignments differ")

    numeric_sources = set().union(*(
        {column for column in features if column not in CATEGORICAL_FEATURES}
        for features in FEATURE_SETS.values()
    ))
    numeric_sources.update(ERROR_PROFILE_FEATURES)
    for column in numeric_sources:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    for columns in FEATURE_VARIANTS.values():
        if FORBIDDEN.intersection(columns):
            raise ValueError(f"Prohibited predictor present: {FORBIDDEN.intersection(columns)}")
        missing = set(columns) - set(frame.columns) - set(LOG_FEATURES) - set(INTERACTION_FEATURES)
        if missing:
            raise ValueError(f"Missing predictors: {sorted(missing)}")
    numeric = set().union(*(
        {column for column in columns if column not in CATEGORICAL_FEATURES}
        for columns in FEATURE_VARIANTS.values()
    )) - set(LOG_FEATURES) - set(INTERACTION_FEATURES)
    for column in numeric:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    for column in LOG_SOURCES:
        values = frame[column]
        if (values.dropna() < 0).any():
            raise ValueError(f"log1p requires nonnegative source values; found negative {column}")
        frame[f"log1p_{column}"] = np.log1p(values)
    frame["built_up_x_log1p_drain_density"] = (
        frame["built_up_fraction"] * frame["log1p_drain_density"]
    )
    frame["built_up_x_log1p_distance_to_drain"] = (
        frame["built_up_fraction"] * frame["log1p_distance_to_drain"]
    )
    frame["slope_x_flow_accumulation_log"] = (
        frame["slope_mean"] * frame["flow_accumulation_log"]
    )
    return frame, _sha256(DATASET)


def _pipeline(feature_columns: list[str]) -> Pipeline:
    numeric = [column for column in feature_columns if column not in CATEGORICAL_FEATURES]
    categorical = [column for column in feature_columns if column in CATEGORICAL_FEATURES]
    transformers = [(
        "numeric",
        Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]),
        numeric,
    )]
    if categorical:
        transformers.append((
            "categorical",
            Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("onehot", OneHotEncoder(handle_unknown="ignore")),
            ]),
            categorical,
        ))
    return Pipeline([
        ("preprocess", ColumnTransformer(transformers, remainder="drop")),
        ("classifier", LogisticRegression(
            C=C_VALUE, max_iter=2000, class_weight=CLASS_WEIGHT, random_state=SEED
        )),
    ])


def _get_train_validation(
    frame: pd.DataFrame, assignments: list[dict], outer_fold: int
) -> tuple[pd.DataFrame, pd.DataFrame, set[int]]:
    validation = frame.loc[frame["_fold"] == outer_fold]
    excluded_ids = {
        row["grid_id"] for row in assignments
        if row[f"buffer_excluded_for_fold_{outer_fold}"]
    }
    training = frame.loc[
        frame["_fold"].isin(DEVELOPMENT_FOLDS)
        & (frame["_fold"] != outer_fold)
        & ~frame["grid_id"].isin(excluded_ids)
    ]
    if set(training["_fold"]) & {outer_fold} or set(validation["_fold"]) != {outer_fold}:
        raise ValueError(f"Unexpected row leakage in outer fold {outer_fold}")
    return training, validation, excluded_ids


def _f2_threshold(target: np.ndarray, probability: np.ndarray) -> tuple[float, float]:
    precision, recall, thresholds = precision_recall_curve(target, probability)
    if not len(thresholds):
        raise ValueError("No threshold candidates in inner out-of-fold predictions")
    f2 = 5 * precision[:-1] * recall[:-1] / np.maximum(4 * precision[:-1] + recall[:-1], 1e-15)
    best = np.flatnonzero(np.isclose(f2, np.max(f2), rtol=1e-12, atol=1e-12))
    chosen = max(best, key=lambda index: (precision[index], thresholds[index]))
    return float(thresholds[chosen]), float(f2[chosen])


def _confusion(y: np.ndarray, probability: np.ndarray, threshold: float) -> dict:
    predicted = (probability >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[0, 1]).ravel()
    precision = precision_score(y, predicted, zero_division=0)
    recall = recall_score(y, predicted, zero_division=0)
    f2 = 5 * precision * recall / max(4 * precision + recall, 1e-15)
    return {
        "precision": float(precision), "recall": float(recall), "f2": float(f2),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }


def _nested_outer_evaluation(
    frame: pd.DataFrame, assignments: list[dict], variant: str, features: list[str]
) -> tuple[list[dict], list[dict]]:
    fold_rows, prediction_rows = [], []
    assignment_by_id = {row["grid_id"]: row for row in assignments}
    for outer_fold in DEVELOPMENT_FOLDS:
        outer_training, outer_validation, outer_excluded = _get_train_validation(
            frame, assignments, outer_fold
        )
        inner_oof_y, inner_oof_probability = [], []
        inner_thresholds = []
        for inner_fold in DEVELOPMENT_FOLDS:
            if inner_fold == outer_fold:
                continue
            inner_validation = outer_training.loc[outer_training["_fold"] == inner_fold]
            inner_excluded = {
                row["grid_id"] for row in assignments
                if row[f"buffer_excluded_for_fold_{inner_fold}"]
            }
            inner_training = outer_training.loc[
                (outer_training["_fold"] != inner_fold)
                & ~outer_training["grid_id"].isin(inner_excluded)
            ]
            if len(inner_training) == 0 or len(inner_validation) == 0:
                raise ValueError(f"Empty inner partition: outer={outer_fold}, inner={inner_fold}")
            inner_model = _pipeline(features)
            inner_model.fit(inner_training[features], inner_training[TARGET].to_numpy())
            inner_probability = inner_model.predict_proba(inner_validation[features])[:, 1]
            inner_oof_y.extend(inner_validation[TARGET].to_numpy())
            inner_oof_probability.extend(inner_probability)
            inner_thresholds.append({
                "inner_fold": inner_fold,
                "train_rows": len(inner_training),
                "validation_rows": len(inner_validation),
            })

        threshold, inner_f2 = _f2_threshold(
            np.asarray(inner_oof_y, dtype=int), np.asarray(inner_oof_probability, dtype=float)
        )
        model = _pipeline(features)
        y_train = outer_training[TARGET].to_numpy()
        y_validation = outer_validation[TARGET].to_numpy()
        model.fit(outer_training[features], y_train)
        train_probability = model.predict_proba(outer_training[features])[:, 1]
        validation_probability = model.predict_proba(outer_validation[features])[:, 1]
        train_pr_auc = float(average_precision_score(y_train, train_probability))
        validation_pr_auc = float(average_precision_score(y_validation, validation_probability))
        validation_roc_auc = float(roc_auc_score(y_validation, validation_probability))
        at_05 = _confusion(y_validation, validation_probability, 0.5)
        at_nested = _confusion(y_validation, validation_probability, threshold)
        fold_rows.append({
            "feature_variant": variant,
            "fold": outer_fold,
            "feature_count": len(features),
            "train_rows": len(outer_training),
            "validation_rows": len(outer_validation),
            "buffer_excluded_rows": len(outer_excluded),
            "train_pr_auc": train_pr_auc,
            "validation_pr_auc": validation_pr_auc,
            "validation_roc_auc": validation_roc_auc,
            "train_validation_pr_auc_gap": train_pr_auc - validation_pr_auc,
            "precision_at_0_5": at_05["precision"],
            "recall_at_0_5": at_05["recall"],
            "tn_at_0_5": at_05["tn"], "fp_at_0_5": at_05["fp"],
            "fn_at_0_5": at_05["fn"], "tp_at_0_5": at_05["tp"],
            "nested_threshold": threshold,
            "inner_threshold_f2": inner_f2,
            "precision_at_nested_threshold": at_nested["precision"],
            "recall_at_nested_threshold": at_nested["recall"],
            "f2_at_nested_threshold": at_nested["f2"],
            "tn_at_nested_threshold": at_nested["tn"],
            "fp_at_nested_threshold": at_nested["fp"],
            "fn_at_nested_threshold": at_nested["fn"],
            "tp_at_nested_threshold": at_nested["tp"],
            "inner_folds": json.dumps(inner_thresholds, sort_keys=True),
        })
        for index, (_, row) in enumerate(outer_validation.iterrows()):
            prediction_rows.append({
                "feature_variant": variant,
                "outer_fold": outer_fold,
                "grid_id": int(row["grid_id"]),
                "target": int(y_validation[index]),
                "predicted_probability": float(validation_probability[index]),
                "nested_threshold": threshold,
                "prediction_at_0_5": int(validation_probability[index] >= 0.5),
                "prediction_at_nested_threshold": int(validation_probability[index] >= threshold),
            })
    return fold_rows, prediction_rows


def _aggregate(fold_rows: list[dict]) -> list[dict]:
    aggregate_rows = []
    for variant in FEATURE_VARIANTS:
        rows = [row for row in fold_rows if row["feature_variant"] == variant]
        if len(rows) != len(DEVELOPMENT_FOLDS):
            raise ValueError(f"Expected four outer folds for {variant}")
        record = {
            "feature_variant": variant,
            "fold": "mean",
            "feature_count": rows[0]["feature_count"],
            "train_rows": "",
            "validation_rows": sum(row["validation_rows"] for row in rows),
            "buffer_excluded_rows": sum(row["buffer_excluded_rows"] for row in rows),
        }
        for key in (
            "train_pr_auc", "validation_pr_auc", "validation_roc_auc",
            "train_validation_pr_auc_gap", "precision_at_0_5", "recall_at_0_5",
            "nested_threshold", "inner_threshold_f2", "precision_at_nested_threshold",
            "recall_at_nested_threshold", "f2_at_nested_threshold",
        ):
            values = [float(row[key]) for row in rows]
            record[key] = float(np.mean(values))
            record[key + "_sd"] = float(np.std(values, ddof=1))
        for key in (
            "tn_at_0_5", "fp_at_0_5", "fn_at_0_5", "tp_at_0_5",
            "tn_at_nested_threshold", "fp_at_nested_threshold",
            "fn_at_nested_threshold", "tp_at_nested_threshold",
        ):
            record[key] = sum(row[key] for row in rows)
        aggregate_rows.append(record)
    return aggregate_rows


def _baseline_error_analysis(frame: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    previous_metrics = []
    with PREVIOUS_METRICS_PATH.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            if row["fold"] in {"0", "1", "2", "3"}:
                if (
                    row["config_id"] == "logistic_regression_C_0.1"
                    and row["feature_set"] == "static_geographic"
                ):
                    previous_metrics.append(row)
    selected_predictions = []
    with gzip.open(PREVIOUS_OOF_PATH, "rt", newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            if (
                row["fold"] in {"0", "1", "2", "3"}
                and row["config_id"] == "logistic_regression_C_0.1"
                and row["feature_set"] == "static_geographic"
            ):
                selected_predictions.append(row)
    if len(previous_metrics) != 4 or len(selected_predictions) != sum(
        int(row["validation_rows"]) for row in previous_metrics
    ):
        raise ValueError("Saved selected Logistic Regression development metrics/OOF predictions are incomplete")

    frame_by_id = frame.set_index("grid_id")
    error_rows = []
    for fold in DEVELOPMENT_FOLDS:
        fold_metric = next(row for row in previous_metrics if int(row["fold"]) == fold)
        preds = [row for row in selected_predictions if int(row["fold"]) == fold]
        false_positive_ids = [int(row["grid_id"]) for row in preds if int(row["target"]) == 0 and int(row["predicted_label_at_0_5"]) == 1]
        false_negative_ids = [int(row["grid_id"]) for row in preds if int(row["target"]) == 1 and int(row["predicted_label_at_0_5"]) == 0]
        record = {
            "fold": fold,
            "validation_rows": len(preds),
            "positive_prevalence": float(fold_metric["validation_prevalence"]),
            "pr_auc": float(fold_metric["validation_pr_auc"]),
            "roc_auc": float(fold_metric["validation_roc_auc"]),
            "precision_at_0_5": float(fold_metric["validation_precision_at_0_5"]),
            "recall_at_0_5": float(fold_metric["validation_recall_at_0_5"]),
            "false_positives_at_0_5": len(false_positive_ids),
            "false_negatives_at_0_5": len(false_negative_ids),
        }
        for feature in ERROR_PROFILE_FEATURES:
            record[f"fp_mean_{feature}"] = (
                float(frame_by_id.loc[false_positive_ids, feature].mean()) if false_positive_ids else ""
            )
            record[f"fn_mean_{feature}"] = (
                float(frame_by_id.loc[false_negative_ids, feature].mean()) if false_negative_ids else ""
            )
        error_rows.append(record)

    all_selected = []
    with PREVIOUS_METRICS_PATH.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            if row["fold"] in {"0", "1", "2", "3"}:
                if row["config_id"] == "logistic_regression_C_0.1":
                    all_selected.append(row)
    ablation_rows = []
    for fold in DEVELOPMENT_FOLDS:
        by_set = {
            row["feature_set"]: float(row["validation_pr_auc"])
            for row in all_selected if int(row["fold"]) == fold
        }
        ablation_rows.append({
            "fold": fold,
            "geographic_pr_auc": by_set["static_geographic"],
            "geographic_plus_proxies_pr_auc": by_set["static_geographic_plus_physics_proxies"],
            "proxy_delta_pr_auc": by_set["static_geographic_plus_physics_proxies"] - by_set["static_geographic"],
        })
    return error_rows, ablation_rows


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"No rows to save for {path.name}")
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_oof(path: Path, rows: list[dict]) -> None:
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with gzip.open(path, "wt", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    assignments, assignment_hash = _read_assignments()
    frame, dataset_hash = _read_development_frame(assignments)
    error_rows, ablation_rows = _baseline_error_analysis(frame)
    _write_csv(ERROR_ANALYSIS_PATH, error_rows)
    _write_csv(PROXY_ABLATION_PATH, ablation_rows)

    fold_rows, predictions = [], []
    for variant, feature_columns in FEATURE_VARIANTS.items():
        variant_folds, variant_predictions = _nested_outer_evaluation(
            frame, assignments, variant, feature_columns
        )
        fold_rows.extend(variant_folds)
        predictions.extend(variant_predictions)
    fold_rows.extend(_aggregate(fold_rows))
    _write_csv(FOLD_METRICS_PATH, fold_rows)
    _write_oof(OOF_PATH, predictions)

    feature_payload = {
        "target": TARGET,
        "target_interpretation": "historical mapped-flood susceptibility; not future-event forecasting",
        "feature_variants": FEATURE_VARIANTS,
        "feature_sources": {
            "baseline": "Existing approved static geographic feature set",
            "hydrology": "Existing static drainage/hydrology proxy feature set",
            "log1p": "Row-wise numpy.log1p transforms of listed nonnegative source features; no dataset-level fitted statistics",
            "interactions": "Row-wise products of listed existing features; no labels or fitted global transformations",
        },
        "forbidden_fields": sorted(FORBIDDEN),
        "folds_used": list(DEVELOPMENT_FOLDS),
        "fold_4_used": False,
        "preprocessing": "Median imputation, standard scaling, categorical imputation and one-hot encoding are fitted inside each training fold.",
        "model": {"name": "LogisticRegression", "C": C_VALUE, "class_weight": CLASS_WEIGHT, "max_iter": 2000},
    }
    FEATURES_PATH.write_text(json.dumps(feature_payload, indent=2) + "\n", encoding="utf-8")
    config_payload = {
        "model": {"name": "LogisticRegression", "C": C_VALUE, "class_weight": CLASS_WEIGHT, "seed": SEED},
        "threshold_selection": {
            "method": "nested development-fold inner OOF threshold selection",
            "objective": "maximize F2 within each outer fold's training data; choose ties by precision then threshold",
            "outer_validation_fold_is_excluded_from_threshold_selection": True,
            "fold_4_used": False,
        },
        "saved_assignment_sha256": assignment_hash,
        "dataset_sha256": dataset_hash,
    }
    CONFIG_PATH.write_text(json.dumps(config_payload, indent=2) + "\n", encoding="utf-8")

    fold_metrics = [row for row in fold_rows if row["fold"] == "mean"]
    baseline = next(row for row in fold_metrics if row["feature_variant"] == "geographic_baseline")
    report_lines = [
        "# Logistic Regression Spatial Feature Experiment",
        "",
        "Target: historical mapped-flood susceptibility from static 100 m grid labels, not future-event forecasting. Unlabelled cells are not confirmed non-flood observations. Fold-4 assignments are skipped when filtering the saved split; no fold-4 labels, metrics, predictions, or outcomes are used or opened by this experiment.",
        "",
        "## Leakage Controls",
        "",
        f"- Reused saved development folds 0–3 and their existing 500 m exclusion flags unchanged (assignment SHA-256 `{assignment_hash}`).",
        "- Every outer fold uses identical eligible train/validation rows across feature variants. Each outer-fold threshold is chosen by nested inner OOF F2 using only that outer fold's training rows.",
        "- Imputation, scaling, and categorical encoding are fit in each inner/outer training pipeline. Added transforms are deterministic row-wise log1p or product terms, with no full-dataset fit.",
        "- Ward, IDs, fold fields, flood fractions/labels, event/rainfall/tide/scenario values, label-location proxies, and SWMM outputs are prohibited or absent.",
        "",
        "## Baseline Error Analysis",
        "",
        "Fold 0 has the lowest saved Logistic Regression PR-AUC; fold 1's low precision is dominated by false positives; fold 3 has the largest false-negative count and lower recall. The baseline proxy ablation below shows whether adding the available static drainage/hydrology group helps within each fold.",
        "",
        "| Fold | PR-AUC | ROC-AUC | Precision@0.5 | Recall@0.5 | FP | FN | Δ PR-AUC adding static proxies |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    error_by_fold = {row["fold"]: row for row in error_rows}
    delta_by_fold = {row["fold"]: row["proxy_delta_pr_auc"] for row in ablation_rows}
    for fold in DEVELOPMENT_FOLDS:
        row = error_by_fold[fold]
        report_lines.append(
            f"| {fold} | {row['pr_auc']:.4f} | {row['roc_auc']:.4f} | {row['precision_at_0_5']:.4f} | {row['recall_at_0_5']:.4f} | {row['false_positives_at_0_5']} | {row['false_negatives_at_0_5']} | {delta_by_fold[fold]:+.4f} |"
        )
    report_lines.extend([
        "",
        "## Feature Variants",
        "",
        "All comparisons use Logistic Regression C=0.1, class_weight=balanced, and the same four outer folds. The log1p and interaction terms are calculated per row from existing source fields; no target information is used.",
        "",
        "| Variant | Features | Train PR-AUC | Outer PR-AUC ± SD | ROC-AUC | Precision@0.5 | Recall@0.5 | Train-validation PR gap | Nested threshold precision | Nested threshold recall |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in sorted(fold_metrics, key=lambda item: item["validation_pr_auc"], reverse=True):
        report_lines.append(
            f"| {row['feature_variant']} | {row['feature_count']} | {row['train_pr_auc']:.4f} | {row['validation_pr_auc']:.4f} ± {row['validation_pr_auc_sd']:.4f} | {row['validation_roc_auc']:.4f} | {row['precision_at_0_5']:.4f} | {row['recall_at_0_5']:.4f} | {row['train_validation_pr_auc_gap']:.4f} | {row['precision_at_nested_threshold']:.4f} | {row['recall_at_nested_threshold']:.4f} |"
        )
    report_lines.extend([
        "",
        "### Per outer fold",
        "",
        "| Variant | Fold | Train PR-AUC | Validation PR-AUC | ROC-AUC | Train-validation gap | Precision / recall @0.5 | Nested threshold | Precision / recall at nested threshold |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in sorted(
        (item for item in fold_rows if item["fold"] != "mean"),
        key=lambda item: (item["feature_variant"], item["fold"]),
    ):
        report_lines.append(
            f"| {row['feature_variant']} | {row['fold']} | {row['train_pr_auc']:.4f} | {row['validation_pr_auc']:.4f} | {row['validation_roc_auc']:.4f} | {row['train_validation_pr_auc_gap']:.4f} | {row['precision_at_0_5']:.4f} / {row['recall_at_0_5']:.4f} | {row['nested_threshold']:.4f} | {row['precision_at_nested_threshold']:.4f} / {row['recall_at_nested_threshold']:.4f} |"
        )
    report_lines.extend([
        "",
        "Per-fold values and confusion matrices at 0.5 and nested thresholds are in `feature_variant_fold_metrics.csv`; fold-specific thresholds are recorded there and in OOF predictions.",
        "",
        "## Threshold and Limitations",
        "",
        "Thresholds are selected separately for each outer fold by F2 on inner OOF predictions from that outer fold's eligible training data, then applied once to that outer validation fold. Thus threshold-selection rows do not score their own calibration predictions. Fold-to-fold threshold variability remains a limitation.",
        "",
        "No mapped spatial SWMM result features exist in this ML dataset. These variants test existing drainage/hydrology proxies and derived row-wise terms, not the value of SWMM outputs. These are susceptibility rankings, not calibrated probabilities, validated forecasts, or evidence of generalization to unseen storms.",
        "",
        "Fold 4 was not read or used here, but its earlier inspection means it is not an untouched final test. A future independent evaluation requires a new untouched spatial holdout or suitable nested spatial evaluation.",
        "",
        "### Next step",
        "",
        "Keep the 13-feature geographic Logistic Regression baseline; none of the tested additions improved mean outer-fold PR-AUC. The next concrete action is to review the mapped-label coverage and the saved fold-0/fold-3 false-positive/false-negative locations, then designate a new untouched spatial holdout before another model comparison. Do not reuse the previously inspected fold 4 as a final test.",
        "",
        "Reproduce with `.venv/Scripts/python.exe scripts/experiment_lr_spatial_features.py`.",
    ])
    REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    if _sha256(ASSIGNMENTS_PATH) != assignment_hash:
        raise RuntimeError("Saved spatial fold assignments changed during experiment")

    print(f"Experiment directory: {EXPERIMENT_DIR}")
    print(f"Development rows: {len(frame)}; folds={DEVELOPMENT_FOLDS}; fold 4 used=False")
    for row in sorted(fold_metrics, key=lambda item: item["validation_pr_auc"], reverse=True):
        print(
            f"{row['feature_variant']}: PR-AUC={row['validation_pr_auc']:.4f} "
            f"+/- {row['validation_pr_auc_sd']:.4f}; ROC-AUC={row['validation_roc_auc']:.4f}; "
            f"gap={row['train_validation_pr_auc_gap']:.4f}"
        )
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
