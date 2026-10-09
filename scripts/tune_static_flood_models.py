"""Development-only model improvement for static mapped-flood susceptibility.

Run from the repository root with the project environment:
    .venv/Scripts/python.exe scripts/tune_static_flood_models.py

Only saved folds 0-3 and their saved 500 m exclusion flags are loaded. Fold 4
labels, metrics, and predictions are not read or evaluated by this experiment.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
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
from sklearn.tree import DecisionTreeClassifier
import sklearn

from evaluate_static_flood_labels import (
    CATEGORICAL_FEATURES,
    DATASET,
    DEVELOPMENT_FOLDS,
    FEATURE_SETS,
    TARGET,
    _sha256,
)


ROOT = Path(__file__).resolve().parents[1]
BASE_EVALUATION_DIR = ROOT / "reports" / "ml_static_flood_evaluation"
ASSIGNMENTS_PATH = BASE_EVALUATION_DIR / "spatial_fold_assignments.csv"
EXPERIMENT_DIR = ROOT / "reports" / "ml_model_improvement_dev_folds_0_3"
METRICS_PATH = EXPERIMENT_DIR / "fold_metrics.csv"
PREDICTIONS_PATH = EXPERIMENT_DIR / "development_oof_predictions.csv.gz"
PR_CURVE_PATH = EXPERIMENT_DIR / "selected_precision_recall_curve.csv"
CONFIG_PATH = EXPERIMENT_DIR / "selected_configuration.json"
FEATURES_PATH = EXPERIMENT_DIR / "feature_lists.json"
VERSION_PATH = EXPERIMENT_DIR / "dataset_version.json"
REPORT_PATH = EXPERIMENT_DIR / "experiment_report.md"
SEED = 20261009
LOGISTIC_C_GRID = (0.1, 1.0, 10.0)
TREE_SETTINGS = {"max_depth": 3, "min_samples_leaf": 50, "ccp_alpha": 0.001}
FOREST_SETTINGS = {
    "n_estimators": 200,
    "max_depth": 12,
    "min_samples_leaf": 20,
    "max_features": "sqrt",
}
PROHIBITED_FEATURES = {
    "grid_id",
    "ward",
    "spatial_fold",
    "spatial_cv_fold",
    "final_test",
    "flood_label",
    "flood_fraction",
    "historical_flood_label",
    "event_id",
    "scenario_name",
    "warning_tier",
    "warning_level_code",
    "rainfall_1h_mm",
    "rainfall_3h_mm",
    "rainfall_6h_mm",
    "rainfall_12h_mm",
    "rainfall_24h_mm",
    "tide_factor",
    "tide_name",
    "scs_curve_number",
    "scs_runoff_3h_mm",
    "scs_runoff_depth_24h_mm",
}


def _read_development_inputs() -> tuple[pd.DataFrame, list[dict], str, str]:
    if not DATASET.is_file() or not ASSIGNMENTS_PATH.is_file():
        raise FileNotFoundError("Required ML dataset or saved spatial assignments are missing")

    assignments = []
    with ASSIGNMENTS_PATH.open(newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            fold = int(row["spatial_fold"])
            if fold in DEVELOPMENT_FOLDS:
                row["grid_id"] = int(row["grid_id"])
                row["spatial_fold"] = fold
                for validation_fold in DEVELOPMENT_FOLDS:
                    row[f"buffer_excluded_for_fold_{validation_fold}"] = int(
                        row[f"buffer_excluded_for_fold_{validation_fold}"]
                    )
                assignments.append(row)

    if not assignments or {row["spatial_fold"] for row in assignments} != set(DEVELOPMENT_FOLDS):
        raise ValueError("Saved development folds 0-3 are incomplete")
    development_ids = {row["grid_id"] for row in assignments}
    if len(development_ids) != len(assignments):
        raise ValueError("Saved development assignments contain duplicate grid IDs")

    development_rows = []
    with DATASET.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        columns = list(reader.fieldnames or [])
        for row in reader:
            grid_id = int(row["grid_id"])
            if grid_id in development_ids:
                development_rows.append(row)
    frame = pd.DataFrame(development_rows)
    if set(frame["grid_id"].astype(int)) != development_ids:
        raise ValueError("Saved development folds and ML dataset IDs differ")
    fold_by_id = {row["grid_id"]: row["spatial_fold"] for row in assignments}
    frame["_fold"] = frame["grid_id"].astype(int).map(fold_by_id)
    frame[TARGET] = pd.to_numeric(frame[TARGET], errors="raise").astype(int)
    numeric_features = set().union(*(
        {column for column in features if column not in CATEGORICAL_FEATURES}
        for features in FEATURE_SETS.values()
    ))
    for column in numeric_features:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    for feature_set, features in FEATURE_SETS.items():
        forbidden = PROHIBITED_FEATURES.intersection(features)
        if forbidden:
            raise ValueError(f"Leakage-prone features in {feature_set}: {sorted(forbidden)}")
        absent = set(features) - set(columns)
        if absent:
            raise ValueError(f"Missing predictors for {feature_set}: {sorted(absent)}")
    if "flood_fraction" not in columns or "ward" not in columns:
        raise ValueError("Expected leakage-sensitive source columns are absent for exclusion checks")
    return frame, assignments, _sha256(DATASET), _sha256(ASSIGNMENTS_PATH)


def _model_specs() -> list[dict]:
    specs = [{
        "model": "prevalence_baseline",
        "config_id": "prevalence_baseline",
        "params": {"probability": "training-fold prevalence", "decision_threshold": 0.5},
        "complexity_rank": 99,
    }]
    for c_value in LOGISTIC_C_GRID:
        specs.append({
            "model": "logistic_regression",
            "config_id": f"logistic_regression_C_{c_value:g}",
            "params": {"C": c_value, "class_weight": "balanced", "max_iter": 2000},
            "complexity_rank": (0, c_value),
        })
    specs.extend([
        {
            "model": "shallow_regularized_tree",
            "config_id": "shallow_regularized_tree",
            "params": {**TREE_SETTINGS, "class_weight": "balanced"},
            "complexity_rank": (1, 0),
        },
        {
            "model": "random_forest",
            "config_id": "random_forest_conservative",
            "params": {**FOREST_SETTINGS, "class_weight": "balanced_subsample"},
            "complexity_rank": (2, 0),
        },
        {
            "model": "extra_trees",
            "config_id": "extra_trees_conservative",
            "params": {**FOREST_SETTINGS, "class_weight": "balanced"},
            "complexity_rank": (3, 0),
        },
    ])
    for spec in specs:
        for feature_set in FEATURE_SETS:
            spec_key = {key: value for key, value in spec.items() if key != "complexity_rank"}
            spec[feature_set] = {
                **spec_key,
                "feature_set": feature_set,
                "selection_complexity": (
                    len(FEATURE_SETS[feature_set]),
                    *(spec["complexity_rank"] if isinstance(spec["complexity_rank"], tuple) else (spec["complexity_rank"],)),
                ),
            }
    return specs


def _new_classifier(spec: dict):
    params = spec["params"]
    if spec["model"] == "logistic_regression":
        return LogisticRegression(
            C=params["C"],
            max_iter=params["max_iter"],
            class_weight=params["class_weight"],
            random_state=SEED,
        )
    if spec["model"] == "shallow_regularized_tree":
        return DecisionTreeClassifier(**params, random_state=SEED)
    if spec["model"] == "random_forest":
        return RandomForestClassifier(**params, random_state=SEED, n_jobs=-1)
    if spec["model"] == "extra_trees":
        return ExtraTreesClassifier(**params, random_state=SEED, n_jobs=-1)
    raise ValueError(f"Unknown model: {spec['model']}")


def _pipeline(feature_columns: list[str], classifier) -> Pipeline:
    numeric = [column for column in feature_columns if column not in CATEGORICAL_FEATURES]
    categorical = [column for column in feature_columns if column in CATEGORICAL_FEATURES]
    transformers = [
        (
            "numeric",
            Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]),
            numeric,
        )
    ]
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
        ("classifier", classifier),
    ])


def _classification_metrics(target: np.ndarray, probability: np.ndarray, threshold: float) -> dict:
    predicted = (probability >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(target, predicted, labels=[0, 1]).ravel()
    return {
        "pr_auc": float(average_precision_score(target, probability)),
        "roc_auc": float(roc_auc_score(target, probability)),
        "precision": float(precision_score(target, predicted, zero_division=0)),
        "recall": float(recall_score(target, predicted, zero_division=0)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def _evaluate(frame: pd.DataFrame, assignments: list[dict]) -> tuple[list[dict], list[dict]]:
    specs = _model_specs()
    fold_metrics = []
    oof_predictions = []
    for spec in specs:
        for feature_set, feature_columns in FEATURE_SETS.items():
            validation_by_fold = {}
            for fold in DEVELOPMENT_FOLDS:
                validation_mask = frame["_fold"].to_numpy() == fold
                validation = frame.loc[validation_mask]
                excluded_ids = {
                    row["grid_id"]
                    for row in assignments
                    if row[f"buffer_excluded_for_fold_{fold}"]
                }
                train_mask = (
                    frame["_fold"].isin(DEVELOPMENT_FOLDS)
                    & (frame["_fold"] != fold)
                    & ~frame["grid_id"].astype(int).isin(excluded_ids)
                ).to_numpy()
                training = frame.loc[train_mask]
                y_train = training[TARGET].to_numpy()
                y_validation = validation[TARGET].to_numpy()
                if len(np.unique(y_train)) != 2 or len(np.unique(y_validation)) != 2:
                    raise ValueError(f"Fold {fold} has a single-class train/validation partition")

                if spec["model"] == "prevalence_baseline":
                    train_probability = np.full(len(training), float(y_train.mean()))
                    validation_probability = np.full(len(validation), float(y_train.mean()))
                else:
                    estimator = _pipeline(feature_columns, _new_classifier(spec))
                    estimator.fit(training[feature_columns], y_train)
                    train_probability = estimator.predict_proba(training[feature_columns])[:, 1]
                    validation_probability = estimator.predict_proba(validation[feature_columns])[:, 1]

                train_metrics = _classification_metrics(y_train, train_probability, 0.5)
                validation_metrics = _classification_metrics(y_validation, validation_probability, 0.5)
                metric_row = {
                    "fold": fold,
                    "feature_set": feature_set,
                    "model": spec["model"],
                    "config_id": spec["config_id"],
                    "parameters_json": json.dumps(spec["params"], sort_keys=True),
                    "train_rows": len(training),
                    "validation_rows": len(validation),
                    "buffer_excluded_rows": len(excluded_ids),
                    "train_prevalence": float(y_train.mean()),
                    "validation_prevalence": float(y_validation.mean()),
                    "train_pr_auc": train_metrics["pr_auc"],
                    "validation_pr_auc": validation_metrics["pr_auc"],
                    "train_roc_auc": train_metrics["roc_auc"],
                    "validation_roc_auc": validation_metrics["roc_auc"],
                    "train_precision_at_0_5": train_metrics["precision"],
                    "validation_precision_at_0_5": validation_metrics["precision"],
                    "train_recall_at_0_5": train_metrics["recall"],
                    "validation_recall_at_0_5": validation_metrics["recall"],
                    "train_tn": train_metrics["tn"],
                    "train_fp": train_metrics["fp"],
                    "train_fn": train_metrics["fn"],
                    "train_tp": train_metrics["tp"],
                    "tn": validation_metrics["tn"],
                    "fp": validation_metrics["fp"],
                    "fn": validation_metrics["fn"],
                    "tp": validation_metrics["tp"],
                    "train_pr_auc_std": "",
                    "validation_pr_auc_std": "",
                    "train_roc_auc_std": "",
                    "validation_roc_auc_std": "",
                    "train_precision_at_0_5_std": "",
                    "validation_precision_at_0_5_std": "",
                    "train_recall_at_0_5_std": "",
                    "validation_recall_at_0_5_std": "",
                    "validation_pr_auc_se": "",
                    "validation_train_pr_auc_gap": train_metrics["pr_auc"] - validation_metrics["pr_auc"],
                    "status": "complete",
                }
                fold_metrics.append(metric_row)
                validation_by_fold[fold] = (validation, validation_probability)
                for index, (_, record) in enumerate(validation.iterrows()):
                    oof_predictions.append({
                        "fold": fold,
                        "grid_id": int(record["grid_id"]),
                        "model": spec["model"],
                        "config_id": spec["config_id"],
                        "feature_set": feature_set,
                        "target": int(y_validation[index]),
                        "predicted_probability": float(validation_probability[index]),
                        "predicted_label_at_0_5": int(validation_probability[index] >= 0.5),
                    })

            # The predictions are all out-of-fold; this row summarizes only development folds.
            del validation_by_fold

    aggregate_rows = []
    grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in fold_metrics:
        grouped[(row["model"], row["config_id"], row["feature_set"])].append(row)
    for (model, config_id, feature_set), fold_rows in grouped.items():
        aggregate = {
            "fold": "macro_mean",
            "feature_set": feature_set,
            "model": model,
            "config_id": config_id,
            "parameters_json": fold_rows[0]["parameters_json"],
            "train_rows": "",
            "validation_rows": sum(row["validation_rows"] for row in fold_rows),
            "buffer_excluded_rows": sum(row["buffer_excluded_rows"] for row in fold_rows),
            "train_prevalence": float(np.mean([row["train_prevalence"] for row in fold_rows])),
            "validation_prevalence": float(np.mean([row["validation_prevalence"] for row in fold_rows])),
        }
        for key in (
            "train_pr_auc", "validation_pr_auc", "train_roc_auc", "validation_roc_auc",
            "train_precision_at_0_5", "validation_precision_at_0_5",
            "train_recall_at_0_5", "validation_recall_at_0_5",
        ):
            vals = [float(row[key]) for row in fold_rows]
            aggregate[key] = float(np.mean(vals))
            aggregate[key + "_std"] = float(np.std(vals, ddof=1))
        aggregate["validation_pr_auc_se"] = aggregate["validation_pr_auc_std"] / np.sqrt(len(fold_rows))
        for key in ("train_tn", "train_fp", "train_fn", "train_tp", "tn", "fp", "fn", "tp"):
            aggregate[key] = sum(row[key] for row in fold_rows)
        aggregate["validation_train_pr_auc_gap"] = aggregate["train_pr_auc"] - aggregate["validation_pr_auc"]
        aggregate["status"] = "complete"
        aggregate_rows.append(aggregate)
    fold_metrics.extend(aggregate_rows)
    return fold_metrics, oof_predictions


def _select_configuration(fold_metrics: list[dict]) -> dict:
    aggregate_rows = [row for row in fold_metrics if row["fold"] == "macro_mean"]
    candidates = [row for row in aggregate_rows if row["model"] != "prevalence_baseline"]
    best = max(candidates, key=lambda row: float(row["validation_pr_auc"]))
    one_se_cutoff = float(best["validation_pr_auc"]) - float(best["validation_pr_auc_se"])
    eligible = [row for row in candidates if float(row["validation_pr_auc"]) >= one_se_cutoff]
    complexity = {spec["config_id"]: spec["complexity_rank"] for spec in _model_specs()}
    selected = min(
        eligible,
        key=lambda row: (
            len(FEATURE_SETS[row["feature_set"]]),
            complexity[row["config_id"]],
            float(row["validation_pr_auc_std"]),
            -float(row["validation_pr_auc"]),
        ),
    )
    return {
        "model": selected["model"],
        "config_id": selected["config_id"],
        "feature_set": selected["feature_set"],
        "parameters": json.loads(selected["parameters_json"]),
        "development_macro_pr_auc": selected["validation_pr_auc"],
        "development_pr_auc_sd": selected["validation_pr_auc_std"],
        "development_pr_auc_se": selected["validation_pr_auc_se"],
        "best_macro_pr_auc": best["validation_pr_auc"],
        "one_standard_error_cutoff": one_se_cutoff,
        "one_se_eligible_configurations": [row["config_id"] + "/" + row["feature_set"] for row in eligible],
        "selection_rule": "Identify the highest development macro PR-AUC; retain configurations within one standard error of it; select the fewest predictors, then lowest predeclared model-complexity rank, then lowest fold PR-AUC SD. Fold 4 is not loaded or scored.",
    }


def _select_threshold(selected: dict, predictions: list[dict]) -> tuple[dict, list[dict]]:
    selected_predictions = [
        row for row in predictions
        if row["config_id"] == selected["config_id"] and row["feature_set"] == selected["feature_set"]
    ]
    selected_predictions.sort(key=lambda row: (row["fold"], row["grid_id"]))
    target = np.asarray([row["target"] for row in selected_predictions], dtype=int)
    probability = np.asarray([row["predicted_probability"] for row in selected_predictions], dtype=float)
    precision, recall, thresholds = precision_recall_curve(target, probability)
    threshold_rows = []
    if not len(thresholds):
        raise ValueError("No thresholds returned for selected OOF predictions")
    f2 = 5 * precision[:-1] * recall[:-1] / np.maximum(4 * precision[:-1] + recall[:-1], 1e-15)
    best_score = float(np.max(f2))
    best_indices = np.flatnonzero(np.isclose(f2, best_score, rtol=1e-12, atol=1e-12))
    best_index = max(best_indices, key=lambda index: (precision[index], thresholds[index]))
    threshold = float(thresholds[best_index])
    for index, value in enumerate(thresholds):
        threshold_rows.append({
            "threshold": float(value),
            "precision": float(precision[index]),
            "recall": float(recall[index]),
            "f2": float(f2[index]),
            "selected": int(index == best_index),
        })
    threshold_metrics = _classification_metrics(target, probability, threshold)
    return {
        "selection_data": "pooled out-of-fold predictions from development folds 0-3 only",
        "objective": "maximize F2 = 5 * precision * recall / (4 * precision + recall), prioritizing recall while retaining a precision penalty; ties choose higher precision then higher threshold",
        "threshold": threshold,
        "f2": best_score,
        "oof_metrics_at_selected_threshold": threshold_metrics,
        "caveat": "The threshold and its displayed OOF metrics are selected and assessed on the same development OOF predictions; this is a development operating point, not an unbiased final performance estimate.",
    }, threshold_rows


def _write_predictions(path: Path, rows: list[dict]) -> None:
    with gzip.open(path, "wt", newline="", encoding="utf-8") as file:
        fieldnames = list(dict.fromkeys(key for row in rows for key in row))
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_outputs(
    frame: pd.DataFrame,
    fold_metrics: list[dict],
    predictions: list[dict],
    selected: dict,
    threshold: dict,
    threshold_curve: list[dict],
    dataset_hash: str,
    assignments_hash: str,
) -> None:
    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    with METRICS_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(fold_metrics[0]))
        writer.writeheader()
        writer.writerows(fold_metrics)
    with PR_CURVE_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(threshold_curve[0]))
        writer.writeheader()
        writer.writerows(threshold_curve)

    features = {
        "selected_config_id": selected["config_id"],
        "selected_feature_set": selected["feature_set"],
        "selected_predictors": FEATURE_SETS[selected["feature_set"]],
        "all_compared_feature_sets": FEATURE_SETS,
        "excluded_predictor_fields": sorted(PROHIBITED_FEATURES),
        "folds_used": list(DEVELOPMENT_FOLDS),
        "fold_4_used": False,
    }
    for row in predictions:
        if row["config_id"] == selected["config_id"] and row["feature_set"] == selected["feature_set"]:
            row["selected_oof_threshold"] = threshold["threshold"]
            row["predicted_label_at_selected_threshold"] = int(
                row["predicted_probability"] >= threshold["threshold"]
            )
    _write_predictions(PREDICTIONS_PATH, predictions)
    FEATURES_PATH.write_text(json.dumps(features, indent=2) + "\n", encoding="utf-8")
    CONFIG_PATH.write_text(json.dumps({"selected_model": selected, "operating_threshold": threshold}, indent=2) + "\n", encoding="utf-8")
    versions = {
        "experiment": "development-only static mapped-flood susceptibility model improvement",
        "dataset_path": str(DATASET.relative_to(ROOT)),
        "dataset_sha256": dataset_hash,
        "saved_development_assignment_sha256": assignments_hash,
        "rows_used": len(frame),
        "positive_count_used": int(frame[TARGET].sum()),
        "positive_rate_used": float(frame[TARGET].mean()),
        "folds_used": list(DEVELOPMENT_FOLDS),
        "fold_4_used": False,
        "seed": SEED,
        "scikit_learn_version": sklearn.__version__,
        "logistic_regularization_grid_C": list(LOGISTIC_C_GRID),
        "random_forest_and_extra_trees_settings": FOREST_SETTINGS,
    }
    VERSION_PATH.write_text(json.dumps(versions, indent=2) + "\n", encoding="utf-8")

    aggregate_rows = [row for row in fold_metrics if row["fold"] == "macro_mean"]
    selected_stats = next(
        row for row in aggregate_rows
        if row["config_id"] == selected["config_id"] and row["feature_set"] == selected["feature_set"]
    )
    baseline_stats = next(
        row for row in aggregate_rows
        if row["model"] == "prevalence_baseline" and row["feature_set"] == "static_geographic"
    )
    report = f"""# Development-Only Static Flood Model Improvement

