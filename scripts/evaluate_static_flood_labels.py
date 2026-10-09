"""Leakage-aware evaluation for the existing static BMC flood labels.

Run from the repository root:
    python scripts/evaluate_static_flood_labels.py

The final spatial fold is reserved before development-fold comparisons. No
model is selected on final-test performance. No source data is modified.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import importlib.util
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import shape
from shapely.strtree import STRtree


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "ml_ready" / "ml_master_spatial_features.csv"
GRID_GEOJSON = ROOT / "data" / "processed" / "flood_grid_100m.geojson"
FLOOD_POLYGONS = ROOT / "data" / "derived" / "bmc_flood_labels_clean_utm43.geojson"
OUTPUT_DIR = ROOT / "reports" / "ml_static_flood_evaluation"
ASSIGNMENTS_PATH = OUTPUT_DIR / "spatial_fold_assignments.csv"
METRICS_PATH = OUTPUT_DIR / "fold_metrics.csv"
FINAL_TEST_METRICS_PATH = OUTPUT_DIR / "final_test_metrics.csv"
DEVELOPMENT_PREDICTIONS_PATH = OUTPUT_DIR / "development_predictions.csv.gz"
FINAL_TEST_PREDICTIONS_PATH = OUTPUT_DIR / "final_test_predictions.csv.gz"
FEATURES_PATH = OUTPUT_DIR / "feature_lists.json"
VERSION_PATH = OUTPUT_DIR / "dataset_version.json"
REPORT_PATH = OUTPUT_DIR / "leakage_limitations.md"

SEED = 20261009
BUFFER_METERS = 500.0
FINAL_TEST_FOLD = 4
DEVELOPMENT_FOLDS = (0, 1, 2, 3)
TARGET = "flood_label"
CATEGORICAL_FEATURES = ("soil_class",)

GEOGRAPHIC_FEATURES = [
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
PHYSICS_PROXY_FEATURES = [
    "flow_accumulation",
    "flow_accumulation_area_km2",
    "flow_accumulation_log",
    "drain_density",
    "distance_to_drain",
    "clay_percent",
    "sand_percent",
    "silt_percent",
    "soil_class",
    "infiltration_proxy",
    "topographic_wetness_index",
    "drain_capacity_proxy_m2",
    "drainage_stress_index",
]
FEATURE_SETS = {
    "static_geographic": GEOGRAPHIC_FEATURES,
    "static_geographic_plus_physics_proxies": GEOGRAPHIC_FEATURES + PHYSICS_PROXY_FEATURES,
}
EXCLUDED_COLUMNS = [
    "grid_id: spatial identifier; never a predictor",
    "ward: administrative/location identifier; prohibited as predictor",
    "spatial_cv_fold: split assignment; prohibited as predictor",
    "flood_label: target",
    "flood_fraction: direct label-construction proxy (thresholded at 0.05)",
    "historical_flood_label: duplicate target in scenario dataset; dataset not used",
    "rainfall_* / tide_* / warning_* / scenario_*: event/scenario fields not aligned to the static label",
    "scs_runoff_*: event-driven proxy from the separate scenario/validation dataset; not used",
    "distances/counts of known flood locations and flood polygon identifiers: not present as inputs and prohibited",
    "synthetic SWMM outputs: not present as spatially joined ML features and not ground truth",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), list(reader)


class _UnionFind:
    def __init__(self, size: int):
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[max(a, b)] = min(a, b)


def _spatial_assignments(rows: list[dict[str, str]]) -> tuple[list[dict], dict]:
    geojson = json.loads(GRID_GEOJSON.read_text(encoding="utf-8"))
    polygon_doc = json.loads(FLOOD_POLYGONS.read_text(encoding="utf-8"))
    grid_features = geojson.get("features", [])
    polygon_features = polygon_doc.get("features", [])
    if not grid_features or not polygon_features:
        raise ValueError("Grid or source flood-polygon GeoJSON has no features")

    ml_by_id = {int(row["grid_id"]): row for row in rows}
    cells = {}
    for feature in grid_features:
        properties = feature["properties"]
        grid_id = int(properties["grid_id"])
        if grid_id not in ml_by_id:
            raise ValueError(f"Grid geometry {grid_id} is missing from the ML dataset")
        if int(properties["flood_label"]) != int(ml_by_id[grid_id][TARGET]):
            raise ValueError(f"Flood target differs between CSV and grid GeoJSON at grid_id={grid_id}")
        geometry = shape(feature["geometry"])
        center = geometry.centroid
        cells[grid_id] = {
            "x": center.x,
            "y": center.y,
            "geometry": geometry,
            "target": int(ml_by_id[grid_id][TARGET]),
            "original_fold": int(ml_by_id[grid_id]["spatial_cv_fold"]),
        }
    if len(cells) != len(rows):
        raise ValueError(f"ML rows/grid geometries differ: {len(rows)} vs {len(cells)}")

    polygons = [shape(feature["geometry"]) for feature in polygon_features]
    polygon_tree = STRtree(polygons)
    union_find = _UnionFind(len(polygons))
    cell_polygon_ids: dict[int, list[int]] = {}
    for grid_id, cell in cells.items():
        if cell["target"] != 1:
            continue
        geometry = cell["geometry"]
        related = [
            int(index)
            for index in polygon_tree.query(geometry)
            if geometry.intersection(polygons[int(index)]).area > geometry.area * 0.05
        ]
        cell_polygon_ids[grid_id] = related
        for polygon_id in related[1:]:
            union_find.union(related[0], polygon_id)

    component_cells: dict[int, list[int]] = defaultdict(list)
    component_polygons: dict[int, set[int]] = defaultdict(set)
    for grid_id, related in cell_polygon_ids.items():
        if not related:
            continue
        root = union_find.find(related[0])
        component_cells[root].append(grid_id)
        component_polygons[root].update(union_find.find(polygon_id) for polygon_id in related)

    final_fold = {grid_id: cell["original_fold"] for grid_id, cell in cells.items()}
    polygon_group: dict[int, int] = {}
    polygon_reassigned_cells = 0
    for root, component_ids in component_cells.items():
        fold_counts = Counter(cells[grid_id]["original_fold"] for grid_id in component_ids)
        assigned_fold = min(fold for fold, count in fold_counts.items() if count == max(fold_counts.values()))
        for grid_id in component_ids:
            polygon_group[grid_id] = root
            final_fold[grid_id] = assigned_fold
            polygon_reassigned_cells += int(cells[grid_id]["original_fold"] != assigned_fold)

    coordinates = np.asarray(
        [[cells[int(row["grid_id"])]["x"], cells[int(row["grid_id"])]["y"]] for row in rows]
    )
    grid_ids = [int(row["grid_id"]) for row in rows]
    fold_values = np.asarray([final_fold[grid_id] for grid_id in grid_ids], dtype=int)
    buffer_exclusions: dict[int, set[int]] = {}
    for heldout_fold in range(5):
        heldout_points = coordinates[fold_values == heldout_fold]
        if not len(heldout_points):
            raise ValueError(f"Spatial fold {heldout_fold} is empty after flood-polygon grouping")
        tree = cKDTree(heldout_points)
        candidate_folds = DEVELOPMENT_FOLDS
        candidate_indices = np.flatnonzero(
            np.isin(fold_values, candidate_folds)
            & (fold_values != heldout_fold if heldout_fold in DEVELOPMENT_FOLDS else True)
        )
        distances, _ = tree.query(coordinates[candidate_indices], k=1)
        buffer_exclusions[heldout_fold] = {
            grid_ids[index]
            for index, distance in zip(candidate_indices, distances)
            if distance <= BUFFER_METERS
        }

    assignment_rows = []
    for grid_id in grid_ids:
        assignment = {
            "grid_id": grid_id,
            "spatial_fold": final_fold[grid_id],
            "final_test": int(final_fold[grid_id] == FINAL_TEST_FOLD),
            "flood_polygon_group": polygon_group.get(grid_id, ""),
        }
        for fold in range(5):
            assignment[f"buffer_excluded_for_fold_{fold}"] = int(grid_id in buffer_exclusions[fold])
        assignment_rows.append(assignment)

    counts = {}
    for fold in range(5):
        fold_rows = [row for row in rows if final_fold[int(row["grid_id"])] == fold]
        counts[str(fold)] = {
            "rows": len(fold_rows),
            "positive": sum(int(row[TARGET]) for row in fold_rows),
            "negative": len(fold_rows) - sum(int(row[TARGET]) for row in fold_rows),
            "buffer_excluded_training_cells": len(buffer_exclusions[fold]),
        }
    polygon_summary = {
        "source_polygon_count": len(polygons),
        "polygon_components_with_positive_cells": len(component_cells),
        "positive_cells_without_polygon_association": sum(not value for value in cell_polygon_ids.values()),
        "positive_cells_reassigned_to_keep_polygon_groups_together": polygon_reassigned_cells,
    }
    return assignment_rows, {
        "fold_counts": counts,
        "polygon_grouping": polygon_summary,
        "coordinates_crs": geojson.get("crs", {}).get("properties", {}).get("name", "EPSG:32643 per grid-generation source"),
        "buffer_exclusions": buffer_exclusions,
        "final_folds": final_fold,
        "coordinates_by_id": {grid_id: (cells[grid_id]["x"], cells[grid_id]["y"]) for grid_id in grid_ids},
    }


def _load_saved_assignments(rows: list[dict[str, str]]) -> tuple[list[dict], dict]:
    if not ASSIGNMENTS_PATH.is_file():
        raise FileNotFoundError(f"Saved spatial folds are required: {ASSIGNMENTS_PATH}")
    _, assignments = _read_rows(ASSIGNMENTS_PATH)
    dataset_ids = {int(row["grid_id"]) for row in rows}
    assignment_ids = [int(row["grid_id"]) for row in assignments]
    if len(assignment_ids) != len(set(assignment_ids)) or set(assignment_ids) != dataset_ids:
        raise ValueError("Saved fold assignments do not exactly match ML dataset grid IDs")
    required_flags = {f"buffer_excluded_for_fold_{fold}" for fold in range(5)}
    if any(not required_flags.issubset(row) for row in assignments):
        raise ValueError("Saved assignments lack one or more 500 m buffer flags")

    assignment_by_id = {int(row["grid_id"]): row for row in assignments}
    dataset_by_id = {int(row["grid_id"]): row for row in rows}
    for assignment in assignments:
        assignment["grid_id"] = int(assignment["grid_id"])
        assignment["spatial_fold"] = int(assignment["spatial_fold"])
        assignment["final_test"] = int(assignment["final_test"])
        for fold in range(5):
            assignment[f"buffer_excluded_for_fold_{fold}"] = int(
                assignment[f"buffer_excluded_for_fold_{fold}"]
            )
        if assignment["final_test"] != int(assignment["spatial_fold"] == FINAL_TEST_FOLD):
            raise ValueError("Saved final-test marker does not match the fixed fold assignment")

    if {row["spatial_fold"] for row in assignments} != set(range(5)):
        raise ValueError("Saved fold assignments do not contain exactly folds 0 through 4")
    groups: dict[str, set[int]] = defaultdict(set)
    for assignment in assignments:
        group = assignment["flood_polygon_group"]
        if group:
            groups[str(group)].add(assignment["spatial_fold"])
    if any(len(folds) != 1 for folds in groups.values()):
        raise ValueError("A saved flood-polygon group spans more than one fold")

    buffer_exclusions = {
        fold: {
            assignment["grid_id"]
            for assignment in assignments
            if assignment[f"buffer_excluded_for_fold_{fold}"]
        }
        for fold in range(5)
    }
    fold_counts = {}
    for fold in range(5):
        fold_rows = [row for row in assignments if row["spatial_fold"] == fold]
        fold_cells_available_for_training = DEVELOPMENT_FOLDS
        eligible_source_folds = [
            source_fold
            for source_fold in fold_cells_available_for_training
            if source_fold != fold
        ]
        excluded_count = sum(
            assignment["spatial_fold"] in eligible_source_folds
            and assignment[f"buffer_excluded_for_fold_{fold}"]
            for assignment in assignments
        )
        positives = sum(int(dataset_by_id[row["grid_id"]][TARGET]) for row in fold_rows)
        fold_counts[str(fold)] = {
            "rows": len(fold_rows),
            "positive": positives,
            "negative": len(fold_rows) - positives,
            "buffer_excluded_training_cells": excluded_count,
        }

    positive_ids = [grid_id for grid_id, row in dataset_by_id.items() if int(row[TARGET]) == 1]
    positive_without_group = sum(not assignment_by_id[grid_id]["flood_polygon_group"] for grid_id in positive_ids)
    reassigned_positive = sum(
        int(assignment_by_id[grid_id]["spatial_fold"] != int(dataset_by_id[grid_id]["spatial_cv_fold"]))
        for grid_id in positive_ids
    )
    grid_doc = json.loads(GRID_GEOJSON.read_text(encoding="utf-8"))
    polygon_doc = json.loads(FLOOD_POLYGONS.read_text(encoding="utf-8"))
    spatial = {
        "fold_counts": fold_counts,
        "polygon_grouping": {
            "source_polygon_count": len(polygon_doc.get("features", [])),
            "polygon_components_with_positive_cells": len(groups),
            "positive_cells_without_polygon_association": positive_without_group,
            "positive_cells_reassigned_to_keep_polygon_groups_together": reassigned_positive,
        },
        "coordinates_crs": grid_doc.get("crs", {}).get("properties", {}).get(
            "name", "EPSG:32643 per grid-generation source"
        ),
        "buffer_exclusions": buffer_exclusions,
    }
    return assignments, spatial


def _write_json(path: Path, content: dict) -> None:
    path.write_text(json.dumps(content, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _write_feature_lists(columns: list[str]) -> dict:
    feature_lists = {
        name: [column for column in requested if column in columns]
        for name, requested in FEATURE_SETS.items()
    }
    used = set().union(*map(set, feature_lists.values()))
    missing = {name: sorted(set(requested) - set(columns)) for name, requested in FEATURE_SETS.items()}
    present_exclusions = [
        item.split(":", 1)[0]
        for item in EXCLUDED_COLUMNS
        if item.split(":", 1)[0] in columns
    ]
    result = {
        "target": TARGET,
        "feature_sets": feature_lists,
        "feature_set_missing_columns": missing,
        "excluded_columns_and_reasons": EXCLUDED_COLUMNS,
        "excluded_columns_present_in_dataset": present_exclusions,
        "columns_used_as_predictors": sorted(used),
        "no_ward_or_label_derived_predictors": not bool(
            used.intersection({"ward", "flood_label", "flood_fraction", "spatial_cv_fold"})
        ),
        "swmm_spatial_features_available": False,
        "physics_ablation_note": "Existing non-event static drainage/hydrology proxies are compared; no spatially joined SWMM outputs are present, so this cannot measure incremental SWMM-output value.",
    }
    _write_json(FEATURES_PATH, result)
    return result


def _metric_row(split: str, fold: str, feature_set: str, model_name: str) -> dict:
    return {
        "split": split,
        "fold": fold,
        "feature_set": feature_set,
        "model": model_name,
        "status": "not_run",
        "pr_auc": "",
        "roc_auc": "",
        "precision": "",
        "recall": "",
        "tn": "",
        "fp": "",
        "fn": "",
        "tp": "",
        "train_rows": "",
        "validation_rows": "",
        "buffer_excluded_rows": "",
        "notes": "",
    }


def _write_blocked_metrics(reason: str) -> None:
    rows = [_metric_row("blocked", "all", "all", "not_run")]
    rows[0]["status"] = "blocked_missing_dependency"
    rows[0]["notes"] = reason
    with METRICS_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _evaluate(rows: list[dict[str, str]], assignments: list[dict], spatial: dict) -> dict:
    import pandas as pd
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, confusion_matrix, precision_score, recall_score, roc_auc_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.tree import DecisionTreeClassifier

    frame = pd.DataFrame(rows)
    assignment_by_id = {int(row["grid_id"]): row for row in assignments}
    frame["spatial_fold"] = frame["grid_id"].astype(int).map(lambda grid_id: int(assignment_by_id[grid_id]["spatial_fold"]))
    for column in set(GEOGRAPHIC_FEATURES + PHYSICS_PROXY_FEATURES) - set(CATEGORICAL_FEATURES):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    y = frame[TARGET].astype(int).to_numpy()
    development_rows = []
    development_predictions = []
    final_predictions = []
    model_factories = {
        "logistic_regression": lambda: LogisticRegression(
            C=1.0, max_iter=2000, class_weight="balanced", random_state=SEED
        ),
        "shallow_regularized_tree": lambda: DecisionTreeClassifier(
            max_depth=3, min_samples_leaf=50, ccp_alpha=0.001,
            class_weight="balanced", random_state=SEED,
        ),
    }

    def score(
        split: str,
        fold: str,
        feature_set: str,
        model_name: str,
        train_ids,
        validation_ids,
        excluded_count,
        prediction_records: list[dict],
    ) -> dict:
        train_mask = frame["grid_id"].astype(int).isin(train_ids).to_numpy()
        validation_mask = frame["grid_id"].astype(int).isin(validation_ids).to_numpy()
        y_train, y_validation = y[train_mask], y[validation_mask]
        row = _metric_row(split, fold, feature_set, model_name)
        row.update({
            "train_rows": int(train_mask.sum()),
            "validation_rows": int(validation_mask.sum()),
            "buffer_excluded_rows": excluded_count,
        })
        if len(set(y_train)) < 2 or len(set(y_validation)) < 2:
            row["status"] = "blocked_single_class_partition"
            row["notes"] = "Both classes are required in train and held-out partitions."
            return row
        if model_name == "prevalence_baseline":
            prevalence = float(y_train.mean())
            probabilities = np.full(int(validation_mask.sum()), prevalence)
            predictions = np.zeros(len(probabilities), dtype=int)
        else:
            feature_columns = FEATURE_SETS[feature_set]
            prohibited = {"grid_id", "ward", "spatial_fold", "spatial_cv_fold", "flood_label", "flood_fraction"}
            if prohibited.intersection(feature_columns):
                raise ValueError("A prohibited identifier, split, or label-derived field entered model inputs")
            numeric = [column for column in feature_columns if column not in CATEGORICAL_FEATURES]
            categorical = [column for column in feature_columns if column in CATEGORICAL_FEATURES]
            transformers = [("numeric", Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
            ]), numeric)]
            if categorical:
                transformers.append(("categorical", Pipeline([
                    ("imputer", SimpleImputer(strategy="most_frequent")),
                    ("onehot", OneHotEncoder(handle_unknown="ignore")),
                ]), categorical))
            preprocess = ColumnTransformer(transformers, remainder="drop")
            model = Pipeline([
                ("preprocess", preprocess),
                ("classifier", model_factories[model_name]()),
            ])
            model.fit(frame.loc[train_mask, feature_columns], y_train)
            probabilities = model.predict_proba(frame.loc[validation_mask, feature_columns])[:, 1]
            predictions = (probabilities >= 0.5).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_validation, predictions, labels=[0, 1]).ravel()
        probability_values = np.asarray(probabilities, dtype=float)
        prediction_values = np.asarray(predictions, dtype=int)
        validation_frame = frame.loc[validation_mask, ["grid_id"]].copy()
        for index, (_, validation_row) in enumerate(validation_frame.iterrows()):
            prediction_records.append({
                "split": split,
                "fold": fold,
                "grid_id": int(validation_row["grid_id"]),
                "model": model_name,
                "feature_set": feature_set,
                "target": int(y_validation[index]),
                "predicted_probability": float(probability_values[index]),
                "predicted_label_at_0_5": int(prediction_values[index]),
            })
        row.update({
            "status": "complete",
            "pr_auc": float(average_precision_score(y_validation, probability_values)),
            "roc_auc": float(roc_auc_score(y_validation, probability_values)),
            "precision": float(precision_score(y_validation, predictions, zero_division=0)),
            "recall": float(recall_score(y_validation, predictions, zero_division=0)),
            "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
        })
        return row

    # Development folds compare fixed model/feature-set choices; no tuning is performed.
    for fold in DEVELOPMENT_FOLDS:
        validation_ids = {
            int(row["grid_id"]) for row in assignments if int(row["spatial_fold"]) == fold
        }
        excluded = spatial["buffer_exclusions"][fold]
        train_ids = {
            int(row["grid_id"])
            for row in assignments
            if int(row["spatial_fold"]) in DEVELOPMENT_FOLDS
            and int(row["spatial_fold"]) != fold
            and int(row["grid_id"]) not in excluded
        }
        for feature_set in FEATURE_SETS:
            development_rows.append(score(
                "development_cv", str(fold), feature_set, "prevalence_baseline",
                train_ids, validation_ids, len(excluded), development_predictions,
            ))
            for model_name in model_factories:
                development_rows.append(score(
                    "development_cv", str(fold), feature_set, model_name,
                    train_ids, validation_ids, len(excluded), development_predictions,
                ))

    aggregates = []
    group_keys = list(dict.fromkeys((row["feature_set"], row["model"]) for row in development_rows))
    for feature_set, model_name in group_keys:
        fold_rows = [
            row for row in development_rows
            if row["feature_set"] == feature_set and row["model"] == model_name
        ]
        if len(fold_rows) != len(DEVELOPMENT_FOLDS) or any(row["status"] != "complete" for row in fold_rows):
            aggregate = _metric_row("development_cv_aggregate", "macro", feature_set, model_name)
            aggregate["status"] = "incomplete_development_folds"
            aggregate["notes"] = "All four development folds must complete before selection."
            aggregates.append(aggregate)
            continue
        aggregate = _metric_row("development_cv_aggregate", "macro", feature_set, model_name)
        aggregate["status"] = "complete"
        for key in ("pr_auc", "roc_auc", "precision", "recall"):
            aggregate[key] = float(np.mean([float(row[key]) for row in fold_rows]))
        for key in ("tn", "fp", "fn", "tp", "validation_rows"):
            aggregate[key] = sum(int(row[key]) for row in fold_rows)
        aggregate["notes"] = "Metric scores are macro-averaged over folds; confusion counts are summed."
        aggregates.append(aggregate)
    development_rows.extend(aggregates)

    selection_candidates = [
        row for row in aggregates
        if row["status"] == "complete" and row["model"] in model_factories
    ]
    if not selection_candidates:
        raise RuntimeError("No candidate model completed all four development folds")
    selected = max(selection_candidates, key=lambda row: float(row["pr_auc"]))

    final_test_ids = {
        int(row["grid_id"]) for row in assignments if int(row["spatial_fold"]) == FINAL_TEST_FOLD
    }
    final_excluded = spatial["buffer_exclusions"][FINAL_TEST_FOLD]
    final_train_ids = {
        int(row["grid_id"])
        for row in assignments
        if int(row["spatial_fold"]) in DEVELOPMENT_FOLDS
        and int(row["grid_id"]) not in final_excluded
    }
    final_rows = [
        score(
            "final_spatial_test", str(FINAL_TEST_FOLD), selected["feature_set"],
            "prevalence_baseline", final_train_ids, final_test_ids, len(final_excluded),
            final_predictions,
        ),
        score(
            "final_spatial_test", str(FINAL_TEST_FOLD), selected["feature_set"],
            selected["model"], final_train_ids, final_test_ids, len(final_excluded),
            final_predictions,
        ),
    ]
    return {
        "development_metrics": development_rows,
        "final_test_metrics": final_rows,
        "selected_approach": {
            "feature_set": selected["feature_set"],
            "model": selected["model"],
            "development_macro_pr_auc": selected["pr_auc"],
            "selection_rule": "Highest macro-average PR-AUC across development folds 0-3; no fold-4 metric accessed during selection.",
        },
        "development_predictions": development_predictions,
        "final_test_predictions": final_predictions,
    }


def _write_predictions(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"No prediction rows to save: {path}")
    with gzip.open(path, "wt", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_report(dataset_info: dict, spatial: dict, features: dict, evaluation: dict) -> None:
    folds = spatial["fold_counts"]
    fold_table = [
        "| Fold | Rows | Positive | Negative | Training cells excluded by 500 m buffer |",
        "|---:|---:|---:|---:|---:|",
    ]
    for fold, counts in folds.items():
        fold_table.append(
            f"| {fold}{' (final test)' if int(fold) == FINAL_TEST_FOLD else ''} | {counts['rows']} | {counts['positive']} | {counts['negative']} | {counts['buffer_excluded_training_cells']} |"
        )
    development_aggregates = [
        row for row in evaluation["development_metrics"]
        if row["fold"] == "macro" and row["status"] == "complete"
    ]
    development_table = [
        "| Feature set | Model | Macro PR-AUC | Macro ROC-AUC | Macro precision | Macro recall | Summed TN / FP / FN / TP |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for row in development_aggregates:
        development_table.append(
            f"| {row['feature_set']} | {row['model']} | {float(row['pr_auc']):.4f} | {float(row['roc_auc']):.4f} | {float(row['precision']):.4f} | {float(row['recall']):.4f} | {row['tn']} / {row['fp']} / {row['fn']} / {row['tp']} |"
        )
    final_table = [
        "| Model | Feature set | PR-AUC | ROC-AUC | Precision | Recall | TN / FP / FN / TP |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for row in evaluation["final_test_metrics"]:
        final_table.append(
            f"| {row['model']} | {row['feature_set']} | {float(row['pr_auc']):.4f} | {float(row['roc_auc']):.4f} | {float(row['precision']):.4f} | {float(row['recall']):.4f} | {row['tn']} / {row['fp']} / {row['fn']} / {row['tp']} |"
        )
    selected = evaluation["selected_approach"]
    report = f"""# Static Flood-Label ML Evaluation

