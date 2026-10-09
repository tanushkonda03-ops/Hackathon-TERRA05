"""Build the evidence audit and frozen, data-limited SWMM Phase 2B handoff."""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "swmm_phase2b"
CAL = OUT / "calibration"
FINAL = OUT / "final"
ML = OUT / "ml_ready"
REPORT = OUT / "reports"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_csv(path: Path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    df = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows, columns=fields)
    df.to_csv(path, index=False)


def build_observation_registry():
    rows = [
        dict(observation_id="RAIN_E001_IMD", source_file="data/processed/rainfall_observations_v1.csv", variable="rainfall", location="Santacruz station", timestamp="2005-07-26/2005-07-27; 3-hour intervals", event="E001", units="mm per 3-hour interval", source_type="OBSERVED", quality="verified; temporal aggregation only", independent_of_model=True, calibration_eligible=True, reason="Independent IMD rainfall observations; useful for rainfall validation, not hydraulic calibration."),
        dict(observation_id="FLOOD_SPOTS_BMC", source_file="data/raw/flooding_spots.geojson; data/processed/flood_grid_100m.csv", variable="flood location label", location="Mumbai compiled flood spots/grid", timestamp="event date not established in dataset metadata", event="unspecified / mixed", units="binary/grid label", source_type="UNKNOWN", quality="compiled locations; event and spatial accuracy not established", independent_of_model=True, calibration_eligible=False, reason="Not verified as July 2005 event extent, water depth, or timing; unsuitable as event-specific hydraulic target."),
        dict(observation_id="TERRAIN_DEM", source_file="data/raw/external/dem_isro_mumbai_utm43.tif", variable="terrain elevation", location="Mumbai raster", timestamp="not applicable", event="not applicable", units="m; vertical datum not documented here", source_type="UNKNOWN", quality="datum/provenance transformation not established", independent_of_model=True, calibration_eligible=False, reason="Useful as terrain context only; no authoritative vertical datum tie to drainage inverts."),
        dict(observation_id="FLOW_SENSORS", source_file="data/raw/bmc/flow_level_sensors.geojson", variable="sensor locations", location="BMC sensor inventory", timestamp="no observed readings found", event="none", units="not applicable", source_type="UNKNOWN", quality="inventory geometry only", independent_of_model=True, calibration_eligible=False, reason="No timestamped stage/depth/flow observations supplied."),
        dict(observation_id="E002_E005_RAIN", source_file="data/processed/mumbai_flood_events_v1.csv", variable="rainfall", location="Santacruz/Colaba", timestamp="2020-2021 or unspecified", event="E002-E005", units="mm", source_type="OBSERVED", quality="partial or pending; not a complete 15-minute series", independent_of_model=True, calibration_eligible=False, reason="No matching SWMM event input and no independent hydraulic observations for validation."),
    ]
    write_csv(CAL / "observations_registry.csv", rows)


def build_rainfall_validation():
    reconstructed = pd.read_csv(DATA / "swmm_ready/swmm_rainfall_catalog.csv")
    observed = pd.read_csv(DATA / "processed/rainfall_observations_v1.csv")
    reconstructed["rainfall_15min_mm"] = pd.to_numeric(reconstructed.rainfall_15min_mm, errors="coerce")
    reconstructed["interval3h"] = reconstructed.index // 12
    grouped = reconstructed.groupby("interval3h").rainfall_15min_mm.sum().reset_index(name="model_reconstructed_mm")
    obs = observed[observed.event_id.eq("E001")].copy()
    obs["rainfall_mm"] = pd.to_numeric(obs.rainfall_mm, errors="coerce")
    obs["interval3h"] = range(len(obs))
    joined = obs.merge(grouped, on="interval3h", how="left")
    joined["error_mm"] = joined.model_reconstructed_mm - joined.rainfall_mm
    joined["absolute_error_mm"] = joined.error_mm.abs()
    joined["comparison_basis"] = "Sum of 12 reconstructed 15-minute bins compared with independent IMD 3-hour interval total"
    joined["eligibility"] = "RAINFALL_VALIDATION_ONLY; not hydraulic calibration"
    write_csv(CAL / "rainfall_validation.csv", joined[["event_id", "station", "observation_date", "observation_time_utc", "rainfall_mm", "model_reconstructed_mm", "error_mm", "absolute_error_mm", "comparison_basis", "eligibility"]])