This experiment uses only existing historical mapped-flood susceptibility labels (`flood_label`) on static 100 m cells. It is not future-event forecasting, calibration, or validation. The previous evaluation's inspected fold 4 was not read, trained on, compared, or used for threshold selection here.

## Leakage and Split Controls

- Used only saved assignment folds 0–3 and their existing 500 m exclusion flags. The assignment CSV was read-only and its SHA-256 is saved in `dataset_version.json`.
- The dataset loader retained only development-fold rows. Flood fraction, labels/duplicates, ward, IDs/split fields, event/rainfall/tide/scenario fields, and known-flood-location proxies are prohibited and runtime-checked against feature lists.
- Geographic feature count: {len(FEATURE_SETS['static_geographic'])}; geographic + available drainage/hydrology proxy feature count: {len(FEATURE_SETS['static_geographic_plus_physics_proxies'])}. The latter tests static proxies only; mapped spatial SWMM output features are absent and their value is not tested.
- Median imputation, scaling, categorical imputation, and encoding were fit inside each training fold.
- OOF predictions cover development validation folds 0–3. No evaluation was performed on fold 4.

## Experiment

Models: Logistic Regression with `C` in {list(LOGISTIC_C_GRID)} (including the existing `C=1` baseline), the prior shallow regularized tree, a class-weighted Random Forest, and class-weighted Extra Trees. Ensemble limits: {FOREST_SETTINGS}. The prevalence baseline is included. Seed: `{SEED}`; scikit-learn `{sklearn.__version__}`.