## Dataset and Target

Dataset: `data/ml_ready/ml_master_spatial_features.csv` ({dataset_info['rows']:,} cells, {dataset_info['columns']} columns; SHA-256 `{dataset_info['sha256']}`). Target: `flood_label`. The source grid creates this target from historical BMC flood polygons using `flood_fraction > 0.05`; it is a static spatial occurrence/susceptibility label, not an event-specific flood forecast target. The label-building rule is in `scripts/build_flood_grid.py` under “HISTORICAL FLOOD LABEL”. Unlabelled cells are not confirmed non-flood observations.

The 2005 validation and warning-scenario tables duplicate the static label alongside event/scenario inputs. They were not used. No spatially mapped SWMM result features are present; the “physics proxy” comparison below uses only existing static flow-accumulation, drainage, soil, infiltration, wetness, capacity/stress features. It cannot establish incremental value from SWMM outputs.

## Leakage Controls

- Preassigned five regional/ward-group folds are used, with fold {FINAL_TEST_FOLD} reserved as the final spatial test before evaluation. Folds {', '.join(map(str, DEVELOPMENT_FOLDS))} provide four development validation runs; model settings are fixed and no hyperparameter search or feature selection is performed.
- Flood grid polygons and the 332 local flood-label polygons are intersected. Cells associated with the same connected source-polygon component are assigned to one fold ({spatial['polygon_grouping']['polygon_components_with_positive_cells']} components with positive cells); {spatial['polygon_grouping']['positive_cells_reassigned_to_keep_polygon_groups_together']} positive cells were reassigned to keep groups together. {spatial['polygon_grouping']['positive_cells_without_polygon_association']} positive cells lacked a source-polygon association and retain their preassigned fold.
- For each held-out fold, candidate training cells within {BUFFER_METERS:g} m of any held-out cell centroid are excluded. Grid geometry is in {spatial['coordinates_crs']}; fold and per-fold buffer flags are saved in `spatial_fold_assignments.csv`.
- `ward`, `grid_id`, split fields, `flood_fraction`, duplicated labels, event/rainfall/tide/scenario fields, and label-location-derived proxies are excluded. Exact feature lists and exclusion rationale are in `feature_lists.json`.
- Numeric imputation, scaling, and categorical imputation/one-hot encoding are inside each training-fold pipeline. The final spatial test is not used in fitting, preprocessing, or development comparisons.
- No synthetic SWMM output is treated as ground truth. The available feature files contain no spatially joined SWMM outputs, so physics-proxy ablation is not a SWMM-feature experiment.

