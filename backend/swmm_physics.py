"""Scenario-driven SWMM physics execution, extraction, spatial mapping and cache.

SWMM node heads/depths are hydraulic states. Grid surface depth remains null
until a validated surface coupling exists; nearest-object fields are explicitly
labelled HYDRAULIC_PROXY and are never reported as observed street flooding.
"""
from __future__ import annotations

import csv
import hashlib
import json
import logging
import math
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

LOGGER = logging.getLogger(__name__)
PHASE1 = Path(__file__).resolve().parents[1] / "data" / "swmm_phase1"
PHASE2 = Path(__file__).resolve().parents[1] / "data" / "swmm_phase2"
MODEL = PHASE1 / "models" / "terra05_wardL_2005.inp"
BASE_RPT = PHASE1 / "baseline" / "baseline.rpt"
BASE_OUT = PHASE1 / "baseline" / "baseline.out"
SWMM_EXE = Path(os.getenv("SWMM_EXE", r"C:\Program Files\EPA SWMM 5.2.4 (64-bit)\runswmm.exe"))
REPORT_INTERVAL_MINUTES = 15
FLOOD_THRESHOLDS_M = {"wet": 0.01, "minor": 0.15, "moderate": 0.30, "severe": 0.60, "extreme": 1.00}
PHYSICS_CONFIG_PATH = PHASE2 / "scenarios" / "physics_config.json"


def load_physics_config() -> dict[str, Any]:
    if PHYSICS_CONFIG_PATH.is_file():
        return json.loads(PHYSICS_CONFIG_PATH.read_text(encoding="utf-8"))
    return {"flood_state_thresholds_m": FLOOD_THRESHOLDS_M, "threshold_source": "CONFIGURED_ENGINEERING_THRESHOLD_NOT_CALIBRATED"}