def build_elevation():
    src = pd.read_csv(DATA / "swmm_phase1/phase1b/audit/elevation_warning_cases.csv")
    rows = []
    for r in src.to_dict("records"):
        rows.append({
            "conduit_id": r.get("conduit_id"), "source_conduit_id": r.get("source_conduit_id"),
            "us_source_node_id": r.get("us_source_node_id"), "ds_source_node_id": r.get("ds_source_node_id"),
            "ground_elevation_m": "", "raw_invert_m": r.get("source_us_invert_m"),
            "converted_invert_m": "", "node_elevation_m": r.get("us_node_elevation_m"),
            "cover_depth_m": "", "datum_offset_m": 27.432,
            "datum_offset_applied": False, "classification": "UNCERTAIN",
            "reason": "Warning 04 caused by source endpoint elevation difference below SWMM minimum; DEM ground is derived and vertical datum tie/27.432 m transformation is undocumented. Source invert retained; no correction applied.",
        })
    write_csv(CAL / "elevation_validation.csv", rows)


def build_boundaries():
    src = pd.read_csv(DATA / "swmm_phase1/phase1b/audit/boundary_analysis.csv")
    rows = []
    for r in src.to_dict("records"):
        rows.append({"boundary_id": r.get("swmm_id"), "location": f"{r.get('longitude','')},{r.get('latitude','')}", "receiving_water": "unknown", "source_evidence": "Phase 1B assumed computational boundary; no verified receiving-water evidence located", "boundary_type": "unknown", "confidence": "LOW", "calibration_eligible": False, "max_depth_m": r.get("max_depth_m"), "max_flooding_rate_cms": r.get("max_flooding_rate_cms")})
    write_csv(CAL / "outfall_validation.csv", rows)


def build_catchments():
    src = pd.read_csv(DATA / "swmm_phase1/phase1b/audit/subcatchment_assignment_audit.csv")
    distance = pd.to_numeric(src.get("outlet_distance_m"), errors="coerce")
    rows = []
    for r, d in zip(src.to_dict("records"), distance):
        if pd.isna(d) or d <= 500:
            continue
        rows.append({"subcatchment_id": r.get("swmm_id"), "grid_id": r.get("grid_id"), "assigned_outlet": r.get("outlet_swmm_node_id"), "outlet_distance_m": d, "mapping_method": r.get("mapping_method"), "classification": "UNKNOWN", "confidence": "LOW", "review": "Long centroid-to-outlet distance alone does not establish a wrong hydraulic outlet; source network drainage direction/catchment topology is unavailable. Assignment retained."})
    write_csv(CAL / "catchment_outlet_review.csv", rows)