Model selection used the one-standard-error rule on development macro PR-AUC: first find the highest mean; consider candidates within one standard error; then choose the smallest feature set, lowest predeclared model-complexity rank, lowest fold PR-AUC SD, and finally higher mean PR-AUC. Selected: **{selected['config_id']}** with **{selected['feature_set']}**; macro PR-AUC {float(selected_stats['validation_pr_auc']):.4f}, fold SD {float(selected_stats['validation_pr_auc_std']):.4f}. No fold-4 data informed this choice.

### Mean development metrics (threshold 0.5; PR-AUC/ROC-AUC/precision/recall)

| Model/config | Feature set | Train PR-AUC | Validation PR-AUC ± SD | ROC-AUC | Precision | Recall | Summed TN / FP / FN / TP | PR train-validation gap |
|---|---|---:|---:|---:|---:|---:|---|---:|
"""
    for row in aggregate_rows:
        report += (
            f"| {row['config_id']} | {row['feature_set']} | {float(row['train_pr_auc']):.4f} | "
            f"{float(row['validation_pr_auc']):.4f} ± {float(row['validation_pr_auc_std']):.4f} | "
            f"{float(row['validation_roc_auc']):.4f} | {float(row['validation_precision_at_0_5']):.4f} | "
            f"{float(row['validation_recall_at_0_5']):.4f} | {row['tn']}/{row['fp']}/{row['fn']}/{row['tp']} | "
            f"{float(row['validation_train_pr_auc_gap']):.4f} |\n"
        )
    report += f"""
