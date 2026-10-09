"""Build reusable Phase 2A baseline artifacts from the preserved Phase 1 SWMM OUT."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.swmm_physics import PHASE1, PHASE2, SwmmScenario, scenario_hash, write_phase2_artifacts


def write_comparison() -> None:
    metrics = json.loads((PHASE1 / "phase1b" / "reports" / "scenario_metrics.json").read_text(encoding="utf-8"))
    baseline = next(x for x in metrics if x["scenario"] == "baseline_100pct")
    rows = []
    for item in metrics:
        if item is baseline or not item["scenario"].startswith("rainfall_"):
            continue
        rows.append({
            "scenario_a": baseline["scenario"], "scenario_b": item["scenario"],
            "rainfall_depth_difference_mm": item["rainfall_mm"] - baseline["rainfall_mm"],
            "peak_depth_difference_m": item["node_max_depth_m"] - baseline["node_max_depth_m"],
            "flooded_area_difference_km2": None,
            "flood_duration_difference_minutes": None,
            "time_to_flood_difference_minutes": None,
            "peak_drainage_flow_difference_m3s": item["max_flow_cms"] - baseline["max_flow_cms"],
            "comparison_status": "HYDRAULIC_METRICS_ONLY; flood area, grid depth and duration unavailable without surface coupling",
        })
    pd.DataFrame(rows).to_csv(PHASE2 / "results" / "scenario_comparison.csv", index=False)


def write_report(result: dict) -> None:
    mapping = result["mapping"]
    baseline = result["baseline"]
    report = f"""# TERRA05 Phase 2A — Physics Engine

## Engine

- SWMM version: EPA SWMM 5.2.4 (existing Phase 1 baseline output reused).
- Routing: Dynamic Wave.
- Model: Existing-only Ward L/Mithi pilot; 3,314 conduits, 3,269 source nodes, 34 computational boundary objects and 1,516 subcatchments.
- Baseline solver execution: 210.925 seconds (Phase 1 record); Phase 2A extraction reuses the saved `.out` and does not rerun SWMM.

## Spatial physics

- Citywide 100 m grid cells mapped to nearest hydraulic objects: {mapping['grid_cell_count']:,}.
- Cells with direct pilot subcatchment assignment: {mapping['hydraulic_coverage_cell_count']:,}; this is the modeled SWMM grid support.
- Pilot nodes/conduits/subcatchments mapped: {mapping['nodes_mapped']:,}/{mapping['conduits_mapped']:,}/{mapping['subcatchments_assigned']:,}.
- Grid nearest-node depth is retained only as `HYDRAULIC_PROXY`. `surface_water_depth_m` and surface storage are null because no validated surface coupling exists.
- SWMM runoff is a direct drainage input, node flooding is direct SWMM overflow, and nearest-object grid interpolation is an engineering proxy. No SWMM runoff is added to the fast surface model.

## Scenarios and execution

Scenario definitions support `historical_2005` and the 0.25, 0.50, 0.75, and 1.00 rainfall multipliers with existing infrastructure and tide disabled. Proposal modes and low/normal/high/very-high tide settings are represented in configuration but rejected for execution until their asset/boundary data is verified. SWMM submissions are asynchronous, deterministic-hash cached, and reuse completed Phase 1B outputs for the precomputed multipliers. Other supported multipliers run in an isolated directory. Fast 2D simulation remains available through `/api/v1/simulation/run`.

SWMM API: `POST /api/v1/simulation/swmm` submits a job; `GET /api/v1/simulation/swmm/{{simulation_id}}` returns status; `GET /api/v1/simulation/swmm/{{simulation_id}}/results/{{table}}` retrieves a normalized table; `POST /api/v1/simulation/swmm/compare` compares completed runs. Requests may supply a 15-minute `rainfall_profile_mm` with up to 108 intervals.

## Validation

- **ENGINE STATUS:** executable; Dynamic Wave output extracted with full 15-minute reporting time series.
- **HYDRAULIC VALIDATION STATUS:** hydraulically unvalidated; current baseline max node depth {baseline['max_node_depth_m']:.3f} m and max conduit velocity {baseline['max_conduit_velocity_ms']:.3f} m/s need engineering review.
- **OBSERVATIONAL CALIBRATION STATUS:** not performed.
- Tide is disabled in the SWMM scenario engine. Fast mode no longer converts tide labels into hidden drainage-capacity scaling.
- Flood state thresholds are configurable engineering thresholds, not calibrated municipal warning thresholds.

## Phase boundary

The surface engine remains a separate Mode A approximation. SWMM is Mode B. Mode C hybrid coupling is intentionally not inferred from nearest-node depth or duplicated runoff; it requires validated surface exchange locations/capacities and explicit volume-transfer bookkeeping. Continue to Phase 2B observational validation and calibration before treating results as authoritative flood predictions.
"""
    (PHASE2 / "reports" / "phase2a_final_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    result = write_phase2_artifacts()
    write_comparison()
    write_report(result)
    scenario = SwmmScenario()
    manifest = {
        "scenario_hash": scenario_hash(scenario),
        "scenario": scenario.__dict__,
        "source_model": "data/swmm_phase1/models/terra05_wardL_2005.inp",
        "source_output": "data/swmm_phase1/baseline/baseline.out",
        "extraction_mode": "reuse existing SWMM output; full 15-minute results",
        "engine_version": "EPA SWMM 5.2.4",
        "validation_status": "ENGINE_EXECUTABLE_HYDRAULICALLY_UNVALIDATED",
        "result_directory": "data/swmm_phase2/results",
    }
    (PHASE2 / "manifests" / "historical_2005.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
