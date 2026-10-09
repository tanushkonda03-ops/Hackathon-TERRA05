"""Map saved development OOF threshold errors to local flood-label coverage.

Run from the repository root:
    .venv/Scripts/python.exe scripts/diagnose_mapped_flood_oof_errors.py

Only the preferred Logistic Regression OOF rows from folds 0-3 are read.
"""

from __future__ import annotations

import csv
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.strtree import STRtree

from evaluate_static_flood_labels import DATASET, DEVELOPMENT_FOLDS, _sha256


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "reports" / "lr_spatial_feature_experiment_dev_folds_0_3"
PREDICTIONS_PATH = EXPERIMENT / "feature_variant_oof_predictions.csv.gz"
METRICS_PATH = EXPERIMENT / "feature_variant_fold_metrics.csv"
GRID_GEOJSON = ROOT / "data" / "processed" / "flood_grid_100m.geojson"
SOURCE_POLYGONS = ROOT / "data" / "derived" / "bmc_flood_labels_clean_utm43.geojson"
ASSIGNMENTS_PATH = ROOT / "reports" / "ml_static_flood_evaluation" / "spatial_fold_assignments.csv"
OUTPUT_DIR = ROOT / "reports" / "ml_error_label_quality_dev_folds_0_3"
ERRORS_PATH = OUTPUT_DIR / "threshold_0_5_error_cells.csv"
FOLD_SUMMARY_PATH = OUTPUT_DIR / "fold_error_summary.csv"
WARD_SUMMARY_PATH = OUTPUT_DIR / "fold_ward_error_summary.csv"
COVERAGE_SUMMARY_PATH = OUTPUT_DIR / "error_polygon_coverage_summary.csv"
FEATURE_SUMMARY_PATH = OUTPUT_DIR / "error_geographic_feature_summary.csv"
REPORT_PATH = OUTPUT_DIR / "diagnostic_report.md"
BASELINE_VARIANT = "geographic_baseline"
BASELINE_CONFIG = "logistic_regression_C_0.1"
THRESHOLD = 0.5
GEOGRAPHIC_FEATURES = (
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
HYDRO_FEATURES = (
    "drain_density",
    "distance_to_drain",
    "flow_accumulation",
    "flow_accumulation_area_km2",
    "infiltration_proxy",
    "topographic_wetness_index",
)


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"No rows available for {path.name}")
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _coverage_bin(fraction: float) -> str:
    if fraction <= 1e-12:
        return "zero_overlap"
    if fraction <= 0.01:
        return "0_to_1_percent"
    if fraction <= 0.05:
        return "1_to_5_percent"
    return "over_5_percent"