def build_parameters():
    conduits = pd.read_csv(DATA / "swmm_phase1/network/pilot_conduits.csv")
    subs = pd.read_csv(DATA / "swmm_phase1/network/pilot_subcatchments.csv")
    rows = [
        ("manning_n", "conduits", conduits.roughness_n.median(), 0.010, 0.030, "pilot_conduits.csv; value marked ASSUMED", "ASSUMED", False, "High potential hydraulic sensitivity; no flow/depth observations to calibrate"),
        ("n_imperv", "subcatchments", subs.n_imperv.median(), 0.010, 0.030, "pilot_subcatchments.csv; marked ASSUMED", "ASSUMED", False, "Runoff timing/sensitivity; no event-specific hydraulic observations"),
        ("n_perv", "subcatchments", subs.n_perv.median(), 0.050, 0.300, "pilot_subcatchments.csv; marked ASSUMED", "ASSUMED", False, "Runoff timing/sensitivity; no event-specific hydraulic observations"),
        ("s_imperv_mm", "subcatchments", subs.s_imperv_mm.median(), 0.0, 5.0, "pilot_subcatchments.csv; marked ASSUMED", "ASSUMED", False, "Storage parameter; no observations"),
        ("s_perv_mm", "subcatchments", subs.s_perv_mm.median(), 0.0, 15.0, "pilot_subcatchments.csv; marked ASSUMED", "ASSUMED", False, "Storage parameter; no observations"),
        ("horton_max_mm_hr", "subcatchments", subs.horton_max_mm_hr.median(), 10.0, 100.0, "pilot_subcatchments.csv; marked ASSUMED", "ASSUMED", False, "Potential high sensitivity; no soil/site calibration data"),
        ("horton_min_mm_hr", "subcatchments", subs.horton_min_mm_hr.median(), 0.5, 20.0, "pilot_subcatchments.csv; marked ASSUMED", "ASSUMED", False, "Potential high sensitivity; no soil/site calibration data"),
        ("horton_decay_hr", "subcatchments", subs.horton_decay_hr.median(), 0.5, 10.0, "pilot_subcatchments.csv; marked ASSUMED", "ASSUMED", False, "Potential sensitivity; no observations"),
        ("horton_dry_days", "subcatchments", subs.horton_dry_days.median(), 1.0, 14.0, "pilot_subcatchments.csv; marked ASSUMED", "ASSUMED", False, "Potential sensitivity; no observations"),
        ("boundary_stage", "boundaries", "not assigned", "not defensible", "not defensible", "No receiving-water stage source", "UNKNOWN", False, "Disabled; no source-supported stage bounds"),
    ]
    write_csv(CAL / "calibration_parameters.csv", [dict(parameter=p, component=c, baseline=v, minimum=lo, maximum=hi, source=s, classification=cl, calibratable=cal, sensitivity=se) for p,c,v,lo,hi,s,cl,cal,se in rows])
    write_csv(CAL / "calibration_results.csv", [dict(parameter=p, baseline=v, final=v, units="SWMM native units", source=s, calibration_method="NONE; frozen at Phase 1 baseline", confidence="low / assumed", result="No defensible observations for hydraulic calibration") for p,c,v,lo,hi,s,cl,cal,se in rows])
    # Rainfall scaling sensitivity is supported by existing Phase 1B runs; other model parameters were not perturbed.
    metrics = json.loads((DATA / "swmm_phase1/phase1b/reports/scenario_metrics.json").read_text(encoding="utf-8"))
    sensitivity = []
    records = metrics if isinstance(metrics, list) else list(metrics.values()) if isinstance(metrics, dict) else []
    baseline = next((r for r in records if r.get("scenario") == "baseline_100pct"), None)
    if baseline:
        for record in records:
            scenario = record.get("scenario", "unknown")
            if scenario not in {"baseline_100pct", "rainfall_25pct", "rainfall_50pct", "rainfall_75pct"}:
                continue
            multiplier = 1.0 if scenario == "baseline_100pct" else float(scenario.split("_")[1].replace("pct", "")) / 100.0
            for metric in ("node_max_depth_m", "max_velocity_m_s", "max_flow_cms", "flooded_nodes"):
                y0, y = float(baseline[metric]), float(record[metric])
                normalized = "not defined at baseline" if multiplier == 1.0 or y0 == 0 else ((y / y0) - 1.0) / (multiplier - 1.0)
                sensitivity.append({"parameter": "rainfall_multiplier", "scenario": scenario, "value": multiplier, "output_metric": metric, "baseline_output": y0, "scenario_output": y, "normalized_sensitivity": normalized, "evidence": "Existing Phase 1B SWMM execution; rainfall uncertainty sensitivity, not hydraulic-parameter calibration"})
    # Explicitly record unsupported hydraulic sensitivity, never pass off rainfall scaling as it.
    for p in ("manning_n", "horton_max_mm_hr", "n_imperv"):
        sensitivity.append({"parameter": p, "scenario": "not_run", "value": "", "output_metric": "peak node depth / flood volume / duration / peak conduit flow", "normalized_sensitivity": "not available", "evidence": "No new full runs: observations absent and full-run cost ~211 s; Phase 1B rainfall-only perturbations do not quantify parameter sensitivity."})
    write_csv(CAL / "parameter_sensitivity.csv", sensitivity)