## Evaluation Design and Results

Seed: `{SEED}`. Simple prevalence baseline, class-weighted Logistic Regression, and a regularized depth-3 decision tree were evaluated. Numeric imputation/scaling and categorical imputation/encoding were fit inside each training fold. Primary metric is average precision (reported as PR-AUC); ROC-AUC, precision, recall, and confusion counts are supporting measures. No hyperparameter tuning was performed.

| Fold | Rows | Positive | Negative | Training cells excluded by 500 m buffer |
|---:|---:|---:|---:|---:|
{chr(10).join(fold_table[2:])}

### Development folds 0–3 (macro mean, confusion counts summed)

{chr(10).join(development_table)}

Approach selected only from development folds by highest macro PR-AUC: **{selected['model']}** with **{selected['feature_set']}** (macro PR-AUC {float(selected['development_macro_pr_auc']):.4f}). The prevalence baseline is a benchmark, not a tuning target.

### Reserved final spatial test fold 4 (evaluated once)

{chr(10).join(final_table)}

Fold 4 was excluded from model/feature selection and preprocessing. Only the selected development approach and its prevalence-baseline comparator were evaluated on fold 4. Full per-fold/aggregate metrics, final-test metrics, and reproducible prediction files are saved separately.

## Limitations

- Flood labels are mapped polygon observations. Negative labels mean “not covered by the mapped polygons under the 5% rule,” not verified no-flood outcomes; class imbalance and incomplete reporting can bias metrics.
- The local dataset has no event-linked flood outcomes and no spatial SWMM outputs. Results cannot validate forecasting, unseen-storm performance, hydraulic validity, or model calibration.
- The static + physics-proxy comparison uses available drainage/hydrology-derived spatial predictors, not mapped SWMM node/link outputs; it does not test the incremental value of spatially mapped SWMM results.
- Existing folds aggregate administrative wards into five regions; the 500 m buffer reduces adjacent-cell leakage but does not remove all spatial dependence. Polygon IDs were reconstructed from local geometries; {spatial['polygon_grouping']['positive_cells_without_polygon_association']} positive cells could not be linked.
- Only one held-out region is reserved as final test; performance uncertainty/generalization across alternative regions or storms remains unmeasured.
- No model score should be interpreted when a row is marked blocked or when either held-out class is absent.