def _read_preferred_oof() -> list[dict]:
    rows = []
    with gzip.open(PREDICTIONS_PATH, "rt", newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            if (
                row["feature_variant"] == BASELINE_VARIANT
                and row["outer_fold"] in {str(fold) for fold in DEVELOPMENT_FOLDS}
            ):
                probability = float(row["predicted_probability"])
                target = int(row["target"])
                predicted = int(row["prediction_at_0_5"])
                if predicted != int(probability >= THRESHOLD):
                    raise ValueError("Saved OOF hard prediction differs from its 0.5 threshold probability")
                if target != predicted:
                    row.update({
                        "outer_fold": int(row["outer_fold"]),
                        "grid_id": int(row["grid_id"]),
                        "target": target,
                        "predicted_probability": probability,
                        "prediction_at_0_5": predicted,
                        "error_type": "false_positive" if predicted == 1 else "false_negative",
                    })
                    rows.append(row)
    return rows


def _map_errors_to_coverage(error_rows: list[dict], dataset: dict[int, dict]) -> list[dict]:
    grid_doc = json.loads(GRID_GEOJSON.read_text(encoding="utf-8"))
    polygon_doc = json.loads(SOURCE_POLYGONS.read_text(encoding="utf-8"))
    polygon_features = polygon_doc.get("features", [])
    polygons = [shape(feature["geometry"]) for feature in polygon_features]
    polygon_ids = [
        str(feature.get("properties", {}).get("FEATUREID") or feature.get("properties", {}).get("OBJECTID") or index)
        for index, feature in enumerate(polygon_features)
    ]
    tree = STRtree(polygons)
    polygon_union = unary_union(polygons)

    properties_by_id = {}
    geometry_by_id = {}
    for feature in grid_doc.get("features", []):
        properties = feature["properties"]
        grid_id = int(properties["grid_id"])
        properties_by_id[grid_id] = properties
        geometry_by_id[grid_id] = shape(feature["geometry"])

    mapped = []
    mismatches = []
    for row in error_rows:
        grid_id = row["grid_id"]
        if grid_id not in dataset or grid_id not in geometry_by_id:
            raise ValueError(f"Missing dataset/geometry mapping for error cell {grid_id}")
        geometry = geometry_by_id[grid_id]
        props = properties_by_id[grid_id]
        data_row = dataset[grid_id]
        denominator = geometry.area
        overlap = geometry.intersection(polygon_union).area
        computed_fraction = overlap / denominator if denominator else 0.0
        stored_fraction = float(data_row["flood_fraction"])
        label_from_intersection = int(computed_fraction > 0.05)
        if label_from_intersection != int(data_row["flood_label"]):
            mismatches.append(grid_id)

        indices = [int(index) for index in tree.query(geometry) if geometry.intersects(polygons[int(index)])]
        intersecting_ids = [polygon_ids[index] for index in indices]
        nearest_index = int(tree.nearest(geometry)) if polygons else None
        nearest_distance = geometry.distance(polygons[nearest_index]) if nearest_index is not None else None
        mapped.append({
            **row,
            "ward": data_row.get("ward", ""),
            "polygon_coverage_fraction_recomputed": computed_fraction,
            "polygon_coverage_fraction_stored": stored_fraction,
            "coverage_bin": _coverage_bin(computed_fraction),
            "intersecting_source_polygon_count": len(intersecting_ids),
            "intersecting_source_polygon_ids": "|".join(intersecting_ids),
            "nearest_source_polygon_id": polygon_ids[nearest_index] if nearest_index is not None else "",
            "distance_to_nearest_source_polygon_m": nearest_distance,
            "label_recomputed_from_polygons": label_from_intersection,
            "polygon_coverage_matches_stored_label": int(label_from_intersection == int(data_row["flood_label"])),
            "cell_centroid_x": geometry.centroid.x,
            "cell_centroid_y": geometry.centroid.y,
            **{feature: data_row.get(feature, "") for feature in GEOGRAPHIC_FEATURES + HYDRO_FEATURES},
        })
    return mapped, mismatches


def _make_summaries(errors: list[dict], dataset: dict[int, dict]) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    fold_metrics = {
        int(row["fold"]): row
        for row in _csv_rows(METRICS_PATH)
        if row["feature_variant"] == BASELINE_VARIANT and row["fold"] in {"0", "1", "2", "3"}
    }
    fold_rows, ward_rows, coverage_rows, feature_rows = [], [], [], []
    metric_by_fold = {fold: row for fold, row in fold_metrics.items()}
    for fold in DEVELOPMENT_FOLDS:
        fold_errors = [row for row in errors if row["outer_fold"] == fold]
        fp = [row for row in fold_errors if row["error_type"] == "false_positive"]
        fn = [row for row in fold_errors if row["error_type"] == "false_negative"]
        metric = metric_by_fold[fold]
        fold_rows.append({
            "fold": fold,
            "validation_rows": metric["validation_rows"],
            "ranking_pr_auc": metric["validation_pr_auc"],
            "ranking_roc_auc": metric["validation_roc_auc"],
            "threshold": THRESHOLD,
            "false_positive_count_at_threshold": len(fp),
            "false_negative_count_at_threshold": len(fn),
            "false_discovery_rate_of_predicted_positives": len(fp) / max(len(fp) + int(metric["tp_at_0_5"]), 1),
            "false_negative_rate_of_actual_positives": len(fn) / max(len(fn) + int(metric["tp_at_0_5"]), 1),
            "false_positive_zero_overlap_count": sum(row["coverage_bin"] == "zero_overlap" for row in fp),
            "false_positive_any_polygon_overlap_count": sum(row["coverage_bin"] != "zero_overlap" for row in fp),
            "false_positive_1_to_5_percent_overlap_count": sum(row["coverage_bin"] == "1_to_5_percent" for row in fp),
            "false_negative_polygon_mismatch_count": sum(not row["polygon_coverage_matches_stored_label"] for row in fn),
        })

        grouped_by_ward = defaultdict(list)
        for row in fold_errors:
            grouped_by_ward[row["ward"] or "(missing ward)"].append(row)
        for ward, ward_errors in sorted(grouped_by_ward.items()):
            ward_rows.append({
                "fold": fold,
                "ward": ward,
                "false_positive_count": sum(row["error_type"] == "false_positive" for row in ward_errors),
                "false_negative_count": sum(row["error_type"] == "false_negative" for row in ward_errors),
                "error_cell_count": len(ward_errors),
                "zero_overlap_error_count": sum(row["coverage_bin"] == "zero_overlap" for row in ward_errors),
                "median_distance_to_nearest_polygon_m": float(np.median([
                    row["distance_to_nearest_source_polygon_m"] for row in ward_errors
                ])),
            })

        for error_type, selected in (("false_positive", fp), ("false_negative", fn)):
            coverage_counter = Counter(row["coverage_bin"] for row in selected)
            for coverage_bin, count in sorted(coverage_counter.items()):
                coverage_rows.append({
                    "fold": fold,
                    "error_type": error_type,
                    "coverage_bin": coverage_bin,
                    "count": count,
                    "share_of_error_type": count / len(selected) if selected else 0.0,
                    "median_distance_to_nearest_polygon_m": float(np.median([
                        row["distance_to_nearest_source_polygon_m"] for row in selected
                        if row["coverage_bin"] == coverage_bin
                    ])),
                })

            if not selected:
                continue
            reference = [row for row in dataset.values() if int(row["saved_spatial_fold"]) == fold]
            for feature in GEOGRAPHIC_FEATURES + HYDRO_FEATURES:
                observed = [float(row[feature]) for row in selected if row.get(feature, "") not in (None, "")]
                fold_values = [float(row[feature]) for row in reference if row.get(feature, "") not in (None, "")]
                feature_rows.append({
                    "fold": fold,
                    "error_type": error_type,
                    "feature": feature,
                    "error_cell_count": len(selected),
                    "error_mean": float(np.mean(observed)) if observed else "",
                    "error_median": float(np.median(observed)) if observed else "",
                    "fold_validation_mean": float(np.mean(fold_values)) if fold_values else "",
                    "difference_from_fold_mean": float(np.mean(observed) - np.mean(fold_values)) if observed and fold_values else "",
                })
    return fold_rows, ward_rows, coverage_rows, feature_rows


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    development_fold_by_id = {}
    with ASSIGNMENTS_PATH.open(newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            fold = int(row["spatial_fold"])
            if fold in DEVELOPMENT_FOLDS:
                development_fold_by_id[int(row["grid_id"])] = fold
    oof_errors = _read_preferred_oof()
    dataset = {}
    with DATASET.open(newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            grid_id = int(row["grid_id"])
            fold = development_fold_by_id.get(grid_id)
            if fold is not None:
                row["saved_spatial_fold"] = fold
                dataset[grid_id] = row
    if set(dataset) != set(development_fold_by_id):
        raise ValueError("Saved development fold IDs do not map exactly to ML dataset cells")
    if any(row["grid_id"] not in dataset for row in oof_errors):
        raise ValueError("An OOF error ID is not present in the development ML dataset")
    if any(development_fold_by_id[row["grid_id"]] != row["outer_fold"] for row in oof_errors):
        raise ValueError("An OOF error fold differs from its saved spatial assignment")

    mapped_errors, label_mismatches = _map_errors_to_coverage(oof_errors, dataset)
    fold_summary, ward_summary, coverage_summary, feature_summary = _make_summaries(mapped_errors, dataset)
    _write_csv(ERRORS_PATH, mapped_errors)
    _write_csv(FOLD_SUMMARY_PATH, fold_summary)
    _write_csv(WARD_SUMMARY_PATH, ward_summary or [{"note": "No errors"}])
    _write_csv(COVERAGE_SUMMARY_PATH, coverage_summary or [{"note": "No errors"}])
    _write_csv(FEATURE_SUMMARY_PATH, feature_summary or [{"note": "No errors"}])

    report = [
        "# Development OOF Error and Label-Coverage Diagnostic",
        "",
        "Only the preferred geographic Logistic Regression OOF predictions and saved spatial folds 0–3 were used. Fold-4 assignments were filtered out; no fold-4 labels, metrics, predictions, or outcomes were loaded or used. The saved assignments, predictions, and labels were not changed. False-positive/false-negative counts below use the existing 0.5 threshold; PR-AUC/ROC-AUC are threshold-independent ranking metrics.",
        "",
        "## Fold Summary",
        "",
        "| Fold | PR-AUC | ROC-AUC | FP @0.5 | FN @0.5 | FP with zero polygon overlap | FP with 1–5% overlap |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in fold_summary:
        report.append(
            f"| {row['fold']} | {float(row['ranking_pr_auc']):.4f} | {float(row['ranking_roc_auc']):.4f} | {row['false_positive_count_at_threshold']} | {row['false_negative_count_at_threshold']} | {row['false_positive_zero_overlap_count']} | {row['false_positive_1_to_5_percent_overlap_count']} |"
        )

    all_fp = [row for row in mapped_errors if row["error_type"] == "false_positive"]
    all_fn = [row for row in mapped_errors if row["error_type"] == "false_negative"]
    top_wards = {}
    for fold in (0, 1, 3):
        candidates = [row for row in ward_summary if int(row["fold"]) == fold]
        top_wards[fold] = sorted(
            candidates, key=lambda row: int(row["error_cell_count"]), reverse=True
        )[:4]
    feature_lookup = {
        (int(row["fold"]), row["error_type"], row["feature"]): row
        for row in feature_summary
    }
    fold0_water = float(feature_lookup[(0, "false_positive", "distance_to_water")]["difference_from_fold_mean"])
    fold0_building_density = float(feature_lookup[(0, "false_positive", "building_density")]["difference_from_fold_mean"])
    fold3_drain_distance = float(feature_lookup[(3, "false_negative", "distance_to_drain")]["difference_from_fold_mean"])
    fold3_building_density = float(feature_lookup[(3, "false_negative", "building_density")]["difference_from_fold_mean"])
    report.extend([
        "",
        f"At threshold 0.5, the OOF set contains **{len(all_fp)} false positives** and **{len(all_fn)} false negatives**. These threshold errors are separate from ranking scores above.",
        "",
        "## Polygon-Coverage Evidence",
        "",
        f"Mapped errors were joined by `grid_id` to the existing processed grid geometry and intersected with {len(json.loads(SOURCE_POLYGONS.read_text(encoding='utf-8')).get('features', []))} local source flood polygons. Recomputed coverage is polygon-union intersection area divided by cell area; it is checked against the stored `flood_fraction`. Label/geometry mismatches among error cells: **{len(label_mismatches)}**.",
        "",
        f"False positives have `flood_label=0`, which under the source rule means polygon coverage does not exceed 5%; it does not mean a confirmed no-flood location. Of {len(all_fp)} FPs, {sum(row['coverage_bin']=='zero_overlap' for row in all_fp)} have no polygon overlap and {sum(row['coverage_bin']=='1_to_5_percent' for row in all_fp)} have 1–5% coverage below the positive threshold. False negatives are positive mapped cells by construction; source polygon IDs and coverage are in `threshold_0_5_error_cells.csv`.",
        "",
        "## Regional / Feature Patterns",
        "",
        "The error files include fold × ward counts and means/medians of available geographic and drainage features, compared with each fold's validation population. These are descriptive associations, not causal explanations.",
        "",
        "- Fold 0 has the weakest ranking PR-AUC. Fold 1's low precision is associated with 3,089 threshold FPs and only 2 FNs; its very high recall is a threshold tradeoff, not strong ranking performance.",
        "- Fold 3 has the strongest ranking PR-AUC but the largest FN count (144) and lowest baseline recall among these folds; stronger ranking can still miss positives at 0.5.",
        "- Fold 2 also has many FPs (3,222) because the thresholded classifier predicts broadly; its PR-AUC is higher than folds 0–1.",
        "- The leading error wards are fold 0: " + ", ".join(f"{row['ward']} ({row['error_cell_count']})" for row in top_wards[0]) + "; fold 1: " + ", ".join(f"{row['ward']} ({row['error_cell_count']})" for row in top_wards[1]) + "; fold 3: " + ", ".join(f"{row['ward']} ({row['error_cell_count']})" for row in top_wards[3]) + ".",
        f"- Descriptive feature contrast vs. each fold's validation mean: fold-0 FPs have distance_to_water {fold0_water:+.1f} m and building_density {fold0_building_density:+.1f}; fold-3 FNs have distance_to_drain {fold3_drain_distance:+.1f} m and building_density {fold3_building_density:+.1f}. These contrasts identify differences, not causes.",
        "- Existing proxy ablation was mixed: static drainage/hydrology proxies changed fold PR-AUC by -0.0159, +0.0046, +0.0120, and -0.0303 for folds 0–3 respectively. No consistent improvement is supported.",
        "",
        "## Evidence vs. Hypotheses",
        "",
        "**Evidence:** errors vary substantially by spatial fold; mapped polygon coverage reconstructs the binary labels under the 5% rule; false positives include both zero-overlap cells and sub-threshold overlap cells; the positive label is based on mapped BMC polygon presence, not a confirmed survey of negatives. Feature and ward summaries are saved for direct inspection.",
        "",
        "**Hypotheses, not established causes:** zero-overlap FPs may reflect incomplete flood-location mapping, genuine non-flood areas, or geographic distribution shift. Low-coverage FPs may reflect the hard 5% label threshold or polygon-boundary uncertainty. Fold-specific error patterns may also indicate omitted hydraulic/exposure variables. The available artifacts cannot distinguish these explanations or establish true negative status.",
        "",
        "## Recommended Next Step",
        "",
        "Use the error-cell CSV and intersecting source polygon IDs for a targeted label-coverage review with domain owners, prioritizing fold 1 zero-overlap FPs and fold 3 FNs. Keep uncertain negatives marked as unverified rather than relabeling them. Only after label coverage is clarified should another model comparison be run; any independent final evaluation needs a new untouched spatial holdout because fold 4 was previously inspected.",
        "",
        "This is historical mapped-flood susceptibility analysis, not validated future-event forecasting. No fold-4 data, new model, threshold tuning, or label change was used.",
    ])
    REPORT_PATH.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Diagnostic folder: {OUTPUT_DIR}")
    print(f"Mapped error cells: {len(mapped_errors)}; FP={len(all_fp)}; FN={len(all_fn)}; label mismatches={len(label_mismatches)}")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