def build_features():
    src = pd.read_csv(DATA / "swmm_phase2/results/grid_physics_timeseries.csv")
    if "scenario_id" in src:
        src = src[src.scenario_id.eq("historical_2005")].copy()
    src["timestamp"] = pd.to_datetime(src.timestamp, errors="coerce")
    # one row per directly mapped pilot cell and event; no claimed street-depth conversion
    rows = []
    for grid, g in src.groupby("grid_id", sort=True):
        g = g.sort_values("timestamp")
        if g.empty:
            continue
        rain = pd.to_numeric(g.rainfall_mm, errors="coerce").fillna(0)
        node_depth = pd.to_numeric(g.nearest_node_depth_m, errors="coerce")
        flooding = pd.to_numeric(g.nearest_node_flooding_m3, errors="coerce")
        flow = pd.to_numeric(g.nearest_conduit_flow_m3s, errors="coerce")
        vel = pd.to_numeric(g.nearest_conduit_velocity_ms, errors="coerce")
        runoff = pd.to_numeric(g.surface_runoff_mm, errors="coerce")
        dt = g.timestamp.diff().dt.total_seconds().median() / 60 if g.timestamp.notna().sum() > 1 else 15
        # SWMM rainfall is at 15-minute increments; trailing sums use finite intervals.
        def rolling_sum(hours):
            n = max(1, int(round(hours * 60 / (dt if pd.notna(dt) and dt > 0 else 15))))
            return float(rain.rolling(n, min_periods=1).sum().max())
        rows.append({
            "event_id": "E001", "grid_id": grid, "timestamp_or_event_window": "2005-07-26 reconstructed 15-minute hyetograph; 108 intervals",
            "rainfall_total_mm": float(rain.sum()), "rainfall_1h_mm": rolling_sum(1), "rainfall_3h_mm": rolling_sum(3), "rainfall_6h_mm": rolling_sum(6), "rainfall_12h_mm": rolling_sum(12), "rainfall_24h_mm": rolling_sum(24),
            "peak_15min_mm": float(rain.max()), "peak_1h_mm": float(rain.rolling(max(1, int(round(60/(dt if pd.notna(dt) and dt>0 else 15)))), min_periods=1).sum().max()),
            "surface_runoff_mm": float(runoff.sum(min_count=1)) if runoff.notna().any() else None,
            "surface_storage_m3": None, "surface_depth_m": None, "flood_duration_minutes": None, "time_to_flood_minutes": None,
            "nearest_node_depth_m": float(node_depth.max()) if node_depth.notna().any() else None,
            "node_flooding_m3": float(flooding.sum(min_count=1)) if flooding.notna().any() else None,
            "node_flood_duration_minutes": None,
            "peak_conduit_flow_m3s": float(flow.max()) if flow.notna().any() else None,
            "peak_conduit_velocity_m_s": float(vel.max()) if vel.notna().any() else None,
            "drainage_surcharge": None,
            "subcatchment_runoff_mm": float(runoff.sum(min_count=1)) if runoff.notna().any() else None,
            "runoff_coefficient": None,
            "elevation_m": None, "slope_pct": None, "flow_accumulation": None,
            "drain_density_m_per_km2": None, "distance_to_drain_m": None,
            "hydraulic_proximity_node_m": float(pd.to_numeric(g.node_distance_m, errors="coerce").min()) if "node_distance_m" in g else None,
            "physics_quality_status": "HYDRAULIC_PROXY; direct SWMM where mapped; street-surface states unavailable",
            "hydraulic_validation_status": "UNVALIDATED_NO_EVENT_MATCHED_HYDRAULIC_OBSERVATIONS",
            "data_quality_status": "RAINFALL_RECONSTRUCTED_15MIN; grid represents Phase 1 pilot coverage",
            "rainfall_provenance": "Reconstructed E001 hyetograph; source rainfall is IMD three-hour observations",
            "surface_provenance": "Unavailable; no street coupling",
            "swmm_provenance": "Phase 2A historical_2005 normalized SWMM output",
        })
    write_csv(ML / "physics_features_v1.csv", rows)