Prevalence baseline macro PR-AUC is {float(baseline_stats['validation_pr_auc']):.4f}, equal to the mean fold prevalence. Per-fold metrics and training-versus-validation results are in `fold_metrics.csv`; individual confusion matrices are represented by TN/FP/FN/TP for each fold.

## OOF Threshold

For the selected configuration, an operating threshold was chosen from pooled OOF predictions by maximizing **F2** (`beta=2`, weighting recall more than precision); ties prefer higher precision, then higher threshold. Threshold: **{threshold['threshold']:.6f}**. OOF precision {threshold['oof_metrics_at_selected_threshold']['precision']:.4f}, recall {threshold['oof_metrics_at_selected_threshold']['recall']:.4f}, F2 {threshold['f2']:.4f}; confusion TN/FP/FN/TP {threshold['oof_metrics_at_selected_threshold']['tn']}/{threshold['oof_metrics_at_selected_threshold']['fp']}/{threshold['oof_metrics_at_selected_threshold']['fn']}/{threshold['oof_metrics_at_selected_threshold']['tp']}.

These threshold metrics use the same OOF labels used to choose the threshold and are therefore an operating-point estimate, not an unbiased performance estimate. Full PR curve is saved in `selected_precision_recall_curve.csv`. No accuracy-only objective was used.

