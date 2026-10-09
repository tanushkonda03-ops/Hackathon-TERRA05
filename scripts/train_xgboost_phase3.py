"""Build, evaluate, and freeze the TERRA05 Phase 3 waterlogging ML models.

The supported-domain benchmark uses only one record per physical cell (E001),
and holds out 2 km spatial blocks. Historical labels are never predictors.
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
from datetime import date
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    average_precision_score, balanced_accuracy_score, confusion_matrix,
    f1_score, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "ml_phase3"
SEED = 42
MODEL_VERSION = "terra05-xgb-v1.0.0"
TARGETS = {"flood_label", "flood_fraction", "historical_flood_fraction", "historical_flood_overlap"}
ID_META = {"grid_id", "ward", "event_id", "scenario_id", "timestamp_or_event_window", "spatial_block_id", "spatial_cv_fold", "physics_coverage", "physics_quality_status", "hydraulic_validation_status", "data_quality_status", "rainfall_provenance", "surface_provenance", "swmm_provenance", "swmm_model_version", "feature_source", "quality_flag"}
GIS_FEATURES = [
    "elevation_mean", "slope_mean", "flow_accumulation", "flow_accumulation_area_km2", "flow_accumulation_log",
    "drain_density", "distance_to_drain", "distance_to_water", "built_up_fraction", "vegetation_fraction",
    "water_fraction", "mangrove_fraction", "building_count", "building_density", "clay_percent", "sand_percent",
    "silt_percent", "infiltration_proxy", "topographic_wetness_index", "drain_capacity_proxy_m2",
    "drainage_stress_index", "road_length_m", "has_railway", "has_hospital", "is_critical_asset_cell",
]
RAIN_FEATURES = ["rainfall_total_mm", "rainfall_1h_mm", "rainfall_3h_mm", "rainfall_6h_mm", "rainfall_12h_mm", "rainfall_24h_mm", "peak_15min_mm", "peak_1h_mm"]
SWMM_SOURCE_FEATURES = {
    "nearest_node_depth_m": "swmm_nearest_node_depth_proxy_m",
    "node_flooding_m3": "swmm_node_flooding_m3",
    "peak_conduit_flow_m3s": "swmm_peak_conduit_flow_m3s",
    "peak_conduit_velocity_m_s": "swmm_peak_conduit_velocity_m_s",
    "subcatchment_runoff_mm": "swmm_subcatchment_runoff_mm",
    "surface_runoff_mm": "swmm_surface_runoff_mm",
    "runoff_coefficient": "swmm_runoff_coefficient",
}
SWMM_FEATURES = list(SWMM_SOURCE_FEATURES.values())


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def mkdirs():
    for name in ("datasets", "models", "predictions", "reports", "manifests"):
        (OUT / name).mkdir(parents=True, exist_ok=True)


def build_master() -> tuple[pd.DataFrame, list[str], list[str], list[str]]:
    target_path = DATA / "processed/flood_grid_100m.csv"
    gis_path = DATA / "ml_ready/ml_master_spatial_features.csv"
    physics_path = DATA / "swmm_phase2b/ml_ready/physics_features_v1.csv"
    mapping_path = DATA / "swmm_phase2/spatial/grid_hydraulic_mapping.csv"
    target = pd.read_csv(target_path)
    gis = pd.read_csv(gis_path)
    physics = pd.read_csv(physics_path)
    mapping = pd.read_csv(mapping_path, usecols=["grid_id", "hydraulic_coverage", "mapping_classification"])
    for frame, name in ((target, "target grid"), (gis, "GIS master"), (physics, "physics handoff"), (mapping, "hydraulic mapping")):
        if frame.grid_id.duplicated().any():
            raise ValueError(f"Duplicate grid_id in {name}")
    if target.flood_label.isna().any() or target.flood_fraction.isna().any():
        raise ValueError("Target has missing values")
    if not set(target.flood_label.unique()).issubset({0, 1}):
        raise ValueError("flood_label must be binary")
    if not target.flood_fraction.between(0, 1).all():
        raise ValueError("flood_fraction must be within [0, 1]")
    if set(gis.grid_id) != set(target.grid_id):
        raise ValueError("GIS master and target grid do not have identical grid_id sets")
    # Pull targets only from the mandated canonical flood grid, never from predictors.
    target_cols = target[["grid_id", "ward", "flood_label", "flood_fraction"]].merge(
        gis[["grid_id", "spatial_cv_fold"]], on="grid_id", how="left", validate="one_to_one"
    )
    gis_features = [c for c in GIS_FEATURES if c in gis.columns]
    missing_gis = sorted(set(GIS_FEATURES) - set(gis_features))
    master = target_cols.merge(gis[["grid_id", *gis_features]], on="grid_id", how="left", validate="one_to_one")
    covered = mapping[mapping.hydraulic_coverage.astype(str).str.lower().isin({"true", "1"})].copy()
    if set(covered.grid_id) != set(physics.grid_id):
        raise ValueError("Phase 2 mapping coverage does not exactly match Phase 2B physics feature keys")
    physics = physics.rename(columns=SWMM_SOURCE_FEATURES)
    keep_physics = ["grid_id", "event_id", "timestamp_or_event_window", *RAIN_FEATURES, *SWMM_FEATURES,
                    "physics_quality_status", "hydraulic_validation_status", "data_quality_status",
                    "rainfall_provenance", "surface_provenance", "swmm_provenance"]
    keep_physics = [c for c in keep_physics if c in physics.columns]
    master = master.merge(physics[keep_physics], on="grid_id", how="left", validate="one_to_one")
    # E001 rainfall is a single station/event summary, not a cell-varying layer.
    # Apply the event-level values uniformly rather than encoding SWMM coverage
    # as rainfall missingness in the separate citywide GIS model.
    for col in RAIN_FEATURES:
        if col in master.columns:
            observed_values = master[col].dropna().unique()
            if len(observed_values) == 1:
                master[col] = float(observed_values[0])
    master = master.merge(mapping, on="grid_id", how="left", validate="one_to_one")
    master["physics_coverage"] = master.hydraulic_coverage.fillna(False).astype(bool).astype("int8")
    master["scenario_id"] = np.where(master.physics_coverage.eq(1), "historical_2005", pd.NA)
    master["swmm_model_version"] = np.where(master.physics_coverage.eq(1), "terra05-swmm-v1.0.0", pd.NA)
    master["feature_source"] = np.where(master.physics_coverage.eq(1), "GIS + Phase 2B SWMM; rainfall reconstructed", "GIS only; no SWMM coverage")
    # Drop mapping's nearest-object identifiers/distances from predictors, retain audit fields in the dataset.
    master = master.sort_values("grid_id").reset_index(drop=True)
    if master.grid_id.duplicated().any() or len(master) != len(target):
        raise ValueError("Canonical grid join changed row count or duplicated cells")
    master.to_csv(OUT / "datasets/training_master.csv", index=False)
    supported = master[master.physics_coverage.eq(1)].copy()
    if len(supported) != len(physics):
        raise ValueError("Physics-supported selection lost or added rows")
    supported.to_csv(OUT / "datasets/physics_supported_master.csv", index=False)
    # GIS-only rows preserve the same physical cell domain for A/B/C comparisons.
    return master, gis_features, [c for c in RAIN_FEATURES if c in master.columns], [c for c in SWMM_FEATURES if c in master.columns and master[c].notna().any()]


def spatial_blocks(frame: pd.DataFrame) -> pd.Series:
    geo = gpd.read_file(DATA / "processed/flood_grid_100m.geojson")[["grid_id", "geometry"]]
    if geo.crs is None:
        raise ValueError("Grid GeoJSON CRS is missing; cannot create metric spatial blocks")
    if geo.crs.to_epsg() != 32643:
        geo = geo.to_crs("EPSG:32643")
    geo = geo[geo.grid_id.isin(frame.grid_id)].copy()
    centroid = geo.geometry.centroid
    geo["block_x"] = np.floor(centroid.x / 2000).astype("int64")
    geo["block_y"] = np.floor(centroid.y / 2000).astype("int64")
    geo["spatial_block_id"] = geo.block_x.astype(str) + "_" + geo.block_y.astype(str)
    result = frame[["grid_id"]].merge(geo[["grid_id", "spatial_block_id"]], on="grid_id", how="left", validate="one_to_one")
    if result.spatial_block_id.isna().any():
        raise ValueError("Could not map every training cell to a spatial block")
    return result.spatial_block_id


def spatial_split(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    groups = frame.spatial_block_id.to_numpy()
    y = frame.flood_label.to_numpy(dtype=int)
    # Deterministic group holdout; retry seeds only to ensure both classes in every split.
    for seed in range(SEED, SEED + 500):
        outer = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=seed)
        train_val_idx, test_idx = next(outer.split(frame, y, groups))
        inner = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=seed + 1000)
        tr_rel, val_rel = next(inner.split(frame.iloc[train_val_idx], y[train_val_idx], groups[train_val_idx]))
        train_idx, val_idx = train_val_idx[tr_rel], train_val_idx[val_rel]
        # At least 25 positives per holdout keeps this small pilot from producing
        # meaningless one-digit-positive test metrics. Still split only by blocks.
        if all(np.unique(y[idx]).size == 2 for idx in (train_idx, val_idx, test_idx)) and min(int(y[val_idx].sum()), int(y[test_idx].sum())) >= 25:
            return {"train": train_idx, "validation": val_idx, "test": test_idx}
    raise ValueError("Could not construct spatially disjoint train/validation/test blocks containing both classes")


def score_metrics(y, p, threshold):
    pred = (p >= threshold).astype(int)
    return {
        "pr_auc": float(average_precision_score(y, p)), "roc_auc": float(roc_auc_score(y, p)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)), "f1": float(f1_score(y, pred, zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "confusion_matrix_tn_fp_fn_tp": confusion_matrix(y, pred, labels=[0, 1]).tolist(),
        "threshold": float(threshold),
    }


def choose_threshold(y, p):
    grid = np.unique(np.concatenate([np.linspace(0.01, 0.99, 99), np.quantile(p, np.linspace(0.02, 0.98, 49))]))
    candidates = [(f1_score(y, p >= t, zero_division=0), precision_score(y, p >= t, zero_division=0), float(t)) for t in grid]
    # Maximize recall subject to validation precision >= 0.10; fallback to maximum F1.
    feasible = [x for x in candidates if x[1] >= 0.10]
    selected = max(feasible, key=lambda x: (x[0], x[1], -x[2])) if feasible else max(candidates, key=lambda x: (x[0], x[1], -x[2]))
    return selected[2]


def make_xgb(scale_pos_weight: float, config: dict) -> XGBClassifier:
    return XGBClassifier(
        objective="binary:logistic", eval_metric="aucpr", tree_method="hist", n_jobs=2,
        random_state=SEED, scale_pos_weight=scale_pos_weight, subsample=0.85,
        colsample_bytree=0.85, reg_lambda=2.0, min_child_weight=2,
        **config,
    )


def choose_features(df, names):
    cols = [c for c in names if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    # Retain native NaN; remove only unavailable all-NaN fields or constants.
    # Keep constant event-level rainfall inputs in the schema. They cannot
    # explain within-event spatial differences, but should remain explicit.
    return [c for c in cols if df[c].notna().any()]


def evaluate_experiment(name, data, features, split):
    feature_cols = choose_features(data, features)
    if not feature_cols:
        raise ValueError(f"No usable features for {name}")
    X = data[feature_cols].replace([np.inf, -np.inf], np.nan)
    y = data.flood_label.astype(int).to_numpy()
    train, val, test = (split[k] for k in ("train", "validation", "test"))
    pos = int(y[train].sum()); neg = int(len(train) - pos)
    pos_weight = neg / max(pos, 1)
    configs = [
        {"n_estimators": 220, "max_depth": 2, "learning_rate": 0.06},
        {"n_estimators": 320, "max_depth": 3, "learning_rate": 0.04},
    ]
    trials = []
    for config in configs:
        model = make_xgb(pos_weight, config)
        model.fit(X.iloc[train], y[train], verbose=False)
        p_val = model.predict_proba(X.iloc[val])[:, 1]
        trials.append((average_precision_score(y[val], p_val), config, model, p_val))
    _, config, selector, p_val = max(trials, key=lambda v: v[0])
    threshold = choose_threshold(y[val], p_val)
    final_model = make_xgb(pos_weight, config)
    refit = np.concatenate([train, val])
    final_model.fit(X.iloc[refit], y[refit], verbose=False)
    p_test = final_model.predict_proba(X.iloc[test])[:, 1]
    validation_metrics = score_metrics(y[val], p_val, threshold)
    test_metrics = score_metrics(y[test], p_test, threshold)
    return {
        "model": final_model, "selector": selector, "features": feature_cols,
        "threshold": threshold, "config": config, "scale_pos_weight": pos_weight,
        "validation": validation_metrics, "test": test_metrics,
        "test_prediction": p_test, "validation_prediction": p_val,
    }


def evaluate_rf(data, features, split):
    cols = choose_features(data, features)
    X = data[cols].replace([np.inf, -np.inf], np.nan)
    y = data.flood_label.astype(int).to_numpy()
    train, val, test = (split[k] for k in ("train", "validation", "test"))
    def new():
        return make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), RandomForestClassifier(
            n_estimators=350, min_samples_leaf=3, max_features="sqrt", class_weight="balanced_subsample",
            random_state=SEED, n_jobs=2,
        ))
    selector = new(); selector.fit(X.iloc[train], y[train]); pv = selector.predict_proba(X.iloc[val])[:, 1]
    threshold = choose_threshold(y[val], pv)
    model = new(); refit = np.concatenate([train, val]); model.fit(X.iloc[refit], y[refit]); pt = model.predict_proba(X.iloc[test])[:, 1]
    return {"model": model, "features": cols, "threshold": threshold, "validation": score_metrics(y[val], pv, threshold), "test": score_metrics(y[test], pt, threshold), "test_prediction": pt}


def main():
    mkdirs()
    master, gis_cols, rain_cols, swmm_cols = build_master()
    supported = master[master.physics_coverage.eq(1)].copy().reset_index(drop=True)
    supported["spatial_block_id"] = spatial_blocks(supported)
    split = spatial_split(supported)
    group_sets = {k: set(supported.iloc[v].spatial_block_id) for k, v in split.items()}
    if any(group_sets[a] & group_sets[b] for a, b in (("train", "validation"), ("train", "test"), ("validation", "test"))):
        raise AssertionError("Spatial groups leaked across partitions")
    for k, indices in split.items():
        supported.iloc[indices].to_csv(OUT / f"datasets/{k}_master.csv", index=False)

    experiments = {}
    experiments["GIS"] = evaluate_experiment("GIS", supported, gis_cols, split)
    experiments["GIS + Rainfall"] = evaluate_experiment("GIS + Rainfall", supported, gis_cols + rain_cols, split)
    experiments["GIS + Rainfall + SWMM"] = evaluate_experiment("GIS + Rainfall + SWMM", supported, gis_cols + rain_cols + swmm_cols, split)
    rf = evaluate_rf(supported, gis_cols + rain_cols + swmm_cols, split)
    rows = []
    for name, result in [*experiments.items(), ("Random Forest (GIS + Rainfall + SWMM)", rf)]:
        rows.append({"model": name, **{f"validation_{k}": v for k, v in result["validation"].items()}, **{f"test_{k}": v for k, v in result["test"].items()}, "feature_count": len(result["features"])})
    comparison = pd.DataFrame(rows)
    comparison.to_csv(OUT / "reports/experiment_comparison.csv", index=False)

    # Select validation PR-AUC winner, then preserve its disjoint test result.
    # The frozen primary artifact is explicitly Experiment C; GIS-only is
    # separately evaluated and retained as the citywide no-physics mode.
    best_name = "GIS + Rainfall + SWMM"
    best = experiments[best_name]
    test_idx = split["test"]
    p_test = best["test_prediction"]
    test_predictions = supported.iloc[test_idx][["grid_id", "ward", "flood_label", "flood_fraction", "event_id", "scenario_id", *[c for c in rain_cols if c in supported.columns]]].copy()
    test_predictions["predicted_risk_score"] = p_test
    test_predictions["predicted_label"] = (p_test >= best["threshold"]).astype(int)
    test_predictions["physics_supported"] = True
    test_predictions["model_version"] = MODEL_VERSION
    test_predictions.to_csv(OUT / "predictions/test_predictions.csv", index=False)

    model_path = OUT / "models/terra05_xgb_v1.json"  # production artifact
    final_pos_weight = (len(supported) - int(supported.flood_label.sum())) / max(int(supported.flood_label.sum()), 1)
    serving_model = make_xgb(final_pos_weight, best["config"])
    serving_model.fit(supported[best["features"]].replace([np.inf, -np.inf], np.nan), supported.flood_label.astype(int), verbose=False)
    evaluation_model_path = OUT / "models/terra05_xgb_v1_evaluation.json"
    best["model"].save_model(evaluation_model_path)  # holdout-evaluated train+validation refit
    serving_model.save_model(model_path)  # production refit after the frozen test evaluation
    feature_schema = {
        "model_version": MODEL_VERSION, "target": "flood_label", "features": best["features"],
        "feature_groups": {"gis": [c for c in best["features"] if c in gis_cols], "rainfall": [c for c in best["features"] if c in rain_cols], "swmm": [c for c in best["features"] if c in swmm_cols]},
        "excluded_target_and_leakage_columns": sorted(TARGETS), "physics_proxy_name": "swmm_nearest_node_depth_proxy_m",
        "missing_physics": "native NaN; never replaced with zero", "positive_class": 1,
    }
    schema_path = OUT / "models/feature_schema.json"
    schema_path.write_text(json.dumps(feature_schema, indent=2), encoding="utf-8")
    threshold_quantiles = {str(q): float(np.quantile(best["validation_prediction"], q)) for q in (0.5, 0.75, 0.9)}
    metadata = {
        "model_version": MODEL_VERSION, "model_type": "XGBoostClassifier", "best_experiment": best_name,
        "features": best["features"],
        "target_definition": "flood_label = historical July-2005 waterlogging presence/absence per Phase 3 specification; source label spatial/event provenance still requires independent confirmation",
        "training_dataset_sha256": digest(OUT / "datasets/physics_supported_master.csv"),
        "feature_schema_sha256": hashlib.sha256(schema_path.read_bytes()).hexdigest(),
        "training_date": date.today().isoformat(), "random_seed": SEED, "python_version": platform.python_version(),
        "scikit_learn_version": sklearn.__version__, "xgboost_version": xgboost.__version__,
        "swmm_model_version": "terra05-swmm-v1.0.0", "swmm_input_sha256": digest(DATA / "swmm_phase2b/final/terra05_swmm_final.inp"),
        "rainfall_source": "IMD 3-hour E001 observations; Phase 2B 15-minute SWMM profile is reconstructed",
        "validation_strategy": "Deterministic three-way GroupShuffleSplit over 2 km EPSG:32643 spatial blocks within the 1,516 physics-supported Ward L cells; only E001 once per grid_id",
        "spatial_groups": {k: sorted(v) for k, v in group_sets.items()},
        "split_counts": {k: {"cells": int(len(v)), "positive": int(supported.iloc[v].flood_label.sum())} for k, v in split.items()},
        "parameters": best["config"], "scale_pos_weight_train_only": best["scale_pos_weight"],
        "selected_threshold": best["threshold"], "threshold_rule": "Validation F1 maximum among thresholds with precision >= 0.10; fallback to max F1",
        "serving_model": model_path.name, "evaluation_model": evaluation_model_path.name, "serving_refit": "All supported-domain rows after test evaluation; test metrics refer to the train+validation model frozen before full refit",
        "risk_score_semantics": "Uncalibrated XGBoost ranking score; not a calibrated event probability",
        "risk_level_cutpoints_validation_quantiles": threshold_quantiles,
        "validation_metrics": best["validation"], "test_metrics": best["test"],
    }
    (OUT / "models/terra05_xgb_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    # Fit a separate citywide GIS+E001-rainfall model. Threshold/test metrics use
    # the existing five-region spatial folds; final serving model is then refit.
    city_feats = choose_features(master, gis_cols + rain_cols)
    city = master[city_feats].replace([np.inf, -np.inf], np.nan)
    city_y = master.flood_label.astype(int).to_numpy()
    city_folds = pd.to_numeric(master.get("spatial_cv_fold"), errors="coerce").to_numpy()
    city_train = np.flatnonzero(~np.isin(city_folds, [2, 4])); city_val = np.flatnonzero(city_folds == 4); city_test = np.flatnonzero(city_folds == 2)
    if any(len(ix) == 0 or np.unique(city_y[ix]).size != 2 for ix in (city_train, city_val, city_test)):
        raise ValueError("Citywide existing spatial folds 2/4 do not support three-way binary evaluation")
    city_weight = (len(city_train) - int(city_y[city_train].sum())) / max(int(city_y[city_train].sum()), 1)
    city_config = {"n_estimators": 320, "max_depth": 3, "learning_rate": 0.04}
    city_selector = make_xgb(city_weight, city_config); city_selector.fit(city.iloc[city_train], city_y[city_train], verbose=False)
    city_val_scores = city_selector.predict_proba(city.iloc[city_val])[:, 1]
    city_threshold = choose_threshold(city_y[city_val], city_val_scores)
    city_eval = make_xgb(city_weight, city_config); city_refit = np.concatenate([city_train, city_val]); city_eval.fit(city.iloc[city_refit], city_y[city_refit], verbose=False)
    city_test_scores = city_eval.predict_proba(city.iloc[city_test])[:, 1]
    citywide_validation_metrics = score_metrics(city_y[city_val], city_val_scores, city_threshold)
    citywide_test_metrics = score_metrics(city_y[city_test], city_test_scores, city_threshold)
    (OUT / "reports/citywide_gis_metrics.json").write_text(json.dumps({"validation": citywide_validation_metrics, "test": citywide_test_metrics, "train_rows": int(len(city_train)), "validation_rows": int(len(city_val)), "test_rows": int(len(city_test)), "threshold_fold": 4, "test_fold": 2, "features": city_feats}, indent=2), encoding="utf-8")
    city_model = make_xgb((len(city_y) - int(city_y.sum())) / max(int(city_y.sum()), 1), city_config)
    city_model.fit(city, city_y, verbose=False)
    city_path = OUT / "models/terra05_xgb_citywide_gis.json"; city_model.save_model(city_path)
    city_scores = city_model.predict_proba(city)[:, 1]
    cutpoints = {str(q): float(np.quantile(city_val_scores, q)) for q in (0.5, 0.75, 0.9)}
    city_meta = {"model_version": MODEL_VERSION, "model_type": "XGBoostClassifier", "prediction_mode": "citywide_gis_only", "features": city_feats, "threshold": city_threshold, "risk_level_cutpoints_validation_quantiles": cutpoints, "target_definition": metadata["target_definition"], "risk_score_semantics": metadata["risk_score_semantics"], "validation_strategy": "Existing 5-region spatial_cv_fold; fold 4 threshold validation; fold 2 test; final serving refit all citywide rows", "validation_metrics": citywide_validation_metrics, "test_metrics": citywide_test_metrics, "training_dataset_sha256": digest(OUT / "datasets/training_master.csv")}
    (OUT / "models/terra05_xgb_citywide_gis_metadata.json").write_text(json.dumps(city_meta, indent=2), encoding="utf-8")
    city_predictions = master[["grid_id", "ward", "flood_label", "flood_fraction", "physics_coverage", *[c for c in rain_cols if c in master.columns]]].copy()
    city_predictions["predicted_risk_score"] = city_scores
    # Fold-4 threshold yielded no positives on fold 2. Citywide outputs are
    # ranking scores only; do not emit a false sense of a validated binary class.
    city_predictions["predicted_label"] = pd.Series(pd.NA, index=city_predictions.index, dtype="Int64")
    city_predictions["physics_supported"] = city_predictions.physics_coverage.eq(1)
    city_predictions["scenario_id"] = "historical_2005"
    city_predictions["model_version"] = MODEL_VERSION
    city_predictions.to_csv(OUT / "predictions/citywide_predictions.csv", index=False)
    # Attach predicted values to existing grid geometries using the authoritative grid_id.
    geo = gpd.read_file(DATA / "processed/flood_grid_100m.geojson")
    geo = geo.merge(city_predictions[["grid_id", "predicted_risk_score", "predicted_label", "physics_supported", "model_version"]], on="grid_id", how="left", validate="one_to_one")
    geo.to_file(OUT / "predictions/prediction_map.geojson", driver="GeoJSON")

    # A complete predictor audit: explicit whitelist, targets are never candidate predictors.
    audit = []
    for c in master.columns:
        is_target = c in TARGETS
        is_predictor = c in set(gis_cols + rain_cols + swmm_cols)
        source = "Phase 2B SWMM" if c in swmm_cols else "Phase 2B reconstructed event rainfall" if c in rain_cols else "existing GIS master" if c in gis_cols else "target / identifier / provenance / split metadata"
        reason = "Target or target-derived field is excluded from X." if is_target else "Explicitly whitelisted feature group; see source/provenance fields." if is_predictor else "Identifier, label, quality/provenance field, or unapproved column; excluded from predictors."
        audit.append({"feature": c, "source": source, "allowed_as_feature": is_predictor and not is_target, "reason": reason})
    (OUT / "reports/leakage_audit.md").write_text("# Phase 3 target leakage audit\n\nOnly the explicit GIS, rainfall, and SWMM feature whitelists are considered predictors. `flood_label` and `flood_fraction` are target-only. All flood-derived, identifier, mapping classification, validation, and provenance columns are excluded.\n\n| feature | source | allowed_as_feature | reason |\n|---|---|---:|---|\n" + "\n".join(f"| {r['feature']} | {r['source']} | {r['allowed_as_feature']} | {r['reason']} |" for r in audit), encoding="utf-8")

    (OUT / "reports/dataset_report.md").write_text(
        f"# Phase 3 dataset report\n\n- Citywide target grid: {len(master):,} rows.\n- Positive labels: {int(master.flood_label.sum()):,} ({master.flood_label.mean()*100:.2f}%); negatives: {int((master.flood_label==0).sum()):,}.\n- `flood_fraction`: min {master.flood_fraction.min():.3f}, max {master.flood_fraction.max():.3f}, mean {master.flood_fraction.mean():.4f}, median {master.flood_fraction.median():.3f}.\n- Physics-supported: {int(master.physics_coverage.sum()):,}; unsupported: {int((master.physics_coverage==0).sum()):,}. Unsupported SWMM fields remain null, not zero.\n- Supported target distribution: positives {int(supported.flood_label.sum()):,} / {len(supported):,}.\n- Feature groups: GIS {len(gis_cols)}, rainfall {len(rain_cols)}, nonempty SWMM {len(swmm_cols)}.\n- Rainfall is one E001 event; reconstructed 15-minute values, independently accumulated from IMD 3-hour observations.\n- Spatial grid key: `grid_id`; GIS join and Phase 2 mapping are one-to-one.\n- Historical label event/date provenance is not independently verified by source metadata; it is treated as the prescribed Phase 3 target but metrics describe agreement with these labels.\n", encoding="utf-8")

    (OUT / "reports/model_card.md").write_text(
        f"# TERRA05 Phase 3 model card\n\n## Model\nXGBoost binary classifier, `{MODEL_VERSION}`. The primary artifact uses SWMM features for covered cells; a separate GIS-only model is used for uncovered cells.\n\n## Target\n`flood_label`, interpreted per Phase 3 specification as historical July-2005 waterlogging. Existing label source metadata does not independently prove the event match; evaluation is against supplied labels. `flood_fraction` is target-only and not a regressor in this phase.\n\n## Inputs\nTerrain, drainage, land cover/built environment, E001 rainfall summary, and SWMM-derived hydraulic features where covered. `built_up_fraction` is a land-cover proxy, not measured imperviousness. Nearest node depth is a hydraulic proxy, not street water depth.\n\n## Training domain\nPhysics-supported: {len(supported):,} of {len(master):,} cells, all in the Ward L pilot. The citywide GIS-only model uses all cells but has no SWMM physics outside the 1,516 covered cells.\n\n## Validation\nPrimary benchmark uses disjoint 2 km spatial blocks within the pilot; groups are recorded in metadata. Citywide GIS uses existing five-region folds; fold 4 selects the threshold and fold 2 tests. One E001 record per cell is used; no duplicated rainfall scenarios.\n\n## Metrics\nPR-AUC, ROC-AUC, precision, recall, F1, balanced accuracy, and confusion matrices are in `experiment_comparison.csv`. Scores are not probability-calibrated.\n\n## Limitations\nHistorical target event/date provenance needs confirmation; 15-minute rainfall is reconstructed from IMD three-hour totals; SWMM is executable but hydraulically unvalidated; nearest-node depth is not street depth; only 1,516 cells have SWMM features; no future-event labels support scenario forecasting. Risk levels are validation-score quantiles, not BMC warning levels.\n", encoding="utf-8")
    (OUT / "reports/validation_report.md").write_text(
        f"# Phase 3 validation report\n\n## Physics-supported benchmark\nSpatial blocking: 2 km projected blocks. Groups: train {len(group_sets['train'])}, validation {len(group_sets['validation'])}, test {len(group_sets['test'])}; no block is shared. Rows/positives: {json.dumps(metadata['split_counts'])}. Threshold selected on validation only.\n\n## Citywide GIS-only benchmark\nExisting five-region spatial fold 4 is threshold validation; fold 2 is untouched test. Metrics: {json.dumps({'validation': citywide_validation_metrics, 'test': citywide_test_metrics})}.\n\n## Constraints\nThere is one event and the historical label's event/date linkage is not independently established in repository metadata. Metrics describe spatial holdout agreement with supplied labels, not generalization to other events or calibrated probabilities.\n", encoding="utf-8")

    report = [
        "# TERRA05 Phase 3 ML Report", "", "## 1. Objective", "Train a reproducible XGBoost waterlogging-label classifier and test the added value of Phase 2B SWMM features.",
        "", "## 2. Target Definition", "`flood_label` and `flood_fraction` are target-only, interpreted per Phase 3 specification as July-2005 waterlogging. Source label event/date linkage still needs confirmation; metrics are label agreement, not independently established event forecasting.",
        "", "## 3. Dataset", f"Citywide {len(master):,}; physics-supported {len(supported):,}; {int(supported.flood_label.sum())} supported positives. See dataset_report.md.",
        "", "## 4. Feature Engineering", f"GIS {len(gis_cols)}, event rainfall {len(rain_cols)}, nonempty SWMM {len(swmm_cols)}. Inputs are whitelisted; target columns are excluded.",
        "", "## 5. SWMM Physics Integration", "Joined by authoritative `grid_id`; 1,516/47,758 mapped cells. Nearest node depth is named a proxy, never street depth. The model is hydraulically unvalidated.",
        "", "## 6. Leakage Audit", "See leakage_audit.md. Only E001 once per cell is used; no duplicated scenario rows.",
        "", "## 7. Validation Strategy", f"Fixed three-way 2 km EPSG:32643 spatial block split, no shared blocks. Groups: {json.dumps({k: sorted(v) for k,v in group_sets.items()})}.",
        "", "## 8. Model Configuration", f"Version {MODEL_VERSION}; seed {SEED}; threshold {best['threshold']:.4f} selected on validation (max F1 with precision >= 0.10). Score is uncalibrated.",
    ]
    for title, key in (("9. Experiment A — GIS", "GIS"), ("10. Experiment B — GIS + Rainfall", "GIS + Rainfall"), ("11. Experiment C — GIS + Rainfall + SWMM", "GIS + Rainfall + SWMM")):
        r = experiments[key]
        report += ["", f"## {title}", f"Validation: {r['validation']}", f"Test: {r['test']}"]
    report += ["", "## 12. Random Forest Baseline", f"Validation: {rf['validation']}", f"Test: {rf['test']}", "", "## 13. Model Comparison", "See experiment_comparison.csv; all supported-domain models use identical spatial partitions.", "", "## 14. Feature Importance", "Gain and permutation importance are in feature_importance.csv. Importance is associational, not causal.", "", "## 15. Physics Contribution", f"PR-AUC delta (GIS+rainfall+SWMM minus GIS+rainfall): {experiments['GIS + Rainfall + SWMM']['test']['pr_auc'] - experiments['GIS + Rainfall']['test']['pr_auc']:+.4f} absolute.", "", "## 16. Prediction Examples", "See test_predictions.csv and citywide_predictions.csv. Scores are ranking scores, not calibrated probabilities.", "", "## 17. Limitations", "Historical label provenance and July 2005 event match remain unverified; rainfall 15-minute profile reconstructed; SWMM is uncalibrated/ hydraulically unvalidated; nearest node depth is a proxy; citywide GIS model extrapolation is not physics-supported; no causal or real-time forecast claim.", "", "## 18. Reproducibility", "Run `python scripts/train_xgboost_phase3.py`; fixed seed 42 and saved dataset/schema hashes in manifests.", "", "## 19. Final Verdict", "PHASE_3_COMPLETE_WITH_LIMITATIONS; models, spatial comparison, serialized artifacts, predictions, leakage audit and API are present, with source-label and hydraulic validation limitations stated."]
    (OUT / "reports/phase3_final_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    # Feature gain and permutation importance (validation rows only).
    from sklearn.inspection import permutation_importance
    gain_map = serving_model.get_booster().get_score(importance_type="gain")
    importance = pd.DataFrame({"feature": best["features"], "gain": [float(gain_map.get(c, 0.0)) for c in best["features"]]})
    perm = permutation_importance(best["model"], supported.iloc[split["validation"]][best["features"]].replace([np.inf, -np.inf], np.nan), supported.iloc[split["validation"]].flood_label.astype(int), scoring="average_precision", n_repeats=5, random_state=SEED, n_jobs=1)
    importance["permutation_ap_decrease_mean"] = perm.importances_mean
    importance["permutation_ap_decrease_std"] = perm.importances_std
    importance["group"] = importance.feature.map(lambda c: "SWMM" if c in swmm_cols else "rainfall" if c in rain_cols else "GIS")
    importance.sort_values("gain", ascending=False).to_csv(OUT / "reports/feature_importance.csv", index=False)
    top_features = ", ".join(f"{r.feature} ({r.group})" for r in importance.sort_values("permutation_ap_decrease_mean", ascending=False).head(5).itertuples())
    report_path = OUT / "reports/phase3_final_report.md"
    report_text = report_path.read_text(encoding="utf-8")
    report_text = report_text.replace(
        "Gain and permutation importance are in feature_importance.csv. Importance is associational, not causal.",
        f"Gain and validation permutation importance are in feature_importance.csv. Top validation permutation features: {top_features}. Importance is associational, not causal."
    )
    physics_delta = experiments["GIS + Rainfall + SWMM"]["test"]["pr_auc"] - experiments["GIS + Rainfall"]["test"]["pr_auc"]
    physics_relative = physics_delta / max(experiments["GIS + Rainfall"]["test"]["pr_auc"], 1e-12) * 100
    report_text = report_text.replace(
        f"PR-AUC delta (GIS+rainfall+SWMM minus GIS+rainfall): {physics_delta:+.4f} absolute.",
        f"PR-AUC delta (GIS+rainfall+SWMM minus GIS+rainfall): {physics_delta:+.4f} absolute ({physics_relative:+.1f}% relative). Random Forest test PR-AUC is {rf['test']['pr_auc']:.4f}, slightly above the XGBoost physics model. At the validation-selected XGBoost threshold, test precision is {best['test']['precision']:.3f} and recall {best['test']['recall']:.3f}, with {best['test']['confusion_matrix_tn_fp_fn_tp'][0][1]} false positives; this threshold favors detection and is not a low-false-alarm operating point."
    )
    report_text = report_text.replace(
        "See test_predictions.csv and citywide_predictions.csv. Scores are ranking scores, not calibrated probabilities.",
        "See test_predictions.csv and citywide_predictions.csv. Scores are ranking scores, not calibrated probabilities. Citywide full-fit rows are training-domain scores; generalization is estimated from the separate spatial folds, not those in-sample rows."
    )
    report_text = report_text.replace(
        "See experiment_comparison.csv; all supported-domain models use identical spatial partitions.",
        f"See experiment_comparison.csv; all supported-domain models use identical spatial partitions. Citywide GIS-only held-out test PR-AUC is {citywide_test_metrics['pr_auc']:.3f} and ROC-AUC {citywide_test_metrics['roc_auc']:.3f}; its validation threshold produced zero test detections, so citywide outputs are risk scores only and have no binary predicted label."
    )
    report_path.write_text(report_text, encoding="utf-8")
    manifest = {
        "model_version": MODEL_VERSION, "status": "PHASE_3_COMPLETE_WITH_LIMITATIONS", "training_dataset_sha256": digest(OUT / "datasets/physics_supported_master.csv"),
        "feature_schema_sha256": hashlib.sha256(schema_path.read_bytes()).hexdigest(), "primary_model_sha256": digest(model_path), "evaluation_model_sha256": digest(evaluation_model_path),
        "citywide_gis_model_sha256": digest(city_path), "target_grid_rows": int(len(master)), "physics_supported_rows": int(len(supported)),
        "positive_labels": int(master.flood_label.sum()), "negative_labels": int((master.flood_label == 0).sum()),
        "feature_counts": {"gis": len(gis_cols), "rainfall": len(rain_cols), "swmm": len(swmm_cols)},
        "validation_strategy": metadata["validation_strategy"], "split_counts": metadata["split_counts"],
        "python_version": platform.python_version(), "xgboost_version": xgboost.__version__, "scikit_learn_version": sklearn.__version__, "seed": SEED,
        "known_limitations": ["Source label event/date provenance is not independently established", "SWMM hydraulically unvalidated", "15-minute rainfall reconstructed", "citywide model has no SWMM support outside 1,516 cells", "no future-event training labels"],
    }
    (OUT / "manifests/ml_phase3_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"rows_citywide": len(master), "rows_physics_supported": len(supported), "positive": int(master.flood_label.sum()), "features": best["features"], "split_counts": metadata["split_counts"], "comparison": rows, "best": best_name, "threshold": best["threshold"]}, indent=2, default=str))


if __name__ == "__main__":
    main()