@dataclass(frozen=True)
class SwmmScenario:
    scenario_id: str = "historical_2005"
    rainfall_multiplier: float = 1.0
    infrastructure_mode: str = "existing"
    tide_mode: str = "disabled"
    rainfall_profile_mm: tuple[float, ...] | None = None

    def validate(self) -> None:
        if not self.scenario_id or len(self.scenario_id) > 100:
            raise ValueError("scenario_id must be a non-empty string up to 100 characters")
        if not math.isfinite(self.rainfall_multiplier) or not 0.0 < self.rainfall_multiplier <= 5.0:
            raise ValueError("rainfall_multiplier must be greater than 0 and at most 5")
        if self.infrastructure_mode != "existing":
            raise ValueError("Only infrastructure_mode='existing' is currently supported")
        if self.tide_mode != "disabled":
            raise ValueError("Tide is disabled until physical receiving-water boundaries are verified")
        if self.rainfall_profile_mm is not None:
            if not 1 <= len(self.rainfall_profile_mm) <= 108:
                raise ValueError("Custom SWMM rainfall profile must contain 1 to 108 15-minute intervals")
            if any(not math.isfinite(float(x)) or float(x) < 0 for x in self.rainfall_profile_mm):
                raise ValueError("Custom rainfall intervals must be finite and non-negative")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def scenario_hash(scenario: SwmmScenario, model_path: Path = MODEL) -> str:
    scenario.validate()
    scenario_definition = asdict(scenario)
    scenario_definition.pop("scenario_id", None)
    payload = {
        "model_sha256": sha256_file(model_path),
        "rainfall_source_sha256": sha256_file(PHASE1 / "source" / "source_manifest.json"),
        "cache_schema": "terra05-swmm-scenario-v2-custom-profile-isolated",
        "scenario": scenario_definition,
        "physics_config": {**load_physics_config(), "report_interval_minutes": REPORT_INTERVAL_MINUTES, "grid_mapping": "nearest-object-v1", "tide_policy": "disabled-until-verified"},
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _read_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = ""
    for raw in text.splitlines():
        value = raw.strip()
        if value.startswith("[") and value.endswith("]"):
            current = value[1:-1].upper()
            sections.setdefault(current, [])
        elif current and value and not value.startswith(";"):
            sections[current].append(value)
    return sections


def read_rainfall_profile(model_path: Path = MODEL) -> list[tuple[str, str, float]]:
    profile = []
    for row in _read_sections(model_path.read_text(encoding="utf-8"))["TIMESERIES"]:
        fields = row.split()
        if fields[0] == "TS_2005_JULY26" and len(fields) == 4:
            profile.append((fields[1], fields[2], float(fields[3])))
    if len(profile) != 108:
        raise ValueError(f"Expected the 108-interval Phase 1 rainfall profile, found {len(profile)}")
    return profile


def make_scaled_inp(scenario: SwmmScenario, destination: Path, source: Path = MODEL) -> Path:
    scenario.validate()
    lines = source.read_text(encoding="utf-8").splitlines()
    changed = 0
    custom = list(scenario.rainfall_profile_mm or ())
    for index, line in enumerate(lines):
        fields = line.strip().split()
        if len(fields) == 4 and fields[0] == "TS_2005_JULY26":
            base_value = custom[changed] if scenario.rainfall_profile_mm is not None and changed < len(custom) else 0.0 if scenario.rainfall_profile_mm is not None else float(fields[-1])
            fields[-1] = f"{base_value * scenario.rainfall_multiplier:.6f}"
            lines[index] = " ".join(fields)
            changed += 1
    if changed != 108:
        raise ValueError(f"Expected to scale 108 rainfall intervals, scaled {changed}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return destination


def _weighted_state(depth: float) -> str:
    if depth < FLOOD_THRESHOLDS_M["wet"]: return "DRY"
    if depth < FLOOD_THRESHOLDS_M["minor"]: return "WET"
    if depth < FLOOD_THRESHOLDS_M["moderate"]: return "MINOR"
    if depth < FLOOD_THRESHOLDS_M["severe"]: return "MODERATE"
    if depth < FLOOD_THRESHOLDS_M["extreme"]: return "SEVERE"
    return "EXTREME"


def extract_node_flood_events(nodes: pd.DataFrame, interval_minutes: int = REPORT_INTERVAL_MINUTES) -> list[dict[str, Any]]:
    """Summarize first/peak flooding from timestamped direct SWMM node output."""
    events = []
    for node_id, group in nodes.groupby("node_id", sort=False):
        peak_depth_row = group.loc[group.node_depth_m.idxmax()]
        flooded = group[group.node_flooding_rate_m3s > 1e-9]
        if flooded.empty:
            continue
        peak_row = flooded.loc[flooded.node_flooding_m3.idxmax()]
        events.append({"object_type": "node", "node_id": node_id, "grid_id": None,
            "first_flood_time": flooded.timestamp.iloc[0], "peak_flood_time": peak_row.timestamp,
            "peak_depth_m": float(peak_depth_row.node_depth_m), "peak_flood_volume_m3": float(peak_row.node_flooding_m3),
            "total_flood_volume_m3": float(flooded.node_flooding_m3.sum()),
            "flood_duration_minutes": int(len(flooded) * interval_minutes),
            "event_basis": "DIRECT_SWMM_NODE_FLOODING", "surface_depth_m": None})
    return events


def nearest_object_mapping(grid_centroids, assets, id_col: str, output_id: str, distance_col: str) -> pd.DataFrame:
    """Map each grid centroid to one nearest object in a common projected CRS."""
    joined = __import__("geopandas").sjoin_nearest(grid_centroids, assets[[id_col, "geometry"]], how="left", distance_col=distance_col)
    joined = joined.sort_values(distance_col).drop_duplicates("grid_id")
    return pd.DataFrame({"grid_id": joined.grid_id, output_id: joined[id_col].astype("string"), distance_col: joined[distance_col].astype(float)})


def extract_output(out_path: Path, scenario: SwmmScenario, simulation_id: str, result_dir: Path, grid_mapping_path: Path | None = None) -> dict[str, Any]:
    """Extract full SWMM reporting time series and normalized object tables."""
    from pyswmm import Output
    from swmm.toolkit.shared_enum import LinkAttribute, NodeAttribute, SubcatchAttribute

    result_dir.mkdir(parents=True, exist_ok=True)
    node_rows: list[dict[str, Any]] = []
    conduit_rows: list[dict[str, Any]] = []
    sub_rows: list[dict[str, Any]] = []
    if out_path.resolve() == BASE_OUT.resolve():
        # Reuse Phase 1's verified extraction rather than reparsing its binary OUT.
        existing_nodes = pd.read_csv(PHASE1 / "results" / "node_results.csv", dtype={"node_id": str, "source_node_id": str})
        existing_links = pd.read_csv(PHASE1 / "results" / "conduit_results.csv")
        existing_subs = pd.read_csv(PHASE1 / "results" / "subcatchment_results.csv")
        for row in existing_nodes.itertuples():
            rate = float(row.flooding_cms)
            node_rows.append({"simulation_id": simulation_id, "scenario_id": scenario.scenario_id, "timestamp": row.timestamp,
                "node_id": row.node_id, "node_depth_m": float(row.depth_m), "node_head_m": float(row.head_m),
                "node_flooding_rate_m3s": rate, "node_flooding_m3": rate * REPORT_INTERVAL_MINUTES * 60,
                "node_inflow_m3s": float(row.total_inflow_cms), "data_provenance": "DIRECT_SWMM; reused Phase 1 extraction"})
        for row in existing_links.itertuples():
            conduit_rows.append({"simulation_id": simulation_id, "scenario_id": scenario.scenario_id, "timestamp": row.timestamp,
                "conduit_id": row.conduit_id, "conduit_flow_m3s": float(row.flow_cms),
                "conduit_velocity_ms": float(row.velocity_m_s), "conduit_depth_m": float(row.depth_m),
                "capacity_ratio": float(row.capacity_ratio), "data_provenance": "DIRECT_SWMM; reused Phase 1 extraction"})
        for row in existing_subs.itertuples():
            rain_rate, inf_rate = float(row.rainfall_mm_hr), float(row.infiltration_mm_hr)
            sub_rows.append({"simulation_id": simulation_id, "scenario_id": scenario.scenario_id, "timestamp": row.timestamp,
                "subcatchment_id": row.subcatchment_id, "rainfall_mm": rain_rate * REPORT_INTERVAL_MINUTES / 60,
                "rainfall_rate_mm_hr": rain_rate, "infiltration_mm": inf_rate * REPORT_INTERVAL_MINUTES / 60,
                "surface_runoff_m3s": float(row.runoff_cms), "data_provenance": "DIRECT_SWMM; reused Phase 1 extraction"})
    else:
        with Output(str(out_path)) as output:
            times = list(output.times)
            for node_id in output.nodes:
                depth = output.node_series(node_id, NodeAttribute.INVERT_DEPTH)
                head = output.node_series(node_id, NodeAttribute.HYDRAULIC_HEAD)
                flood = output.node_series(node_id, NodeAttribute.FLOODING_LOSSES)
                inflow = output.node_series(node_id, NodeAttribute.TOTAL_INFLOW)
                for stamp in times:
                    rate = float(flood.get(stamp, 0.0))
                    node_rows.append({"simulation_id": simulation_id, "scenario_id": scenario.scenario_id,
                        "timestamp": stamp.isoformat(), "node_id": node_id,
                        "node_depth_m": float(depth.get(stamp, 0.0)), "node_head_m": float(head.get(stamp, 0.0)),
                        "node_flooding_rate_m3s": rate, "node_flooding_m3": rate * REPORT_INTERVAL_MINUTES * 60,
                        "node_inflow_m3s": float(inflow.get(stamp, 0.0)), "data_provenance": "DIRECT_SWMM"})
            for conduit_id in output.links:
                flow = output.link_series(conduit_id, LinkAttribute.FLOW_RATE)
                velocity = output.link_series(conduit_id, LinkAttribute.FLOW_VELOCITY)
                depth = output.link_series(conduit_id, LinkAttribute.FLOW_DEPTH)
                capacity = output.link_series(conduit_id, LinkAttribute.CAPACITY)
                for stamp in times:
                    conduit_rows.append({"simulation_id": simulation_id, "scenario_id": scenario.scenario_id,
                        "timestamp": stamp.isoformat(), "conduit_id": conduit_id,
                        "conduit_flow_m3s": float(flow.get(stamp, 0.0)), "conduit_velocity_ms": float(velocity.get(stamp, 0.0)),
                        "conduit_depth_m": float(depth.get(stamp, 0.0)), "capacity_ratio": float(capacity.get(stamp, 0.0)),
                        "data_provenance": "DIRECT_SWMM"})
            for sub_id in output.subcatchments:
                rain = output.subcatch_series(sub_id, SubcatchAttribute.RAINFALL)
                infiltration = output.subcatch_series(sub_id, SubcatchAttribute.INFIL_LOSS)
                runoff = output.subcatch_series(sub_id, SubcatchAttribute.RUNOFF_RATE)
                for stamp in times:
                    rain_rate = float(rain.get(stamp, 0.0))
                    inf_rate = float(infiltration.get(stamp, 0.0))
                    runoff_rate = float(runoff.get(stamp, 0.0))
                    sub_rows.append({"simulation_id": simulation_id, "scenario_id": scenario.scenario_id,
                        "timestamp": stamp.isoformat(), "subcatchment_id": sub_id,
                        "rainfall_mm": rain_rate * REPORT_INTERVAL_MINUTES / 60,
                        "rainfall_rate_mm_hr": rain_rate, "infiltration_mm": inf_rate * REPORT_INTERVAL_MINUTES / 60,
                        "surface_runoff_m3s": runoff_rate, "data_provenance": "DIRECT_SWMM"})
    nodes = pd.DataFrame(node_rows)
    conduits = pd.DataFrame(conduit_rows)
    subcatchments = pd.DataFrame(sub_rows)
    nodes.to_csv(result_dir / "node_physics_timeseries.csv", index=False)
    conduits.to_csv(result_dir / "conduit_physics_timeseries.csv", index=False)
    subareas = pd.read_csv(PHASE1 / "network" / "pilot_subcatchments.csv")[["swmm_id", "grid_id", "area_ha"]]
    subcatchments = subcatchments.merge(subareas, left_on="subcatchment_id", right_on="swmm_id", how="left")
    subcatchments["surface_runoff_mm"] = subcatchments.surface_runoff_m3s * REPORT_INTERVAL_MINUTES * 60 / (subcatchments.area_ha.fillna(1.0) * 10000) * 1000
    subcatchments.to_csv(result_dir / "subcatchment_physics_timeseries.csv", index=False)

    node_events = extract_node_flood_events(nodes)

    link_metrics = conduits.groupby("conduit_id", as_index=False).agg(
        max_flow_m3s=("conduit_flow_m3s", lambda x: float(x.abs().max())),
        max_velocity_ms=("conduit_velocity_ms", lambda x: float(x.abs().max())),
        max_depth_m=("conduit_depth_m", "max"),
        duration_surcharged_minutes=("capacity_ratio", lambda x: int((x >= 0.99).sum() * REPORT_INTERVAL_MINUTES)),
        full_flow_duration_minutes=("capacity_ratio", lambda x: int((x >= 1.0).sum() * REPORT_INTERVAL_MINUTES)))
    peak_idx = conduits.groupby("conduit_id").conduit_flow_m3s.apply(lambda x: x.abs().idxmax())
    peak_times = conduits.loc[peak_idx, ["conduit_id", "timestamp"]].rename(columns={"timestamp": "time_of_peak_flow"})
    link_metrics = link_metrics.merge(peak_times, on="conduit_id", how="left")
    link_metrics["validation_status"] = "ENGINE_EXECUTABLE_HYDRAULICALLY_UNVALIDATED"
    link_metrics.to_csv(result_dir / "conduit_metrics.csv", index=False)

    subcatch_metrics = subcatchments.groupby("subcatchment_id", as_index=False).agg(
        rainfall_total_mm=("rainfall_mm", "sum"), infiltration_total_mm=("infiltration_mm", "sum"),
        peak_runoff_m3s=("surface_runoff_m3s", "max"))
    subcatchments["runoff_volume_m3"] = subcatchments.surface_runoff_m3s * REPORT_INTERVAL_MINUTES * 60
    runoff_vol = subcatchments.groupby("subcatchment_id").runoff_volume_m3.sum()
    subcatch_metrics["runoff_total_m3"] = subcatch_metrics.subcatchment_id.map(runoff_vol).fillna(0)
    subcatch_metrics = subcatch_metrics.merge(subareas, left_on="subcatchment_id", right_on="swmm_id", how="left")
    area_m2 = subcatch_metrics.area_ha.fillna(1.0) * 10000
    subcatch_metrics["runoff_total_mm"] = subcatch_metrics.runoff_total_m3 / area_m2 * 1000
    subcatch_metrics["runoff_coefficient"] = subcatch_metrics.runoff_total_mm / subcatch_metrics.rainfall_total_mm.replace(0, float("nan"))
    subcatch_metrics["time_to_peak"] = subcatch_metrics.subcatchment_id.map(
        subcatchments.loc[subcatchments.groupby("subcatchment_id").surface_runoff_m3s.idxmax()].set_index("subcatchment_id").timestamp)
    subcatch_metrics["data_provenance"] = "DIRECT_SWMM; runoff depth derived from volume / source area"
    subcatch_metrics.to_csv(result_dir / "subcatchment_metrics.csv", index=False)

    if grid_mapping_path is not None:
        mapping = pd.read_csv(grid_mapping_path)
        pilot_map = mapping[mapping.subcatchment_id.notna()].copy()
        sub_rates = subcatchments.drop(columns=["grid_id", "swmm_id"], errors="ignore")
        grid = pilot_map.merge(sub_rates, left_on="subcatchment_id", right_on="subcatchment_id", how="inner")
        node_time = nodes.rename(columns={"node_id": "nearest_node", "node_depth_m": "nearest_node_depth_m", "node_head_m": "nearest_node_head_m", "node_flooding_m3": "nearest_node_flooding_m3"})
        grid = grid.merge(node_time[["timestamp", "nearest_node", "nearest_node_depth_m", "nearest_node_head_m", "nearest_node_flooding_m3"]], on=["timestamp", "nearest_node"], how="left")
        conduit_time = conduits.rename(columns={"conduit_id": "nearest_conduit", "conduit_flow_m3s": "nearest_conduit_flow_m3s", "conduit_velocity_ms": "nearest_conduit_velocity_ms", "capacity_ratio": "nearest_conduit_capacity_ratio"})
        grid = grid.merge(conduit_time[["timestamp", "nearest_conduit", "nearest_conduit_flow_m3s", "nearest_conduit_velocity_ms", "nearest_conduit_capacity_ratio"]], on=["timestamp", "nearest_conduit"], how="left")
        grid["surface_water_depth_m"] = float("nan")
        grid["surface_water_volume_m3"] = float("nan")
        grid["drainage_inflow_m3s"] = grid.surface_runoff_m3s
        grid["drainage_outflow_m3s"] = grid.nearest_conduit_flow_m3s.abs()
        grid["drainage_pressure"] = grid.nearest_conduit_capacity_ratio
        grid["drainage_inflow_provenance"] = "DIRECT_SWMM_SUBCATCHMENT_RUNOFF"
        grid["drainage_outflow_provenance"] = "HYDRAULIC_PROXY; nearest conduit flow is not a verified inlet exchange"
        grid["drainage_pressure_provenance"] = "HYDRAULIC_PROXY; nearest conduit capacity ratio"
        grid["flood_state"] = "UNCLASSIFIED_NO_SURFACE_COUPLING"
        grid["flood_state_threshold_source"] = "CONFIGURED_ENGINEERING_THRESHOLD; thresholds apply to depth only after surface coupling"
        grid["surface_water_provenance"] = "NOT_AVAILABLE"
        grid["nearest_node_provenance"] = "HYDRAULIC_PROXY; SWMM node depth is not street flood depth"
        grid["surface_runoff_provenance"] = "DIRECT_SWMM"
        keep = ["simulation_id", "scenario_id", "timestamp", "grid_id", "node_id", "conduit_id", "subcatchment_id", "rainfall_mm", "surface_runoff_mm", "drainage_pressure", "nearest_node_depth_m", "nearest_node_flooding_m3", "nearest_conduit_flow_m3s", "surface_water_depth_m", "surface_water_volume_m3", "drainage_inflow_m3s", "drainage_outflow_m3s", "flood_state", "flood_state_threshold_source", "nearest_node_provenance", "surface_water_provenance", "surface_runoff_provenance"]
        grid = grid.rename(columns={"surface_runoff_m3s": "surface_runoff_rate_m3s"})
        grid["surface_runoff_mm"] = grid.surface_runoff_rate_m3s * 900 / (grid.area_ha.fillna(1.0) * 10000) * 1000
        grid["node_id"] = grid.nearest_node
        grid["conduit_id"] = grid.nearest_conduit
        grid.to_csv(result_dir / "grid_physics_timeseries.csv", index=False)
        grid_events = []
        for grid_id, group in grid.groupby("grid_id", sort=False):
            proxy_peak = group.loc[group.nearest_node_depth_m.idxmax()]
            overflow = group[group.nearest_node_flooding_m3 > 0]
            grid_events.append({"grid_id": int(grid_id), "first_wet_timestamp": None, "first_flood_timestamp": None,
                "peak_timestamp": proxy_peak.timestamp, "peak_depth_m": None,
                "nearest_node_peak_depth_proxy_m": float(proxy_peak.nearest_node_depth_m),
                "flood_duration_minutes": None,
                "first_hydraulic_overflow_proxy_timestamp": overflow.timestamp.iloc[0] if not overflow.empty else None,
                "event_basis": "HYDRAULIC_PROXY; no surface-water depth coupling"})
        pd.DataFrame(grid_events).to_csv(result_dir / "grid_event_metrics.csv", index=False)
        node_events.extend(_write_grid_flood_events(grid, node_events, result_dir))

    pd.DataFrame(node_events).to_csv(result_dir / "flood_events.csv", index=False)
    rpt_path = BASE_RPT if out_path == BASE_OUT else out_path.with_suffix(".rpt")
    quality = make_quality_report(out_path, rpt_path, scenario, node_rows, conduit_rows, sub_rows)
    (result_dir / "physics_quality_report.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
    water = read_water_balance(rpt_path)
    water.update({"simulation_id": simulation_id, "scenario_id": scenario.scenario_id,
        "rainfall_multiplier": scenario.rainfall_multiplier,
        "counting_contract": "SWMM runoff is the runoff inflow to drainage and is reported separately; do not add drainage inflow to rainfall runoff again. SWMM flooding is overflow loss from the drainage system. Surface storage/depth is unavailable without a coupled 2D surface model."})
    pd.DataFrame([water]).to_csv(result_dir / "physics_water_balance.csv", index=False)
    summaries = {
        "engine": "swmm", "simulation_id": simulation_id, "scenario_id": scenario.scenario_id,
        "rainfall_multiplier": scenario.rainfall_multiplier,
        "max_node_depth_m": float(nodes.node_depth_m.max()),
        "max_conduit_velocity_ms": float(conduits.conduit_velocity_ms.abs().max()),
        "peak_drainage_flow_m3s": float(conduits.conduit_flow_m3s.abs().max()),
        "flooded_node_count": int((nodes.groupby("node_id").node_flooding_rate_m3s.max() > 1e-9).sum()),
        "grid_flooded_area_km2": None,
        "validation_status": quality["overall_status"],
        "result_paths": {p.stem: p.name for p in result_dir.glob("*.csv")},
    }
    (result_dir / "simulation_summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    return {"quality": quality, "summary": summaries, "water_balance": water}


def _write_grid_flood_events(grid: pd.DataFrame, node_events: list[dict[str, Any]], result_dir: Path) -> list[dict[str, Any]]:
    """Allocate each overflowing node once to its closest pilot grid as a proxy."""
    events = pd.DataFrame(node_events)
    if events.empty:
        return []
    pairs = grid[["grid_id", "nearest_node", "node_distance_m"]].drop_duplicates()
    pairs = pairs.sort_values("node_distance_m").drop_duplicates("nearest_node")
    mapped = events.drop(columns=["grid_id"], errors="ignore").merge(pairs, left_on="node_id", right_on="nearest_node", how="inner")
    mapped["object_type"] = "grid_hydraulic_proxy"
    mapped["nearest_node_peak_depth_proxy_m"] = mapped["peak_depth_m"]
    mapped["allocated_node_overflow_volume_proxy_m3"] = mapped["total_flood_volume_m3"]
    mapped["node_flood_duration_proxy_minutes"] = mapped["flood_duration_minutes"]
    mapped["peak_depth_m"] = float("nan")
    mapped["peak_flood_volume_m3"] = float("nan")
    mapped["total_flood_volume_m3"] = float("nan")
    mapped["flood_duration_minutes"] = pd.NA
    mapped["event_basis"] = "HYDRAULIC_PROXY; direct node overflow assigned to nearest grid cell once"
    mapped["nearest_node_peak_depth_proxy_m"] = mapped["peak_depth_m"]
    mapped["allocated_node_overflow_volume_proxy_m3"] = mapped["total_flood_volume_m3"]
    mapped["node_flood_duration_proxy_minutes"] = mapped["flood_duration_minutes"]
    mapped["peak_depth_m"] = float("nan")
    mapped["peak_flood_volume_m3"] = float("nan")
    mapped["total_flood_volume_m3"] = float("nan")
    mapped["flood_duration_minutes"] = pd.NA
    mapped["event_basis"] = "HYDRAULIC_PROXY; direct node overflow assigned to nearest grid cell once"
    mapped["grid_surface_depth_m"] = float("nan")
    mapped["spatial_allocation"] = "overflow node assigned once to nearest pilot cell; not a surface flood depth"
    mapped.to_csv(result_dir / "grid_flood_events_proxy.csv", index=False)
    return mapped.to_dict(orient="records")


def read_water_balance(rpt_path: Path) -> dict[str, Any]:
    text = rpt_path.read_text(encoding="utf-8", errors="replace")
    metrics = {}
    volume_lines = {
        "rainfall_volume_ML": "Total Precipitation",
        "infiltration_volume_ML": "Infiltration Loss",
        "surface_runoff_volume_ML": "Surface Runoff",
    }
    for key, label in volume_lines.items():
        hit = re.search(rf"{re.escape(label)}\s*\.*\s*([-+\d.]+)\s+([-+\d.]+)", text, flags=re.I)
        metrics[key] = float(hit.group(1)) * 10 if hit else None  # SWMM first-column unit is hectare-m; 1 ha-m = 10 ML.
    patterns = {
        "total_rainfall_mm": r"Total Precipitation\s*\.*\s*[-+\d.]+\s+([-+\d.]+)",
        "total_infiltration_mm": r"Infiltration Loss\s*\.*\s*[-+\d.]+\s+([-+\d.]+)",
        "total_surface_runoff_mm": r"Surface Runoff\s*\.*\s*[-+\d.]+\s+([-+\d.]+)",
        "drainage_inflow_ML": r"Wet Weather Inflow\s*\.*\s*[-+\d.]+\s+([-+\d.]+)",
        "drainage_outflow_ML": r"External Outflow\s*\.*\s*[-+\d.]+\s+([-+\d.]+)",
        "swmm_flooding_ML": r"Flooding Loss\s*\.*\s*[-+\d.]+\s+([-+\d.]+)",
        "final_drainage_storage_ML": r"Final Stored Volume\s*\.*\s*[-+\d.]+\s+([-+\d.]+)",
    }
    for key, pattern in patterns.items():
        hit = re.search(pattern, text, flags=re.I)
        metrics[key] = float(hit.group(1)) if hit else None
    errs = [float(x) for x in re.findall(r"Continuity Error\s*\(%\)\s*\.+\s*([-+]?\d+(?:\.\d+)?)", text)]
    metrics["continuity_error_percent"] = errs
    metrics["surface_storage_ML"] = None
    metrics["surface_storage_note"] = "Not available from SWMM 1D output; no surface coupling was run"
    return metrics


def make_quality_report(out_path: Path, rpt_path: Path, scenario: SwmmScenario, node_rows: list[dict[str, Any]], conduit_rows: list[dict[str, Any]], sub_rows: list[dict[str, Any]]) -> dict[str, Any]:
    link_map = json.loads((PHASE1 / "network" / "connectivity_report.json").read_text(encoding="utf-8"))
    rpt = rpt_path.read_text(encoding="utf-8", errors="replace")
    continuity = [float(x) for x in re.findall(r"Continuity Error\s*\(%\)\s*\.+\s*([-+]?\d+(?:\.\d+)?)", rpt)]
    warning_ids = re.findall(r"\bWARNING\s+(\d+):", rpt, flags=re.I)
    warnings = {key: warning_ids.count(key) for key in sorted(set(warning_ids))}
    one_sub = sorted({x["subcatchment_id"] for x in sub_rows})[0]
    rainfall_total = sum(x["rainfall_mm"] for x in sub_rows if x["subcatchment_id"] == one_sub)
    expected_rainfall = sum(scenario.rainfall_profile_mm) * scenario.rainfall_multiplier if scenario.rainfall_profile_mm is not None else 944.2 * scenario.rainfall_multiplier
    max_depth = max((float(x["node_depth_m"]) for x in node_rows), default=0.0)
    max_velocity = max((abs(float(x["conduit_velocity_ms"])) for x in conduit_rows), default=0.0)
    return {
        "swmm_runtime_ok": out_path.is_file(),
        "continuity_ok": bool(continuity) and max(abs(x) for x in continuity) < 1,
        "continuity_error_percent": continuity,
        "topology_ok": len(node_rows) > 0 and len(conduit_rows) > 0 and link_map.get("existing_component_count", 0) > 0,
        "rainfall_ok": len(sub_rows) > 0 and abs(rainfall_total - expected_rainfall) < 1.0,
        "rainfall_total_mm": rainfall_total,
        "elevation_validation_status": "UNVERIFIED; datum and cover assumptions remain",
        "warning04_count": int(warnings.get("04", 0)),
        "boundary_validation_status": "UNVERIFIED; pilot boundaries are computational, physical outfalls/tide not confirmed",
        "catchment_validation_status": "UNVERIFIED; all outlet IDs resolve, 203 outlets exceed 500 m",
        "hydraulic_sanity_status": "REVIEW_REQUIRED" if max_depth > 10 or max_velocity > 10 else "WITHIN_CONFIGURED_SANITY_LIMITS",
        "overall_status": "ENGINE_EXECUTABLE_HYDRAULICALLY_UNVALIDATED",
        "validation_status": "OBSERVATION_CALIBRATION_NOT_PERFORMED",
        "warning_counts": warnings,
        "flood_threshold_source": "CONFIGURED_ENGINEERING_THRESHOLD; not calibrated municipal warning thresholds",
    }


def build_grid_mapping(output_path: Path = PHASE2 / "spatial" / "grid_hydraulic_mapping.csv") -> dict[str, Any]:
    """Map the city grid to nearest hydraulic objects in projected metres."""
    import geopandas as gpd

    out_geo = output_path.with_suffix(".geojson")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    grid = gpd.read_file(PHASE1.parent / "processed" / "flood_grid_100m.geojson")
    if grid.crs is None:
        raise ValueError("City grid has no CRS")
    if grid.crs.to_string() != "EPSG:32643":
        grid = grid.to_crs("EPSG:32643")
    grid = grid[["grid_id", "ward", "geometry"]].copy()
    centroids = gpd.GeoDataFrame(grid[["grid_id", "ward"]].copy(), geometry=grid.geometry.centroid, crs=grid.crs)

    def nearest(asset_path: Path, id_col: str, out_id: str, dist_col: str) -> pd.DataFrame:
        assets = gpd.read_file(asset_path)
        if assets.crs is None:
            raise ValueError(f"Hydraulic asset has no CRS: {asset_path}")
        assets = assets.to_crs(grid.crs)[[id_col, "geometry"]].copy()
        return nearest_object_mapping(centroids, assets, id_col, out_id, dist_col)

    node_map = nearest(PHASE1 / "network" / "pilot_nodes.geojson", "swmm_id", "nearest_node", "node_distance_m")
    conduit_map = nearest(PHASE1 / "network" / "pilot_conduits.geojson", "swmm_id", "nearest_conduit", "conduit_distance_m")
    sub_map = nearest(PHASE1 / "network" / "pilot_subcatchments.geojson", "swmm_id", "nearest_subcatchment", "subcatchment_distance_m")
    table = pd.DataFrame(grid.drop(columns="geometry"))
    for item in (node_map, conduit_map, sub_map):
        table = table.merge(item, on="grid_id", how="left")
    exact = pd.read_csv(PHASE1 / "network" / "pilot_subcatchments.csv")[["grid_id", "swmm_id", "area_ha"]].rename(columns={"swmm_id": "subcatchment_id", "area_ha": "subcatchment_area_ha"})
    table = table.merge(exact, on="grid_id", how="left")
    table["subcatchment_area_fraction"] = (table.subcatchment_area_ha / 1.0).clip(upper=1).fillna(0.0)
    table["node_influence_weight"] = 1 / (1 + table.node_distance_m / 100)
    table["conduit_influence_weight"] = 1 / (1 + table.conduit_distance_m / 100)
    table["hydraulic_coverage"] = table.subcatchment_id.notna()
    table["mapping_classification"] = table.hydraulic_coverage.map({True: "PILOT_SUBCATCHMENT_ASSIGNED", False: "NEAREST_HYDRAULIC_PROXY_OUTSIDE_PILOT"})
    table["mapping_provenance"] = table.hydraulic_coverage.map({True: "DIRECT_GRID_TO_SWMM_SUBCATCHMENT; nearest hydraulic objects are proxies", False: "NEAREST_OBJECT_PROXY; no SWMM catchment covers this cell"})
    table.to_csv(output_path, index=False)
    grid_out = grid.merge(table.drop(columns=["ward"], errors="ignore"), on="grid_id", how="left")
    grid_out.to_crs("EPSG:4326").to_file(out_geo, driver="GeoJSON")
    report = {"grid_cell_count": int(len(table)), "hydraulic_coverage_cell_count": int(table.hydraulic_coverage.sum()),
        "nodes_mapped": int(table.nearest_node.nunique()), "conduits_mapped": int(table.nearest_conduit.nunique()),
        "subcatchments_assigned": int(table.subcatchment_id.notna().sum()), "pilot_node_count": 3269,
        "pilot_conduit_count": 3314, "pilot_subcatchment_count": 1516,
        "node_distance_m_quantiles": table.node_distance_m.quantile([0, .5, .95, .99, 1]).to_dict(),
        "conduit_distance_m_quantiles": table.conduit_distance_m.quantile([0, .5, .95, .99, 1]).to_dict(),
        "interpretation": "Citywide nearest objects are a locator only. Direct hydraulic coverage is limited to cells with an explicit pilot subcatchment. Node depth is never assigned as surface-water depth; nearest-node quantities are labeled HYDRAULIC_PROXY."}
    (PHASE2 / "spatial" / "spatial_mapping_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def write_uncertainty_ledger(path: Path) -> None:
    rows = [
        ("U01", "vertical datum", "DEM metadata / repository offset", "Node ground and cover elevations may be shifted", "UNVERIFIED"),
        ("U02", "node elevation", "DEM-derived rim and source inverts", "Affects surcharge and node flooding", "UNVERIFIED"),
        ("U03", "36 Warning 04 conduits", "Source conduit endpoint records", "SWMM substitutes minimum slope for hydraulic calculations", "SOURCE MATCHED; ENGINEERING REVIEW REQUIRED"),
        ("U04", "physical outfalls", "Directed pilot network sinks", "Pilot boundaries may not be receiving-water outlets", "UNVERIFIED"),
        ("U05", "receiving water / tide", "No verified boundary-stage series", "Backwater is not represented; tide disabled", "DISABLED"),
        ("U06", "catchment routing", "Nearest existing-network node assignment", "Spatial runoff allocation may be misplaced", "UNVERIFIED"),
        ("U07", "203 distant catchment outlets", "Outlet distances over 500 m", "Runoff may enter network at a distant node", "REVIEW REQUIRED"),
        ("U08", "Manning roughness", "Shape-based engineering assumptions", "Controls conduit conveyance", "ASSUMED; NOT CALIBRATED"),
        ("U09", "Horton parameters", "MVP infiltration parameters", "Controls runoff generation", "ASSUMED; NOT CALIBRATED"),
        ("U10", "reconstructed rainfall", "Coarse historical totals interpolated to 15-minute steps", "Affects peak runoff timing/intensity", "RECONSTRUCTED; NOT OBSERVED AT 15 MINUTES"),
        ("U11", "missing inlet capacity", "No surveyed inlet/gully inventory", "Surface-to-sewer transfer capacity is unknown", "UNAVAILABLE"),
        ("U12", "surface depth coupling", "No calibrated 2D surface-SWMM coupling", "SWMM depth cannot represent street depth", "NOT IMPLEMENTED; OUTPUT NULL"),
    ]
    pd.DataFrame(rows, columns=["uncertainty_id", "parameter", "source", "impact", "status"]).to_csv(path, index=False)


class SwmmPhysicsService:
    """File-backed asynchronous jobs and deterministic cache for SWMM scenarios."""
    def __init__(self, root: Path = PHASE2, max_workers: int = 1):
        self.root = root
        self.jobs = root / "manifests" / "jobs"
        self.runs = root / "runs"
        self.jobs.mkdir(parents=True, exist_ok=True)
        self.runs.mkdir(parents=True, exist_ok=True)
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="terra05-swmm")
        self._futures: dict[str, Future] = {}
        self._lock = threading.Lock()

    def _job_path(self, simulation_id: str) -> Path:
        if not re.fullmatch(r"sim_[a-f0-9]{20}", simulation_id):
            raise LookupError("Unknown simulation_id")
        return self.jobs / f"{simulation_id}.json"

    def submit(self, scenario: SwmmScenario) -> dict[str, Any]:
        scenario.validate()
        digest = scenario_hash(scenario)
        simulation_id = f"sim_{digest[:20]}"
        path = self._job_path(simulation_id)
        with self._lock:
            if path.is_file():
                existing = json.loads(path.read_text(encoding="utf-8"))
                if existing.get("status") in {"queued", "running", "completed"}:
                    existing["cache_hit"] = True
                    return existing
            record = {"simulation_id": simulation_id, "scenario_id": scenario.scenario_id, "scenario_hash": digest,
                "engine": "swmm", "status": "queued", "cache_hit": False, "created_at": datetime.now(timezone.utc).isoformat(),
                "validation_status": "ENGINE_EXECUTABLE_HYDRAULICALLY_UNVALIDATED"}
            path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            future = self._executor.submit(self._run_job, scenario, simulation_id, digest)
            self._futures[simulation_id] = future
        return record

    def _run_job(self, scenario: SwmmScenario, simulation_id: str, digest: str) -> None:
        path = self._job_path(simulation_id)
        record = json.loads(path.read_text(encoding="utf-8"))
        record.update(status="running", started_at=datetime.now(timezone.utc).isoformat())
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        started = time.monotonic()
        run_dir = self.runs / digest
        run_dir.mkdir(parents=True, exist_ok=True)
        result_dir = run_dir / "results"
        try:
            input_path = make_scaled_inp(scenario, run_dir / "scenario.inp")
            # Scaled Phase 1B outputs only represent the original E001 hyetograph.
            # Never reuse them when a caller supplies a custom rainfall profile.
            cached = _phase1b_cached_run(scenario.rainfall_multiplier) if scenario.rainfall_profile_mm is None else None
            if cached is not None:
                rpt_path, out_path = cached
                execution = {"reused_existing_run": True, "source_report": str(rpt_path), "source_output": str(out_path), "runtime_seconds": 0.0}
            else:
                if not SWMM_EXE.is_file():
                    raise FileNotFoundError(f"EPA SWMM executable unavailable: {SWMM_EXE}")
                rpt_path, out_path = run_dir / "scenario.rpt", run_dir / "scenario.out"
                start = time.monotonic()
                proc = subprocess.run([str(SWMM_EXE), str(input_path), str(rpt_path), str(out_path)], capture_output=True, text=True, timeout=1800, cwd=run_dir)
                errors = re.findall(r"\bERROR\s+\d+:[^\r\n]*", rpt_path.read_text(encoding="utf-8", errors="replace"), re.I) if rpt_path.exists() else []
                if proc.returncode or errors or not out_path.is_file():
                    raise RuntimeError(f"SWMM failed (code {proc.returncode}): {errors or proc.stderr}")
                execution = {"reused_existing_run": False, "runtime_seconds": time.monotonic()-start, "return_code": proc.returncode}
            mapping_path = self.root / "spatial" / "grid_hydraulic_mapping.csv"
            if not mapping_path.is_file():
                build_grid_mapping(mapping_path)
            result = extract_output(out_path, scenario, simulation_id, result_dir, mapping_path)
            manifest = {"simulation_id": simulation_id, "scenario_hash": digest, "scenario": asdict(scenario),
                "event_id": "E001" if scenario.scenario_id == "historical_2005" else None,
                "scenario_id": scenario.scenario_id, "model_version": "terra05-swmm-v1.0.0",
                "input_hash": sha256_file(input_path),
                "model_sha256": sha256_file(input_path), "input_path": str(input_path), "execution": execution,
                "rainfall_hash": hashlib.sha256(json.dumps(list(scenario.rainfall_profile_mm) if scenario.rainfall_profile_mm is not None else read_rainfall_profile(), sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                "run_timestamp": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": time.monotonic()-started, "completed_at": datetime.now(timezone.utc).isoformat(),
                "result_dir": str(result_dir), **result}
            (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            record.update(status="completed", completed_at=manifest["completed_at"], summary=result["summary"], validation_status=result["quality"]["overall_status"], result_paths=result["summary"]["result_paths"])
        except Exception as exc:
            LOGGER.exception("SWMM scenario %s failed", simulation_id)
            record.update(status="failed", error=f"{type(exc).__name__}: {exc}", completed_at=datetime.now(timezone.utc).isoformat())
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    def status(self, simulation_id: str) -> dict[str, Any]:
        path = self._job_path(simulation_id)
        if not path.is_file():
            raise LookupError(f"Unknown simulation_id: {simulation_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def results(self, simulation_id: str, table: str) -> Path:
        status = self.status(simulation_id)
        if status["status"] != "completed":
            raise RuntimeError(f"Simulation is {status['status']}")
        allowed = {"grid_physics_timeseries.csv", "node_physics_timeseries.csv", "conduit_physics_timeseries.csv", "subcatchment_physics_timeseries.csv", "flood_events.csv", "grid_event_metrics.csv", "grid_flood_events_proxy.csv", "physics_water_balance.csv", "physics_quality_report.json", "simulation_summary.json"}
        if table not in allowed:
            raise LookupError("Unknown result table")
        path = self.runs / status["scenario_hash"] / "results" / table
        if not path.is_file() and status.get("scenario_hash") == scenario_hash(SwmmScenario()):
            path = self.root / "results" / table
        if not path.is_file():
            raise LookupError(f"Result table not found: {table}")
        return path

    def compare(self, first_id: str, second_id: str) -> dict[str, Any]:
        first, second = self.status(first_id), self.status(second_id)
        if first["status"] != "completed" or second["status"] != "completed":
            raise RuntimeError("Both simulations must be completed before comparison")
        a, b = first["summary"], second["summary"]
        row = {"scenario_a": first_id, "scenario_b": second_id,
            "peak_depth_difference_m": b["max_node_depth_m"] - a["max_node_depth_m"],
            "flooded_area_difference_km2": None,
            "flood_duration_difference_minutes": None,
            "time_to_flood_difference_minutes": None,
            "peak_drainage_flow_difference_m3s": b["peak_drainage_flow_m3s"] - a["peak_drainage_flow_m3s"],
            "comparison_status": "HYDRAULIC_METRICS_ONLY; surface area/duration unavailable without surface coupling"}
        comparisons = self.root / "results" / "scenario_comparison.csv"
        comparisons.parent.mkdir(parents=True, exist_ok=True)
        previous = pd.read_csv(comparisons) if comparisons.is_file() else pd.DataFrame()
        updated = pd.concat([previous, pd.DataFrame([row])], ignore_index=True).drop_duplicates(["scenario_a", "scenario_b"], keep="last")
        updated.to_csv(comparisons, index=False)
        return row


def _phase1b_cached_run(multiplier: float) -> tuple[Path, Path] | None:
    known = {0.25: "rainfall_25pct", 0.5: "rainfall_50pct", 0.75: "rainfall_75pct", 1.0: "baseline_2005"}
    name = known.get(round(multiplier, 8))
    if name == "baseline_2005":
        pair = (BASE_RPT, BASE_OUT)
    elif name:
        folder = PHASE1 / "phase1b" / "runs" / name
        pair = (folder / f"{name}.rpt", folder / f"{name}.out")
    else:
        return None
    return pair if pair[0].is_file() and pair[1].is_file() else None


def create_phase2_scenarios() -> None:
    folder = PHASE2 / "scenarios"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "physics_config.json").write_text(json.dumps({
        "flood_state_thresholds_m": FLOOD_THRESHOLDS_M,
        "threshold_source": "CONFIGURED_ENGINEERING_THRESHOLD_NOT_CALIBRATED",
        "surface_depth_required_for_classification": True,
        "note": "Thresholds remain configurable and are not municipal warning levels. Grid flood state remains unclassified until surface depth is available.",
        "infrastructure_modes_supported": ["existing"],
        "infrastructure_modes_prepared_not_claimed": ["proposal", "existing_plus_proposal"],
        "tide_modes_prepared": ["low", "normal", "high", "very_high"],
        "tide_hydraulically_applied_modes": ["disabled"],
    }, indent=2), encoding="utf-8")
    items = [("historical_2005", 1.0), ("rainfall_025", .25), ("rainfall_050", .50), ("rainfall_075", .75), ("rainfall_100", 1.0)]
    for scenario_id, multiplier in items:
        value = {"scenario_id": scenario_id, "base_event": "historical_2005", "rainfall_multiplier": multiplier,
            "infrastructure_mode": "existing", "tide_mode": "disabled", "rainfall_source": "reconstructed 26 July 2005 profile; 108 x 15-minute intervals",
            "infrastructure_modes_supported": ["existing"], "infrastructure_modes_prepared": ["proposal", "existing_plus_proposal"],
            "tide_modes_prepared": ["low", "normal", "high", "very_high"], "tide_modes_applied": ["disabled"],
            "validation_status": "ENGINE_EXECUTABLE_HYDRAULICALLY_UNVALIDATED"}
        (folder / f"{scenario_id}.json").write_text(json.dumps(value, indent=2), encoding="utf-8")


def write_phase2_artifacts() -> dict[str, Any]:
    for part in ("scenarios", "runs", "results", "spatial", "diagnostics", "manifests", "reports"):
        (PHASE2 / part).mkdir(parents=True, exist_ok=True)
    mapping_path = PHASE2 / "spatial" / "grid_hydraulic_mapping.csv"
    if not mapping_path.is_file():
        mapping_report = build_grid_mapping(mapping_path)
    else:
        mapping_report = json.loads((PHASE2 / "spatial" / "spatial_mapping_report.json").read_text(encoding="utf-8"))
    create_phase2_scenarios()
    write_uncertainty_ledger(PHASE2 / "diagnostics" / "uncertainty_ledger.csv")
    scenario = SwmmScenario()
    digest = scenario_hash(scenario)
    simulation_id = f"sim_{digest[:20]}"
    result_dir = PHASE2 / "results"
    extracted = extract_output(BASE_OUT, scenario, simulation_id, result_dir, mapping_path)
    (PHASE2 / "diagnostics" / "physics_quality_report.json").write_text(json.dumps(extracted["quality"], indent=2), encoding="utf-8")
    job_dir = PHASE2 / "manifests" / "jobs"
    job_dir.mkdir(parents=True, exist_ok=True)
    job = {"engine": "swmm", "simulation_id": simulation_id, "scenario_id": scenario.scenario_id, "scenario_hash": digest,
        "status": "completed", "cache_hit": True, "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(), "summary": extracted["summary"],
        "validation_status": extracted["quality"]["overall_status"], "result_paths": extracted["summary"]["result_paths"],
        "execution": "reused saved Phase 1 baseline; no new solver run"}
    (job_dir / f"{simulation_id}.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
    return {"mapping": mapping_report, "baseline": extracted["summary"], "quality": extracted["quality"]}