## Interpretation and Limits

"""
    selected_train_pr = float(selected_stats["train_pr_auc"])
    selected_validation_pr = float(selected_stats["validation_pr_auc"])
    if selected_train_pr - selected_validation_pr > 0.10:
        fit_note = "A noticeable training-to-validation PR-AUC gap suggests overfitting remains; assess fold-specific gaps and uncertainty before deployment."
    elif selected_train_pr - selected_validation_pr < 0.02:
        fit_note = "The selected model has a small train-validation PR-AUC gap; this alone does not rule out underfitting."
    else:
        fit_note = "There is a moderate train-validation PR-AUC gap; fold variation and rare labels remain important uncertainty sources."
    report += f"{fit_note}\n\n"
    ensemble_gaps = [
        float(row["validation_train_pr_auc_gap"])
        for row in aggregate_rows
        if row["model"] in {"random_forest", "extra_trees"}
    ]
    if ensemble_gaps and max(ensemble_gaps) > 0.15:
        report += (
            "The tree ensembles show substantially larger training than validation PR-AUC "
            f"gaps ({min(ensemble_gaps):.3f} to {max(ensemble_gaps):.3f}), consistent with overfitting despite the conservative limits. "
        )
    shallow_rows = [row for row in aggregate_rows if row["model"] == "shallow_regularized_tree"]
    if shallow_rows and max(float(row["train_pr_auc"]) for row in shallow_rows) < 0.12:
        report += "The depth-3 tree has low training and validation PR-AUC relative to the selected Logistic Regression, consistent with limited fit/possible underfitting. "
    report += "\n\n"
    report += """Unlabelled cells are not confirmed negatives. The label reflects mapped historical flood polygons only; performance is sensitive to incomplete location reporting and fold geography. Static drainage/hydrology proxies are not spatially mapped SWMM output and this experiment does not measure SWMM feature value. Probabilities are not calibrated. No model is claimed to forecast future events or generalize to unseen storms.