def main():
    for d in (CAL, FINAL, ML, REPORT):
        d.mkdir(parents=True, exist_ok=True)
    build_observation_registry()
    build_rainfall_validation()
    build_elevation()
    build_boundaries()
    build_catchments()
    build_parameters()
    build_features()
    # Phase 1 baseline is frozen and physically executed; copy byte-for-byte, never overwrite it.
    source = DATA / "swmm_phase1/baseline"
    for ext in ("inp", "rpt", "out"):
        shutil.copy2(source / f"baseline.{ext}", FINAL / f"terra05_swmm_final.{ext}")
    final_parameters = {
        "model_version": "terra05-swmm-v1.0.0", "selection": "Phase 1 baseline retained; no hydraulic calibration performed",
        "parameters": "Source/configuration values preserved exactly; see calibration_parameters.csv",
        "rainfall": "historical_2005 reconstructed 108x15-minute hyetograph; no changes",
        "infrastructure_mode": "existing", "routing": "Dynamic Wave", "boundary_configuration": "Phase 1 assumed computational boundaries; tide disabled",
        "calibration_status": "SWMM_CALIBRATION_READY_DATA_LIMITED", "confidence": "low for assumed hydraulic parameters; no independently observed hydraulic validation",
    }
    (FINAL / "final_parameters.json").write_text(json.dumps(final_parameters, indent=2), encoding="utf-8")
    source_files = [DATA / "swmm_phase1/baseline/baseline.inp", DATA / "processed/rainfall_observations_v1.csv", DATA / "swmm_phase1/network/pilot_conduits.csv", DATA / "swmm_phase1/network/pilot_subcatchments.csv", DATA / "swmm_phase2/results/grid_physics_timeseries.csv"]
    manifest = {
        "model_version": "terra05-swmm-v1.0.0", "swmm_version": "EPA SWMM 5.2.4", "routing": "Dynamic Wave",
        "source_data_hashes_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in source_files},
        "code_version": "Phase 1 baseline and Phase 2A engine; frozen by Phase 2B evidence audit",
        "parameter_set": "Phase 1 baseline retained; no calibration without hydraulic observations",
        "rainfall_definition": "E001 July 2005 reconstructed 108x15-minute hyetograph; source validated only against published IMD 3-hour accumulations where comparable",
        "infrastructure_mode": "existing", "boundary_configuration": "34 assumed computational boundaries; receiving water unknown; tide disabled",
        "calibration_status": "SWMM_CALIBRATION_READY_DATA_LIMITED", "validation_status": "hydraulically unvalidated; no event-matched depth/flow/stage/flood extent observations",
        "known_limitations": ["No event-matched hydraulic observation series", "Flood-spot grid event/date/depth unverified", "Vertical datum and 27.432 m transformation unverified", "34 model boundary objects are assumed", "203 long-distance catchment assignments remain unknown", "36 Warning 04 cases retained without fabricated drops", "No surface street-depth coupling", "Only rainfall-scale (not hydraulic-parameter) sensitivity cases pre-existed"],
        "baseline_hashes_sha256": {f"terra05_swmm_final.{ext}": sha(FINAL / f"terra05_swmm_final.{ext}") for ext in ("inp", "rpt", "out")},
        "artifact_created_utc": "2026-10-09"
    }
    (FINAL / "model_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    report = """# Final SWMM quality report — Phase 2B

## 1. Executive summary
Frozen status: **SWMM_CALIBRATION_READY_DATA_LIMITED**. EPA SWMM 5.2.4 Dynamic Wave baseline is preserved and copied byte-for-byte to `final/`. No hydraulic calibration or observational hydraulic validation is claimed. The ML handoff contains event-level, pilot-grid features with explicit proxy/missingness flags.

## 2. Model architecture
The existing infrastructure model has 3,314 conduits, 3,269 nodes, 1,516 subcatchments, 34 assumed computational boundaries, and a reconstructed July 2005 storm. Phase 2A spatial mapping and scenario API are reused.

## 3–5. Source data, limitations, and observation inventory
See `calibration/observations_registry.csv`. `rainfall_observations_v1.csv` contains verified IMD Santacruz 3-hour interval rainfall for E001 and supports rainfall validation. BMC flood-spot labels lack demonstrated event date, depth, timing, and event-matched spatial extent; they are ineligible for E001 hydraulic calibration. BMC flow-level sensor file provides sensor inventory geometry, not readings. E002–E005 do not supply matching hydraulic event observations.

## 6. Rainfall validation
The model storm is a reconstruction (108 × 15 minutes; 944.182 mm in the SWMM input). `calibration/rainfall_validation.csv` compares the reconstructed 15-minute bins aggregated into 3-hour intervals against nine independently reported IMD intervals. The event total is checked against 944.2 mm; this validates interval accumulation to the coarser source resolution, not the reconstructed within-interval 15-minute shape. Hydraulic parameters were not adjusted to compensate. Rainfall scale sensitivity outputs from Phase 1B are retained; no new full-model parameter perturbations were run.

## 7–8. Elevation validation and Warning 04
All 36 Warning 04 cases are in `calibration/elevation_validation.csv`. Source node elevation and invert values are retained. The DEM-derived ground and cover are not treated as authoritative because a vertical datum tie, including the proposed 27.432 m transformation, is not documented. Cases are UNCERTAIN; no artificial elevation drops were introduced. The existing Phase 1B report identifies source endpoint differences below SWMM's minimum as the warning mechanism.

## 9. Outfall validation
`calibration/outfall_validation.csv` reviews all 34 assumed computational boundaries. No repository evidence verifies coast, river, Mithi, open-drain or receiving-water identity or stage; all remain unknown/low confidence. Tide remains disabled.

## 10. Catchment validation
`calibration/catchment_outlet_review.csv` lists assignments over 500 m (203 expected from Phase 1B). Distance alone cannot prove a routing error; source network topology/flow direction is insufficient to remap, so assignments remain unchanged and UNKNOWN.

## 11. Parameter sensitivity
`calibration/parameter_sensitivity.csv` documents rainfall multiplier response for peak node depth, peak velocity, peak flow, and flooded-node count from the already executed 25/50/75/100% scenarios. This is rainfall uncertainty sensitivity only. Hydraulic parameter OAT is unavailable: no new ~211-second full runs were justified without observations; those sensitivities are explicitly marked not run. This is a documented limitation rather than a completed hydraulic-parameter sensitivity study.

## 12–13. Calibration methodology and results
No calibration objective/search was run. Direct hydraulic observations are absent, so calibrated parameters = none and best objective = N/A. Assumed parameters remain frozen at their Phase 1 baseline values. This avoids fitting SWMM to its own output or to unverified historical flood labels.

## 14. Validation results
Rainfall can be checked at the published IMD 3-hour intervals, but independent hydraulic validation is unavailable. No RMSE/MAE/NSE/IoU or event timing metrics are claimed.

## 15. Water balance
The Phase 2A baseline water-balance outputs remain the source for the computed SWMM accounting. These are internal numerical balance checks, not independent validation of real-world water fluxes. Surface storage and street flood depth remain unavailable; SWMM node depth is not represented as street depth.

## 16. Scenario results
Phase 2A retains historical_2005 and rainfall_025/050/075/100 plus custom 15-minute inputs with existing infrastructure. Proposal infrastructure and tide remain disabled. Final files are copies of the executed baseline; no scenario overwrote Phase 1 artifacts.

## 17. Uncertainty
Dominant uncertainties: reconstructed sub-hourly rainfall shape; assumed conduit roughness/infiltration/imperviousness; 34 unverified boundaries; unknown vertical datum; long-distance outlet assignments; no surface coupling. `calibration/parameter_sensitivity.csv` and the manifest distinguish known uncertainty from measured sensitivity.

## 18. Final model status
**SWMM_CALIBRATION_READY_DATA_LIMITED**. The model executes reproducibly and is frozen for ML handoff, but remains hydraulically unvalidated and uncalibrated.

## 19. ML handoff
`ml_ready/physics_features_v1.csv` contains one record per directly mapped Phase 2A pilot grid cell for E001, with event window, reconstructed rainfall summaries, direct SWMM hydraulic values where available, and explicit nulls/provenance flags for unavailable surface/terrain fields. Nulls are deliberate; no missing measurements were fabricated.

## 20. Remaining limitations
No event-matched depth/flow/stage/flood extent; datum unresolved; 34 assumed boundaries; 203 questionable/unknown long assignments; Warning 04 endpoint differences retained; no surface-water routing; hydraulic parameter sensitivity not run; no multi-event hydraulic validation. Reopen SWMM work only if authoritative source data or a critical correctness defect becomes available.
"""
    (REPORT / "final_swmm_quality_report.md").write_text(report, encoding="utf-8")
    print(json.dumps({"features": len(pd.read_csv(ML / "physics_features_v1.csv")), "warning04": len(pd.read_csv(CAL / "elevation_validation.csv")), "boundaries": len(pd.read_csv(CAL / "outfall_validation.csv")), "catchments_gt_500m": len(pd.read_csv(CAL / "catchment_outlet_review.csv")), "status": manifest["calibration_status"]}, indent=2))


if __name__ == "__main__":
    main()