Predicted scores are ranking outputs, **not calibrated flood probabilities**. The target is historical mapped-flood susceptibility, not future-event forecasting.

Reproduce with `python scripts/evaluate_static_flood_labels.py` using the repository `.venv`. Dataset hashes, row counts, feature lists, seed, selected approach, and fold settings are in `dataset_version.json`; saved fold assignments are reused without modification. `fold_metrics.csv` contains per-fold and aggregate development scores; `final_test_metrics.csv` contains only the selected approach and prevalence baseline for fold 4. Predictions are in compressed CSV files.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    columns, rows = _read_rows(DATASET)
    if TARGET not in columns or "spatial_cv_fold" not in columns or "ward" not in columns:
        raise SystemExit("Required target or preassigned spatial-fold columns are missing")
    if any(column not in columns for column in GEOGRAPHIC_FEATURES + PHYSICS_PROXY_FEATURES):
        raise SystemExit("One or more prespecified geographic/physics features are absent")
    if importlib.util.find_spec("sklearn") is None:
        raise SystemExit("scikit-learn is required; install from scripts/requirements.txt in the project .venv")

    assignment_hash_before = _sha256(ASSIGNMENTS_PATH)
    assignments, spatial = _load_saved_assignments(rows)

    features = _write_feature_lists(columns)
    dataset_info = {
        "dataset": str(DATASET.relative_to(ROOT)),
        "sha256": _sha256(DATASET),
        "rows": len(rows),
        "columns": len(columns),
        "target": TARGET,
        "positive_count": sum(int(row[TARGET]) for row in rows),
        "positive_rate": sum(int(row[TARGET]) for row in rows) / len(rows),
        "grid_geojson_sha256": _sha256(GRID_GEOJSON),
        "source_flood_polygons_sha256": _sha256(FLOOD_POLYGONS),
        "seed": SEED,
        "buffer_meters": BUFFER_METERS,
        "final_test_fold": FINAL_TEST_FOLD,
        "development_folds": list(DEVELOPMENT_FOLDS),
        "sklearn_available": True,
        "feature_sets": features["feature_sets"],
        "fold_counts": spatial["fold_counts"],
        "polygon_grouping": spatial["polygon_grouping"],
        "spatial_assignment_sha256": assignment_hash_before,
    }
    import sklearn
    dataset_info["sklearn_version"] = sklearn.__version__

    evaluation = _evaluate(rows, assignments, spatial)
    with METRICS_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(evaluation["development_metrics"][0]))
        writer.writeheader()
        writer.writerows(evaluation["development_metrics"])
    with FINAL_TEST_METRICS_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(evaluation["final_test_metrics"][0]))
        writer.writeheader()
        writer.writerows(evaluation["final_test_metrics"])
    _write_predictions(DEVELOPMENT_PREDICTIONS_PATH, evaluation["development_predictions"])
    _write_predictions(FINAL_TEST_PREDICTIONS_PATH, evaluation["final_test_predictions"])
    if _sha256(ASSIGNMENTS_PATH) != assignment_hash_before:
        raise RuntimeError("Saved spatial fold assignments were modified during evaluation")
    dataset_info["selected_approach"] = evaluation["selected_approach"]
    _write_json(VERSION_PATH, dataset_info)

    _write_report(dataset_info, spatial, features, evaluation)
    print(f"Fold assignments: {ASSIGNMENTS_PATH}")
    print(f"Metrics: {METRICS_PATH}")
    print(f"Leakage report: {REPORT_PATH}")
    print(f"Dataset: {len(rows)} rows; positives={dataset_info['positive_count']}; rate={dataset_info['positive_rate']:.4%}")
    print(f"Final test fold {FINAL_TEST_FOLD}: {spatial['fold_counts'][str(FINAL_TEST_FOLD)]}")
    print(f"Selected by development folds only: {evaluation['selected_approach']}")
    print(f"Final-test metrics: {FINAL_TEST_METRICS_PATH}")
    print(f"Development predictions: {DEVELOPMENT_PREDICTIONS_PATH}")
    print(f"Final-test predictions: {FINAL_TEST_PREDICTIONS_PATH}")
    print(f"Completed development metric rows: {len(evaluation['development_metrics'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())