The earlier fold-4 result has already been inspected outside this experiment. Do not treat it as an untouched final test. Any future independent final evaluation requires a new untouched spatial holdout or suitable nested spatial evaluation.

Reproduce with `python .venv/Scripts/python.exe scripts/tune_static_flood_models.py`. Artifacts: `fold_metrics.csv`, `development_oof_predictions.csv.gz`, `selected_precision_recall_curve.csv`, `selected_configuration.json`, `feature_lists.json`, and `dataset_version.json`.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    frame, assignments, dataset_hash, assignment_hash = _read_development_inputs()
    fold_metrics, predictions = _evaluate(frame, assignments)
    selected = _select_configuration(fold_metrics)
    threshold, curve = _select_threshold(selected, predictions)
    _write_outputs(frame, fold_metrics, predictions, selected, threshold, curve, dataset_hash, assignment_hash)
    if _sha256(ASSIGNMENTS_PATH) != assignment_hash:
        raise RuntimeError("Saved fold assignments changed during the experiment")
    print(f"Experiment directory: {EXPERIMENT_DIR}")
    print(f"Development rows: {len(frame)}; folds: {DEVELOPMENT_FOLDS}; fold 4 used: False")
    print(f"Selected: {selected['config_id']} / {selected['feature_set']}; macro PR-AUC={float(selected['development_macro_pr_auc']):.4f}")
    print(f"Operating threshold: {threshold['threshold']:.6f}; objective=F2")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
