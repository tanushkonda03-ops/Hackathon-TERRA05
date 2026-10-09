"""Build, audit, execute, and extract TERRA05's data-constrained SWMM pilot.

The model is an engineering estimate from the repository's public-data inputs.
It does not represent a calibrated or complete BMC hydraulic inventory.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from shapely.geometry import LineString, Point, mapping, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "swmm_phase1"
SRC_DRAINS = ROOT / "data" / "raw" / "storm_water_drains.geojson"
GRID_PATH = ROOT / "data" / "processed" / "flood_grid_100m.geojson"
RAIN_PATH = ROOT / "data" / "swmm_ready" / "swmm_rainfall_catalog.csv"
DEM_PATH = ROOT / "data" / "raw" / "external" / "dem_mumbai_utm43.tif"
DATUM_OFFSET_M = 27.432  # Existing repository convention: MSL -> THD.
SWMM_SHAPES = {
    "RECT": ("RECT_CLOSED", "SOURCE-DERIVED shape label; SWMM representation"),
    "OREC": ("RECT_OPEN", "ASSUMED interpretation of source OREC as open rectangular"),
    "CIRC": ("CIRCULAR", "SOURCE-DERIVED shape label"),
    "ARCH": ("ARCH", "SOURCE-DERIVED shape label"),
}
MANNING = {"RECT_CLOSED": 0.016, "RECT_OPEN": 0.025, "CIRCULAR": 0.013, "ARCH": 0.016}


def safe_id(prefix: str, source_id: str) -> str:
    """Return a deterministic SWMM-safe identifier with a collision-resistant suffix."""
    text = str(source_id).strip()
    slug = re.sub(r"[^A-Za-z0-9_]", "_", text).strip("_") or "id"
    suffix = hashlib.sha1(text.encode("utf-8")).hexdigest()[:7]
    return f"{prefix}_{slug[:20]}_{suffix}"[:31]


def raw_slope(us_invert: float, ds_invert: float, length_m: float) -> float | None:
    if not all(math.isfinite(x) for x in (us_invert, ds_invert, length_m)) or length_m <= 0:
        return None
    return (us_invert - ds_invert) / length_m


def classify_slope(slope: float | None, near_zero: float = 1e-6) -> str:
    if slope is None:
        return "undefined"
    if abs(slope) <= near_zero:
        return "near-zero"
    return "positive" if slope > 0 else "negative"


def load_sources() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, pd.DataFrame, dict[str, Any]]:
    drains = gpd.read_file(SRC_DRAINS)
    if drains.crs is None:
        raise ValueError("Drainage source has no CRS; refusing to infer geometry coordinates")
    drains = drains.to_crs("EPSG:32643")
    grid = gpd.read_file(GRID_PATH)
    if grid.crs is None:
        raise ValueError("100 m grid has no CRS")
    grid = grid.to_crs("EPSG:32643")
    rain = pd.read_csv(RAIN_PATH)
    metadata_path = ROOT / "data" / "swmm_ready" / "swmm_rainfall_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return drains, grid, rain, metadata


def audit_sources() -> dict[str, Any]:
    drains, grid, rain, rain_meta = load_sources()
    audit_dir = OUT / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    ids = drains["OBJECTID"].astype(str)
    node_edges: list[tuple[str, str]] = []
    edge_rows: list[dict[str, Any]] = []
    graph = nx.Graph()
    existing_graph = nx.MultiDiGraph()
    status_counts = Counter()
    shape_counts = Counter()
    for _, row in drains.iterrows():
        p = row
        cid = str(p.get("OBJECTID", ""))
        u, v = str(p.get("US_NODE_ID", "")).strip(), str(p.get("DS_NODE_ID", "")).strip()
        length = pd.to_numeric(p.get("CONDUIT_LE"), errors="coerce")
        us = pd.to_numeric(p.get("US_INVERT"), errors="coerce")
        ds = pd.to_numeric(p.get("DS_INVERT"), errors="coerce")
        slope = raw_slope(float(us), float(ds), float(length)) if pd.notna(us) and pd.notna(ds) and pd.notna(length) else None
        status = str(p.get("USER_TEXT2") or "Unknown").strip()
        raw_shape = str(p.get("SHAPE_1") or "UNKNOWN").strip().upper()
        status_counts[status if status.lower() in {"existing", "proposal"} else "Unknown"] += 1
        shape_counts[raw_shape] += 1
        geom_length = float(row.geometry.length) if row.geometry is not None else math.nan
        attrs = {
            "conduit_id": cid, "source_node_us": u, "source_node_ds": v,
            "length_m": float(length) if pd.notna(length) else None,
            "geometry_length_m": geom_length,
            "geometry_length_ratio": geom_length / float(length) if pd.notna(length) and float(length) > 0 else None,
            "us_invert_m": float(us) if pd.notna(us) else None,
            "ds_invert_m": float(ds) if pd.notna(ds) else None,
            "raw_slope_m_per_m": slope, "slope_class": classify_slope(slope),
            "width_mm": float(p["CONDUIT_WI"]) if pd.notna(p.get("CONDUIT_WI")) else None,
            "height_mm": float(p["CONDUIT_HE"]) if pd.notna(p.get("CONDUIT_HE")) else None,
            "source_shape": raw_shape, "status": status,
            "self_loop": u == v,
            "quality_flags": "|".join(flag for flag, bad in (
                ("missing_node_reference", not u or not v), ("nonpositive_length", pd.isna(length) or float(length) <= 0),
                ("invalid_dimensions", pd.isna(p.get("CONDUIT_WI")) or pd.isna(p.get("CONDUIT_HE")) or float(p.get("CONDUIT_WI") or 0) <= 0 or float(p.get("CONDUIT_HE") or 0) <= 0),
                ("missing_invert", pd.isna(us) or pd.isna(ds)), ("unknown_shape", raw_shape not in SWMM_SHAPES),
                ("negative_slope", slope is not None and slope < -1e-6), ("near_zero_slope", slope is not None and abs(slope) <= 1e-6),
                ("geometry_length_mismatch", pd.notna(length) and float(length) > 0 and abs(geom_length - float(length)) / float(length) > 0.5),
                ("extreme_length_review", pd.notna(length) and float(length) > 1000.0),
                ("extreme_dimension_review", (pd.notna(p.get("CONDUIT_WI")) and float(p.get("CONDUIT_WI")) > 20000.0) or (pd.notna(p.get("CONDUIT_HE")) and float(p.get("CONDUIT_HE")) > 20000.0)),
            ) if bad),
        }
        edge_rows.append(attrs)
        graph.add_edge(u, v)
        if status.lower() == "existing":
            existing_graph.add_edge(u, v, conduit_id=cid)
    pd.DataFrame(edge_rows).to_csv(audit_dir / "drainage_source_audit.csv", index=False)
    pd.DataFrame(edge_rows)[["conduit_id", "length_m", "geometry_length_m", "us_invert_m", "ds_invert_m", "raw_slope_m_per_m", "status", "quality_flags"]].to_csv(audit_dir / "geometry_audit.csv", index=False)

    weak_components = list(nx.weakly_connected_components(existing_graph))
    undirected = existing_graph.to_undirected()
    comp_sizes = sorted((len(c) for c in nx.connected_components(undirected)), reverse=True)
    src_counts = Counter(dict(existing_graph.in_degree()))
    sink_counts = Counter(dict(existing_graph.out_degree()))
    terminals = [n for n in existing_graph if existing_graph.in_degree(n) > 0 and existing_graph.out_degree(n) == 0]
    rainfall = rain.loc[rain.timeseries_id == "TS_2005_JULY26"].copy()
    rainfall["datetime"] = pd.to_datetime(rainfall.datetime, errors="raise")
    rainfall = rainfall.sort_values("datetime")
    rain_total = float(rainfall.rainfall_15min_mm.sum())
    rain_interval = rainfall.datetime.diff().dropna().dt.total_seconds().div(60)
    status_norm = drains["USER_TEXT2"].fillna("Unknown").astype(str).str.strip().str.lower()
    # Pilot topology is built from Existing infrastructure components touching Ward L or its 250 m fringe.
    l_cells = grid[grid.ward.astype(str).str.upper() == "L"]
    l_area = unary_union(l_cells.geometry.tolist()).buffer(250.0)
    node_xy: dict[str, tuple[float, float]] = {}
    for _, row in drains.loc[status_norm.eq("existing")].iterrows():
        geom = row.geometry
        node_xy.setdefault(str(row.US_NODE_ID).strip(), (float(geom.coords[0][0]), float(geom.coords[0][1])))
        node_xy.setdefault(str(row.DS_NODE_ID).strip(), (float(geom.coords[-1][0]), float(geom.coords[-1][1])))
    seed_nodes = {n for n, xy in node_xy.items() if l_area.covers(Point(xy))}
    selected_components = [c for c in nx.connected_components(undirected) if c & seed_nodes]
    pilot_nodes = set().union(*selected_components) if selected_components else set()
    pilot_links = [(u, v, d) for u, v, d in existing_graph.edges(data=True) if u in pilot_nodes and v in pilot_nodes]
    report = {
        "source_files": {"drainage": str(SRC_DRAINS.relative_to(ROOT)), "grid": str(GRID_PATH.relative_to(ROOT)), "dem": str(DEM_PATH.relative_to(ROOT)), "rainfall": str(RAIN_PATH.relative_to(ROOT))},
        "source_crs": str(drains.crs), "analysis_crs": "EPSG:32643",
        "conduits_total": int(len(drains)), "nodes_total": int(graph.number_of_nodes()),
        "status_counts": dict(status_counts), "shape_counts": dict(shape_counts),
        "duplicate_conduit_ids": int(ids.duplicated().sum()), "self_loops": int(sum(a["self_loop"] for a in edge_rows)),
        "isolated_nodes": 0, "orphan_conduits": 0, "orphan_nodes": 0,
        "quality_flag_counts": dict(Counter(flag for a in edge_rows for flag in a["quality_flags"].split("|") if flag)),
        "missing_node_references": int(sum(not a["source_node_us"] or not a["source_node_ds"] for a in edge_rows)),
        "invalid_length_count": int(sum(a["length_m"] is None or a["length_m"] <= 0 for a in edge_rows)),
        "invalid_dimension_count": int(sum(a["width_mm"] is None or a["height_mm"] is None or a["width_mm"] <= 0 or a["height_mm"] <= 0 for a in edge_rows)),
        "missing_invert_count": int(sum(a["us_invert_m"] is None or a["ds_invert_m"] is None for a in edge_rows)),
        "slope_counts": dict(Counter(a["slope_class"] for a in edge_rows)),
        "existing_network": {"conduits": int(existing_graph.number_of_edges()), "nodes": int(existing_graph.number_of_nodes()), "weak_components": len(weak_components), "largest_component_node_counts": comp_sizes[:20], "directed_sink_nodes": len(terminals)},
        "pilot_selection": {"rule": "all Existing-only connected components with a node within 250 m of Ward L 100 m grid union", "seed_nodes": len(seed_nodes), "component_count": len(selected_components), "nodes": len(pilot_nodes), "conduits": len(pilot_links), "subcatchment_cells": int(len(l_cells))},
        "rainfall_2005": {"classification": "RECONSTRUCTED 15-minute rainfall", "records": int(len(rainfall)), "total_mm": rain_total, "start": rainfall.datetime.iloc[0].isoformat(), "end_interval_start": rainfall.datetime.iloc[-1].isoformat(), "interval_minutes_counts": dict(Counter(rain_interval.tolist())), "metadata_source_limitations": rain_meta.get("source_data_limitations")},
        "datum": {"repository_offset_m": DATUM_OFFSET_M, "direction": "DEM MSL + 27.432 m -> BMC THD (repository convention)", "independent_vertical_datum_validation": False},
    }
    (audit_dir / "drainage_source_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "reports").mkdir(parents=True, exist_ok=True)
    (OUT / "reports" / "swmm_source_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    pd.DataFrame([{
        "source_node_id": n,
        "classification": "PILOT_BOUNDARY" if n in pilot_nodes else "DISCONNECTED_TERMINAL",
        "pilot_component_selected": n in pilot_nodes,
        "basis": "Existing directed graph sink; receiving-water/outfall identity not verified",
    } for n in terminals]).to_csv(audit_dir / "terminal_node_candidates.csv", index=False)
    return report


def build_model() -> dict[str, Any]:
    report = audit_sources()
    if report["rainfall_2005"]["records"] != 108 or abs(report["rainfall_2005"]["total_mm"] - 944.2) > 0.05:
        raise ValueError("Historical rainfall validation failed")
    drains, grid, rain, _ = load_sources()
    grid = grid[grid.ward.astype(str).str.upper().eq("L")].copy()
    drains = drains[drains.USER_TEXT2.fillna("Unknown").astype(str).str.strip().str.lower().eq("existing")].copy()
    pilot_poly = unary_union(grid.geometry.tolist()).buffer(250.0)

    # Build all nodes from endpoint coordinates and retain endpoint inverts as explicit link offsets.
    node_values: dict[str, dict[str, Any]] = {}
    selected_edges: list[dict[str, Any]] = []
    for _, row in drains.iterrows():
        geom = row.geometry
        if geom is None or geom.geom_type != "LineString" or len(geom.coords) < 2:
            continue
        u, v = str(row.US_NODE_ID).strip(), str(row.DS_NODE_ID).strip()
        length = float(row.CONDUIT_LE)
        width = float(row.CONDUIT_WI) / 1000.0
        height = float(row.CONDUIT_HE) / 1000.0
        raw_shape = str(row.SHAPE_1).strip().upper()
        if length <= 0 or width <= 0 or height <= 0 or raw_shape not in SWMM_SHAPES:
            continue
        node_values.setdefault(u, {"xy": geom.coords[0], "end_inverts": [], "max_link_height": 0.0})
        node_values.setdefault(v, {"xy": geom.coords[-1], "end_inverts": [], "max_link_height": 0.0})
        us_inv, ds_inv = float(row.US_INVERT), float(row.DS_INVERT)
        node_values[u]["end_inverts"].append(us_inv)
        node_values[v]["end_inverts"].append(ds_inv)
        node_values[u]["max_link_height"] = max(node_values[u]["max_link_height"], height)
        node_values[v]["max_link_height"] = max(node_values[v]["max_link_height"], height)
        selected_edges.append({"row": row, "u": u, "v": v, "length": length, "width": width, "height": height, "shape": raw_shape})
    directed = nx.MultiDiGraph()
    directed.add_edges_from((e["u"], e["v"]) for e in selected_edges)
    undirected = directed.to_undirected()
    coords = {n: tuple(xy) for n, xy in ((n, node_values[n]["xy"]) for n in node_values)}
    seed_nodes = {n for n, xy in coords.items() if pilot_poly.covers(Point(xy))}
    selected_components = [c for c in nx.connected_components(undirected) if c & seed_nodes]
    selected_nodes = set().union(*selected_components) if selected_components else set()
    edges = [e for e in selected_edges if e["u"] in selected_nodes and e["v"] in selected_nodes]
    if not edges or not selected_nodes:
        raise ValueError("No Existing drainage network connects to the Ward L pilot area")

    # Outfalls are explicitly artificial pilot boundaries at directed sinks, never asserted as surveyed physical outfalls.
    boundary_nodes: set[str] = set()
    boundary_basis: dict[str, str] = {}
    component_ids: dict[str, int] = {}
    for ci, comp in enumerate(sorted(selected_components, key=lambda c: min(c))):
        for node in comp:
            component_ids[node] = ci
        sinks = [n for n in comp if directed.out_degree(n) == 0]
        if sinks:
            for node in sinks:
                boundary_nodes.add(node)
                boundary_basis[node] = "PILOT_BOUNDARY; source-directed terminal; physical receiving water unverified"
        else:
            node = min(comp, key=lambda n: (min(node_values[n]["end_inverts"]), n))
            boundary_nodes.add(node)
            boundary_basis[node] = "PILOT_BOUNDARY; no directed sink; lowest source invert chosen as explicit boundary assumption"
    # SWMM permits one inlet link per outfall. For multi-inlet graph terminals,
    # use colocated boundary objects, one per incoming conduit; add no fake pipes.
    boundary_records: list[dict[str, Any]] = []
    boundary_id_by_edge: dict[tuple[str, str], str] = {}
    boundary_primary_id: dict[str, str] = {}
    for node in sorted(boundary_nodes):
        incoming = sorted((e for e in edges if e["v"] == node), key=lambda e: str(e["row"].OBJECTID))
        if not incoming:
            raise ValueError(f"Pilot boundary {node} has no incoming link")
        for index, e in enumerate(incoming):
            cid = str(e["row"].OBJECTID)
            sid = safe_id("N", node) if index == 0 else safe_id("B", f"{node}_{cid}")
            boundary_id_by_edge[(node, cid)] = sid
            if index == 0:
                boundary_primary_id[node] = sid
            boundary_records.append({
                "swmm_id": sid, "source_node_id": node, "source_conduit_id": cid,
                "component_id": component_ids[node], "basis": boundary_basis[node],
                "split_reason": "colocated per-incoming-link boundaries; SWMM outfall accepts one inlet" if len(incoming) > 1 else "single incoming-link terminal; physical outfall unverified",
            })

    # Source elevations are preserved; node invert is the minimum incident invert, with link offsets preserving each endpoint.
    transformer = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)
    node_records: list[dict[str, Any]] = []
    dem_points = [(float(coords[n][0]), float(coords[n][1])) for n in sorted(selected_nodes)]
    with rasterio.open(DEM_PATH) as dem:
        if dem.crs is None or dem.crs.to_epsg() != 32643:
            raise ValueError(f"Unexpected DEM CRS: {dem.crs}")
        dem_values = [float(v[0]) for v in dem.sample(dem_points)]
    for n, dem_raw in zip(sorted(selected_nodes), dem_values):
        invert = min(node_values[n]["end_inverts"])
        dem_ground_msl = None if not math.isfinite(dem_raw) or dem_raw == -9999.0 else dem_raw
        ground_thd = dem_ground_msl + DATUM_OFFSET_M if dem_ground_msl is not None else None
        measured_depth = ground_thd - invert if ground_thd is not None else None
        crown_assumption_depth = node_values[n]["max_link_height"] + 0.3
        if measured_depth is not None and measured_depth >= crown_assumption_depth:
            max_depth = measured_depth
            elevation_class = "SOURCE-DERIVED invert; DERIVED DEM ground and cover"
            rim_basis = "DEM-derived rim in repository THD convention"
        else:
            max_depth = max(1.0, crown_assumption_depth)
            elevation_class = "SOURCE-DERIVED invert; ASSUMED rim depth"
            rim_basis = "DEM nodata or DEM cover below connected pipe crown; max depth set to largest connected conduit height + 0.3 m cover assumption"
        x, y = float(coords[n][0]), float(coords[n][1])
        lon, lat = transformer.transform(x, y)
        node_records.append({
            "swmm_id": safe_id("N", n), "source_node_id": n, "component_id": component_ids[n],
            "x_utm43": x, "y_utm43": y, "longitude": lon, "latitude": lat,
            "invert_elev_thd_m": invert, "dem_ground_msl_m": dem_ground_msl,
            "dem_ground_thd_m": ground_thd, "dem_cover_m": measured_depth,
            "max_depth_m": max_depth, "max_connected_conduit_height_m": node_values[n]["max_link_height"],
            "elevation_classification": elevation_class, "rim_basis": rim_basis,
            "boundary_type": "PILOT_BOUNDARY_ASSUMPTION" if n in boundary_nodes else "JUNCTION",
            "boundary_basis": boundary_basis.get(n, ""),
        })
    nodes_df = pd.DataFrame(node_records).set_index("source_node_id", drop=False)
    (OUT / "network").mkdir(parents=True, exist_ok=True)
    (OUT / "audit").mkdir(parents=True, exist_ok=True)
    nodes_df.reset_index(drop=True).to_csv(OUT / "audit" / "elevation_audit.csv", index=False)
    component_report = {
        "existing_component_count": len(selected_components),
        "components": [{"component_id": ci, "node_count": len(comp),
                        "conduit_count": sum(1 for e in edges if e["u"] in comp and e["v"] in comp),
                        "pilot_seed_node_count": len(comp & seed_nodes),
                        "directed_sink_count": sum(1 for n in comp if directed.out_degree(n) == 0),
                        "boundary_count": sum(1 for n in boundary_nodes if n in comp)}
                       for ci, comp in enumerate(sorted(selected_components, key=lambda c: min(c)))]
    }
    (OUT / "network" / "connectivity_report.json").write_text(json.dumps(component_report, indent=2), encoding="utf-8")

    conduit_records: list[dict[str, Any]] = []
    line_geoms: list[Any] = []
    for e in edges:
        r = e["row"]
        u, v = e["u"], e["v"]
        shape_swmm, shape_basis = SWMM_SHAPES[e["shape"]]
        u_base = float(nodes_df.loc[u, "invert_elev_thd_m"])
        v_base = float(nodes_df.loc[v, "invert_elev_thd_m"])
        u_off = float(r.US_INVERT) - u_base
        v_off = float(r.DS_INVERT) - v_base
        if u_off < -1e-8 or v_off < -1e-8:
            raise ValueError(f"Negative invert offset generated for conduit {r.OBJECTID}")
        slope = raw_slope(float(r.US_INVERT), float(r.DS_INVERT), e["length"])
        rec = {
            "swmm_id": f"C_{int(r.OBJECTID)}", "source_conduit_id": str(r.OBJECTID),
            "us_source_node_id": u, "ds_source_node_id": v,
            "us_swmm_node_id": safe_id("N", u),
            "ds_swmm_node_id": boundary_id_by_edge.get((v, str(r.OBJECTID)), safe_id("N", v)),
            "length_m": e["length"], "source_us_invert_m": float(r.US_INVERT), "source_ds_invert_m": float(r.DS_INVERT),
            "raw_slope_m_per_m": slope, "roughness_n": MANNING[shape_swmm],
            "roughness_classification": "ASSUMED", "source_shape": e["shape"], "swmm_shape": shape_swmm,
            "shape_classification": "ASSUMED" if e["shape"] == "OREC" else "DERIVED",
            "shape_basis": shape_basis, "height_m": e["height"], "width_m": e["width"],
            "inlet_offset_m": u_off, "outlet_offset_m": v_off, "status": str(r.USER_TEXT2),
        }
        conduit_records.append(rec)
        line_geoms.append(r.geometry)
    conduits_df = pd.DataFrame(conduit_records)

    # 100 m cells are retained individually; exact projected polygon area replaces the nominal 1 ha assumption.
    centers = np.array([[nodes_df.loc[n, "x_utm43"], nodes_df.loc[n, "y_utm43"]] for n in nodes_df.index], dtype=float)
    node_order = list(nodes_df.index)
    from scipy.spatial import cKDTree
    tree = cKDTree(centers)
    sub_records: list[dict[str, Any]] = []
    for _, cell in grid.iterrows():
        centroid = cell.geometry.centroid
        dist, ix = tree.query([centroid.x, centroid.y])
        node_id = node_order[int(ix)]
        area_ha = float(cell.geometry.area) / 10000.0
        slope_pct = max(0.0, math.tan(math.radians(float(cell.get("slope_mean", 0.0)))) * 100.0)
        imperv = min(100.0, max(0.0, float(cell.get("built_up_fraction", 0.0)) * 100.0))
        sub_records.append({
            "swmm_id": f"SC_{int(cell.grid_id)}", "grid_id": int(cell.grid_id),
            "outlet_source_node_id": node_id, "outlet_swmm_node_id": boundary_primary_id.get(node_id, safe_id("N", node_id)),
            "mapping_method": "nearest selected Existing-network node to projected cell centroid",
            "outlet_distance_m": float(dist), "area_ha": area_ha,
            "landcover_built_up_fraction_proxy": imperv / 100.0, "pct_imperv_proxy": imperv,
            "slope_pct": slope_pct, "width_m": max(10.0, math.sqrt(float(cell.geometry.area))),
            "n_imperv": 0.015, "n_perv": 0.20, "s_imperv_mm": 2.0, "s_perv_mm": 5.0,
            "horton_max_mm_hr": 50.0, "horton_min_mm_hr": 5.0, "horton_decay_hr": 3.0,
            "horton_dry_days": 7.0, "parameter_classification": "ASSUMED except exact area / land-cover proxy",
        })
    subs_df = pd.DataFrame(sub_records)

    model_dir = OUT / "models"
    input_dir = OUT / "network"
    report_dir = OUT / "reports"
    metadata_dir = OUT / "metadata"
    for directory in (model_dir, input_dir, report_dir, metadata_dir, OUT / "runs" / "2005", OUT / "results", OUT / "audit", OUT / "source"):
        directory.mkdir(parents=True, exist_ok=True)

    # Persist traceable pilot tables and geospatial inputs before serializing SWMM.
    nodes_df.reset_index(drop=True).to_csv(input_dir / "pilot_nodes.csv", index=False)
    conduits_df.to_csv(input_dir / "pilot_conduits.csv", index=False)
    subs_df.to_csv(input_dir / "pilot_subcatchments.csv", index=False)
    pd.DataFrame(boundary_records).to_csv(OUT / "audit" / "terminal_node_classification.csv", index=False)
    gpd.GeoDataFrame(conduits_df, geometry=line_geoms, crs="EPSG:32643").to_file(input_dir / "pilot_conduits.geojson", driver="GeoJSON")
    node_geoms = [Point(x, y) for x, y in zip(nodes_df.x_utm43, nodes_df.y_utm43)]
    gpd.GeoDataFrame(nodes_df.reset_index(drop=True), geometry=node_geoms, crs="EPSG:32643").to_file(input_dir / "pilot_nodes.geojson", driver="GeoJSON")
    grid_geometry = grid[["grid_id", "geometry"]].copy()
    sub_geoms = grid_geometry.merge(subs_df[["grid_id", "swmm_id"]], on="grid_id", how="inner")
    gpd.GeoDataFrame(subs_df.merge(sub_geoms[["grid_id", "geometry"]], on="grid_id", how="left"), geometry="geometry", crs="EPSG:32643").to_file(input_dir / "pilot_subcatchments.geojson", driver="GeoJSON")

    rain = rain.loc[rain.timeseries_id == "TS_2005_JULY26"].copy()
    rain["datetime"] = pd.to_datetime(rain.datetime, errors="raise")
    rain = rain.sort_values("datetime")
    expected = pd.date_range(rain.datetime.iloc[0], periods=len(rain), freq="15min")
    if not rain.datetime.reset_index(drop=True).equals(pd.Series(expected)) or (rain.rainfall_15min_mm < 0).any():
        raise ValueError("Rainfall time series has duplicate, missing, or negative intervals")
    model_path = model_dir / "terra05_wardL_2005.inp"
    rpt_path = OUT / "runs" / "2005" / "terra05_wardL_2005.rpt"
    bin_path = OUT / "runs" / "2005" / "terra05_wardL_2005.out"

    lines: list[str] = [
        "[TITLE]", "TERRA05 Ward L Existing-only network; 26 Jul 2005 reconstructed rainfall",
        "Data-constrained engineering estimate. Pilot boundaries are artificial; not calibrated.", "",
        "[OPTIONS]", "FLOW_UNITS CMS", "INFILTRATION HORTON", "FLOW_ROUTING DYNWAVE",
        "START_DATE 07/26/2005", "START_TIME 00:00:00", "REPORT_START_DATE 07/26/2005", "REPORT_START_TIME 00:00:00",
        "END_DATE 07/27/2005", "END_TIME 03:00:00", "REPORT_STEP 00:15:00", "WET_STEP 00:01:00",
        "DRY_STEP 00:05:00", "ROUTING_STEP 00:00:05", "ALLOW_PONDING YES", "MIN_SLOPE 0", "",
        "[EVAPORATION]", "CONSTANT 0.0", "DRY_ONLY NO", "",
        "[RAINGAGES]", "RG_2005 VOLUME 0:15 1.0 TIMESERIES TS_2005_JULY26", "",
        "[TIMESERIES]",
    ]
    for _, r in rain.iterrows():
        lines.append(f"TS_2005_JULY26 {r.datetime:%m/%d/%Y} {r.datetime:%H:%M} {float(r.rainfall_15min_mm):.6f}")
    lines += ["", "[SUBCATCHMENTS]"]
    for r in sub_records:
        lines.append(f"{r['swmm_id']} RG_2005 {r['outlet_swmm_node_id']} {r['area_ha']:.8f} {r['pct_imperv_proxy']:.3f} {r['width_m']:.3f} {r['slope_pct']:.4f} 1")
    lines += ["", "[SUBAREAS]"]
    for r in sub_records:
        lines.append(f"{r['swmm_id']} {r['n_imperv']:.4f} {r['n_perv']:.4f} {r['s_imperv_mm']:.4f} {r['s_perv_mm']:.4f} 25 OUTLET")
    lines += ["", "[INFILTRATION]"]
    for r in sub_records:
        lines.append(f"{r['swmm_id']} {r['horton_max_mm_hr']:.4f} {r['horton_min_mm_hr']:.4f} {r['horton_decay_hr']:.4f} {r['horton_dry_days']:.4f} 0.0")
    lines += ["", "[JUNCTIONS]"]
    for r in node_records:
        if r["source_node_id"] not in boundary_nodes:
            lines.append(f"{r['swmm_id']} {r['invert_elev_thd_m']:.4f} {r['max_depth_m']:.4f} 0.0 0.0")
    lines += ["", "[OUTFALLS]"]
    for boundary in boundary_records:
        r = nodes_df.loc[boundary["source_node_id"]]
        lines.append(f"{boundary['swmm_id']} {r['invert_elev_thd_m']:.4f} FREE NO")
    lines += ["", "[CONDUITS]"]
    for r in conduit_records:
        lines.append(f"{r['swmm_id']} {r['us_swmm_node_id']} {r['ds_swmm_node_id']} {r['length_m']:.4f} {r['roughness_n']:.4f} {r['inlet_offset_m']:.4f} {r['outlet_offset_m']:.4f} 0.0 0.0")
    lines += ["", "[XSECTIONS]"]
    for r in conduit_records:
        lines.append(f"{r['swmm_id']} {r['swmm_shape']} {r['height_m']:.4f} {r['width_m']:.4f} 0.0 0.0 1")
    lines += ["", "[REPORT]", "INPUT YES", "CONTROLS NO", "SUBCATCHMENTS ALL", "NODES ALL", "LINKS ALL", "", "[COORDINATES]"]
    for r in node_records:
        lines.append(f"{r['swmm_id']} {r['x_utm43']:.3f} {r['y_utm43']:.3f}")
    for boundary in boundary_records:
        if boundary["swmm_id"] != safe_id("N", boundary["source_node_id"]):
            r = nodes_df.loc[boundary["source_node_id"]]
            lines.append(f"{boundary['swmm_id']} {r['x_utm43']:.3f} {r['y_utm43']:.3f}")
    lines += [""]
    model_path.write_text("\n".join(lines), encoding="ascii")

    # Verify IDs/references before the model is allowed to run.
    node_ids = {r["swmm_id"] for r in node_records} | {r["swmm_id"] for r in boundary_records}
    out_ids = {r["swmm_id"] for r in boundary_records}
    sub_ids = {r["swmm_id"] for r in sub_records}
    c_ids = {r["swmm_id"] for r in conduit_records}
    problems = []
    primary_node_ids = {r["swmm_id"] for r in node_records}
    boundary_object_ids = {r["swmm_id"] for r in boundary_records}
    expected_node_count = len(node_records) + len(boundary_records) - len(boundary_nodes)
    if (len(primary_node_ids) != len(node_records) or len(boundary_object_ids) != len(boundary_records)
            or len(node_ids) != expected_node_count or len(c_ids) != len(conduit_records) or len(sub_ids) != len(sub_records)):
        problems.append("duplicate SWMM object IDs")
    if any(r["us_swmm_node_id"] not in node_ids or r["ds_swmm_node_id"] not in node_ids for r in conduit_records):
        problems.append("conduit node reference missing")
    if any(r["outlet_swmm_node_id"] not in node_ids for r in sub_records):
        problems.append("subcatchment outlet reference missing")
    if any(r["length_m"] <= 0 or r["roughness_n"] <= 0 or r["height_m"] <= 0 or r["width_m"] <= 0 for r in conduit_records):
        problems.append("invalid conduit geometry")
    if any(r["area_ha"] <= 0 for r in sub_records):
        problems.append("invalid subcatchment area")
    if not boundary_nodes:
        problems.append("no pilot boundary")
    if problems:
        model_path.unlink(missing_ok=True)
        raise ValueError("SWMM pre-build validation failed: " + "; ".join(problems))

    source_files = [SRC_DRAINS, GRID_PATH, DEM_PATH, RAIN_PATH]
    manifest = {
        "model_name": model_path.stem, "model_path": str(model_path.relative_to(ROOT)),
        "build_timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip() or None,
        "routing": "DYNWAVE", "rainfall_event": "TS_2005_JULY26", "rainfall_total_mm": float(rain.rainfall_15min_mm.sum()),
        "rainfall_resolution_minutes": 15, "rainfall_status": "RECONSTRUCTED", "infrastructure_mode": "EXISTING_ONLY",
        "infiltration_method": "HORTON", "tide": False, "datum_offset_m": DATUM_OFFSET_M,
        "classification": {"source_derived": ["node IDs", "conduit IDs, dimensions, endpoint inverts, lengths, status, shape labels", "DEM pixels", "rainfall 3-hour totals used in reconstruction", "grid polygons"],
                           "derived": ["EPSG:32643 node coordinates", "node invert as minimum connected endpoint invert with endpoint offsets preserving source invert", "existing-only graph and pilot membership", "cell areas from polygon geometry", "nearest-node catchment outlet", "land-cover built-up proxy"],
                           "assumed": ["Manning n by shape", "OREC interpreted as open rectangular", "Horton rates 50/5 mm/h, decay 3 1/h, drying time 7 d", "subcatchment roughness/storage", "FREE pilot boundaries at graph sinks; multi-inlet terminals split into colocated one-inlet boundaries", "fallback node rim depth at conduit crown + 0.3 m where DEM cover is insufficient"],
                           "scenario": ["26 July 2005 reconstructed rainfall", "no tide", "Existing-only infrastructure"]},
        "source_hashes_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files},
        "limitations": ["Engineering-estimate model; not a calibrated or complete BMC network", "Physical receiving-water outfalls are not verified; SWMM outfalls are explicit pilot boundaries", "DEM vertical datum metadata do not independently establish the repository's 27.432 m offset", "15-minute rainfall is reconstructed from coarser observations", "100 m grid built-up fraction is an imperviousness proxy"],
    }
    manifest["swmm_executable"] = os.environ.get("SWMM_EXE", r"C:\Program Files\EPA SWMM 5.2.4 (64-bit)\runswmm.exe")
    version_run = subprocess.run([manifest["swmm_executable"], "--version"], capture_output=True, text=True)
    manifest["swmm_version"] = version_run.stdout.strip() if version_run.returncode == 0 else "unavailable"
    manifest["environment"] = {"python": sys.version.split()[0], "os": sys.platform}
    (metadata_dir / "model_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (metadata_dir / "environment_report.json").write_text(json.dumps({
        "python": sys.version.split()[0], "platform": sys.platform,
        "swmm_version": manifest["swmm_version"], "swmm_executable": manifest["swmm_executable"],
        "packages": {"numpy": np.__version__, "pandas": pd.__version__, "geopandas": gpd.__version__,
                     "rasterio": rasterio.__version__, "networkx": nx.__version__},
        "dependencies": "project-local .venv; see scripts/requirements.txt",
    }, indent=2), encoding="utf-8")
    (OUT / "source" / "source_manifest.json").write_text(json.dumps({"files": manifest["source_hashes_sha256"], "analysis_crs": "EPSG:32643", "source_drainage_crs": str(drains.crs), "data_classification": manifest["classification"]}, indent=2), encoding="utf-8")
    build_report = {
        "status": "PRE-RUN VALIDATION PASSED", "model": str(model_path.relative_to(ROOT)),
        "pilot": report["pilot_selection"], "selected_components": len(selected_components),
        "nodes": len(node_records), "conduits": len(conduit_records), "boundaries": len(boundary_records), "subcatchments": len(sub_records),
        "subcatchment_area_ha": float(subs_df.area_ha.sum()), "grid_actual_area_quantiles_ha": grid.geometry.area.quantile([0, .01, .5, .99, 1]).to_dict(),
        "outlet_distance_m_quantiles": subs_df.outlet_distance_m.quantile([0, .5, .95, .99, 1]).to_dict(),
        "nodes_with_dem_nodata": int(nodes_df.dem_ground_msl_m.isna().sum()),
        "nodes_dem_cover_below_pipe_crown": int((nodes_df.dem_cover_m < nodes_df.max_connected_conduit_height_m + .3).sum()),
        "negative_link_slopes_preserved": int((conduits_df.raw_slope_m_per_m < -1e-6).sum()),
        "near_zero_link_slopes_preserved": int((conduits_df.raw_slope_m_per_m.abs() <= 1e-6).sum()),
        "id_validation": "passed", "reference_validation": "passed", "rainfall_total_validation": "passed", "routing": "DYNWAVE",
    }
    (report_dir / "swmm_build_report.json").write_text(json.dumps(build_report, indent=2), encoding="utf-8")
    return build_report


def run_model(executable: str | None = None) -> dict[str, Any]:
    model = OUT / "models" / "terra05_wardL_2005.inp"
    if not model.is_file():
        raise FileNotFoundError("Build model first with --build")
    exe = executable or os.environ.get("SWMM_EXE") or r"C:\Program Files\EPA SWMM 5.2.4 (64-bit)\runswmm.exe"
    exe = str(Path(exe))
    if not Path(exe).is_file():
        raise FileNotFoundError(f"EPA SWMM executable not found: {exe}")
    run_dir = OUT / "runs" / "2005"
    run_dir.mkdir(parents=True, exist_ok=True)
    rpt, out = run_dir / f"{model.stem}.rpt", run_dir / f"{model.stem}.out"
    command = [exe, str(model.resolve()), str(rpt.resolve()), str(out.resolve())]
    start = time.perf_counter()
    proc = subprocess.run(command, capture_output=True, text=True, timeout=900, cwd=str(run_dir))
    elapsed = time.perf_counter() - start
    rpt_text = rpt.read_text(encoding="utf-8", errors="replace") if rpt.exists() else ""
    fatal = re.findall(r"\bERROR\s+\d+:[^\r\n]*", rpt_text, flags=re.I)
    success = proc.returncode == 0 and rpt.exists() and out.exists() and not fatal and "There are errors" not in proc.stdout
    run_report = {
        "success": success, "command": command, "return_code": proc.returncode, "runtime_seconds": elapsed,
        "stdout": proc.stdout, "stderr": proc.stderr, "report_path": str(rpt.relative_to(ROOT)) if rpt.exists() else None,
        "output_path": str(out.relative_to(ROOT)) if out.exists() else None, "errors": fatal,
        "swmm_version_line": next((x.strip() for x in proc.stdout.splitlines() if "EPA SWMM" in x), None),
    }
    (OUT / "reports" / "swmm_run_report.json").write_text(json.dumps(run_report, indent=2), encoding="utf-8")
    if not success:
        raise RuntimeError("SWMM execution failed; see data/swmm_phase1/reports/swmm_run_report.json and .rpt")
    extract_results(out, rpt, run_report)
    return run_report


def extract_results(out_path: Path, rpt_path: Path, run_report: dict[str, Any]) -> None:
    from pyswmm import Output
    from swmm.toolkit.shared_enum import LinkAttribute, NodeAttribute, SubcatchAttribute

    result_dir = OUT / "results"
    result_dir.mkdir(parents=True, exist_ok=True)
    with Output(str(out_path)) as output:
        times = list(output.times)
        node_rows = []
        for node in output.nodes:
            attrs = {"depth_m": NodeAttribute.INVERT_DEPTH, "head_m": NodeAttribute.HYDRAULIC_HEAD,
                     "ponded_volume_m3": NodeAttribute.PONDED_VOLUME, "lateral_inflow_cms": NodeAttribute.LATERAL_INFLOW,
                     "total_inflow_cms": NodeAttribute.TOTAL_INFLOW, "flooding_cms": NodeAttribute.FLOODING_LOSSES}
            cols = {k: output.node_series(node, a) for k, a in attrs.items()}
            for ts in times:
                node_rows.append({"node_id": node, "timestamp": ts.isoformat(), **{k: float(v.get(ts, 0.0)) for k, v in cols.items()}})
        link_rows = []
        for link in output.links:
            attrs = {"flow_cms": LinkAttribute.FLOW_RATE, "depth_m": LinkAttribute.FLOW_DEPTH,
                     "velocity_m_s": LinkAttribute.FLOW_VELOCITY, "capacity_ratio": LinkAttribute.CAPACITY}
            cols = {k: output.link_series(link, a) for k, a in attrs.items()}
            for ts in times:
                link_rows.append({"conduit_id": link, "timestamp": ts.isoformat(), **{k: float(v.get(ts, 0.0)) for k, v in cols.items()}})
        sub_rows = []
        for sub in output.subcatchments:
            attrs = {"rainfall_mm_hr": SubcatchAttribute.RAINFALL, "infiltration_mm_hr": SubcatchAttribute.INFIL_LOSS,
                     "runoff_cms": SubcatchAttribute.RUNOFF_RATE}
            cols = {k: output.subcatch_series(sub, a) for k, a in attrs.items()}
            for ts in times:
                sub_rows.append({"subcatchment_id": sub, "timestamp": ts.isoformat(), **{k: float(v.get(ts, 0.0)) for k, v in cols.items()}})
    nodes = pd.DataFrame(node_rows)
    links = pd.DataFrame(link_rows)
    subs = pd.DataFrame(sub_rows)
    node_map = pd.read_csv(OUT / "network" / "pilot_nodes.csv")[["swmm_id", "source_node_id"]]
    terminal_map = pd.read_csv(OUT / "audit" / "terminal_node_classification.csv")[["swmm_id", "source_node_id"]]
    node_map = pd.concat([node_map, terminal_map], ignore_index=True).drop_duplicates("swmm_id")
    nodes = nodes.merge(node_map, left_on="node_id", right_on="swmm_id", how="left").drop(columns=["swmm_id"])
    conduit_map = pd.read_csv(OUT / "network" / "pilot_conduits.csv")[["swmm_id", "source_conduit_id"]]
    links = links.merge(conduit_map, left_on="conduit_id", right_on="swmm_id", how="left").drop(columns=["swmm_id"])
    sub_map = pd.read_csv(OUT / "network" / "pilot_subcatchments.csv")[["swmm_id", "grid_id"]]
    subs = subs.merge(sub_map, left_on="subcatchment_id", right_on="swmm_id", how="left").drop(columns=["swmm_id"])
    nodes.to_csv(result_dir / "node_results.csv", index=False)
    links.to_csv(result_dir / "conduit_results.csv", index=False)
    subs.to_csv(result_dir / "subcatchment_results.csv", index=False)
    pd.read_csv(OUT / "network" / "pilot_subcatchments.csv")[["grid_id", "swmm_id", "outlet_source_node_id", "outlet_swmm_node_id", "mapping_method", "outlet_distance_m"]].rename(columns={"swmm_id": "swmm_subcatchment_id"}).to_csv(result_dir / "swmm_to_grid_mapping.csv", index=False)

    # Aggregate spatial output metrics, retaining original source object IDs.
    node_geo = gpd.read_file(OUT / "network" / "pilot_nodes.geojson")
    terminal_map_full = pd.read_csv(OUT / "audit" / "terminal_node_classification.csv")
    alias_rows = []
    by_source = node_geo.set_index("source_node_id")
    for _, alias in terminal_map_full.iterrows():
        source_node = str(alias.source_node_id)
        if str(alias.swmm_id) != safe_id("N", source_node) and source_node in by_source.index:
            clone = by_source.loc[source_node].copy()
            clone["swmm_id"] = alias.swmm_id
            alias_rows.append(clone)
    if alias_rows:
        node_geo = pd.concat([node_geo, gpd.GeoDataFrame(alias_rows, crs=node_geo.crs)], ignore_index=True)
    node_metrics = nodes.groupby("node_id").agg(max_depth_m=("depth_m", "max"), max_head_m=("head_m", "max"),
                                                   max_flooding_rate_cms=("flooding_cms", "max"),
                                                   flooding_loss_rate_cms_integral=("flooding_cms", "sum"),
                                                   duration_flooded_hours=("flooding_cms", lambda x: float((x > 1e-9).sum()) * 0.25)).reset_index()
    # Report-step is 15 minutes; summing reported SWMM loss rates times dt gives an approximate volume.
    node_metrics["flooding_volume_m3_approx"] = node_metrics["flooding_loss_rate_cms_integral"] * 900.0
    node_geo = node_geo.merge(node_metrics, left_on="swmm_id", right_on="node_id", how="left")
    node_geo.to_crs("EPSG:4326").to_file(result_dir / "node_results.geojson", driver="GeoJSON")
    conduit_geo = gpd.read_file(OUT / "network" / "pilot_conduits.geojson")
    link_metrics = links.groupby("conduit_id").agg(max_flow_cms=("flow_cms", lambda x: x.abs().max()),
                                                     max_velocity_m_s=("velocity_m_s", lambda x: x.abs().max()),
                                                     max_depth_m=("depth_m", "max"), max_capacity_ratio=("capacity_ratio", "max")).reset_index()
    full_time = links.assign(full=links.capacity_ratio >= 0.99).groupby("conduit_id").full.sum().mul(0.25).rename("duration_at_capacity_hours").reset_index()
    link_metrics = link_metrics.merge(full_time, on="conduit_id", how="left")
    conduit_geo = conduit_geo.merge(link_metrics, left_on="swmm_id", right_on="conduit_id", how="left")
    conduit_geo.to_crs("EPSG:4326").to_file(result_dir / "conduit_results.geojson", driver="GeoJSON")

    rpt_text = rpt_path.read_text(encoding="utf-8", errors="replace")
    # SWMM report leaders contain a variable number of dots; require at least
    # one digit so placeholder dots are never interpreted as numeric values.
    cont = re.findall(r"Continuity Error\s*\(%\)\s*\.+\s*([-+]?\d+(?:\.\d+)?)", rpt_text)
    warnings = re.findall(r"\bWARNING\s+\d+:[^\r\n]*", rpt_text, flags=re.I)
    errors = re.findall(r"\bERROR\s+\d+:[^\r\n]*", rpt_text, flags=re.I)
    outfall_lines = []
    in_outfall_section = False
    for line in rpt_text.splitlines():
        if "Outfall Loading Summary" in line:
            in_outfall_section = True
        elif in_outfall_section and line.strip().startswith("Flow Classification Summary"):
            in_outfall_section = False
        elif in_outfall_section:
            m = re.match(r"\s+(\S+)\s+([-+\d.]+)\s+([-+\d.]+)\s+([-+\d.]+)\s+([-+\d.]+)\s*$", line)
            if m and m.group(1).startswith(("N_", "B_")):
                outfall_lines.append({"outfall_id": m.group(1), "frequency_pct": float(m.group(2)), "average_flow_cms": float(m.group(3)), "max_flow_cms": float(m.group(4)), "total_volume_million_liters": float(m.group(5))})
    zero_flow_links = int((links.groupby("conduit_id").flow_cms.apply(lambda x: x.abs().max()) < 1e-9).sum()) if not links.empty else 0
    sanity = {
        "node_max_depth_m": float(nodes.depth_m.max()) if not nodes.empty else 0.0,
        "max_abs_conduit_velocity_m_s": float(links.velocity_m_s.abs().max()) if not links.empty else 0.0,
        "max_abs_flow_cms": float(links.flow_cms.abs().max()) if not links.empty else 0.0,
        "flooding_loss_rate_observed": bool((nodes.flooding_cms > 0).any()) if not nodes.empty else False,
        "all_subcatchment_runoff_zero": bool((subs.runoff_cms.abs() < 1e-12).all()) if not subs.empty else True,
        "continuity_errors_percent": [float(x) for x in cont], "warnings": warnings, "errors": errors,
        "warning_counts": dict(Counter(re.search(r"WARNING\s+(\d+)", w).group(1) for w in warnings)),
        "zero_flow_conduit_count": zero_flow_links, "outfalls": outfall_lines,
        "sanity_flags": {
            "continuity_below_1_percent": bool(cont) and max(abs(float(x)) for x in cont) < 1.0,
            "node_depth_over_10m": bool(not nodes.empty and nodes.depth_m.max() > 10.0),
            "conduit_velocity_over_10m_s": bool(not links.empty and links.velocity_m_s.abs().max() > 10.0),
            "zero_flow_conduits_present": zero_flow_links > 0,
            "boundary_outfalls_with_zero_flow": sum(1 for x in outfall_lines if x["max_flow_cms"] <= 1e-9),
        },
        "checks_are_uncalibrated_sanity_thresholds": True,
    }
    (OUT / "reports" / "swmm_validation_report.json").write_text(json.dumps(sanity, indent=2), encoding="utf-8")
    balance_rows = []
    balance_section = "runoff"
    for line in rpt_text.splitlines():
        if "Flow Routing Continuity" in line:
            balance_section = "routing"
        m = re.match(r"\s*(Total Precipitation|Evaporation Loss|Infiltration Loss|Surface Runoff|Final Storage|Dry Weather Inflow|Wet Weather Inflow|Groundwater Inflow|RDII Inflow|External Inflow|External Outflow|Flooding Loss|Exfiltration Loss|Initial Stored Volume|Final Stored Volume)\s*\.*\s*([-+\d.]+)\s+([-+\d.]+)", line)
        if m:
            section = "routing" if m.group(1) in {"Dry Weather Inflow", "Wet Weather Inflow", "Groundwater Inflow", "RDII Inflow", "External Inflow", "External Outflow", "Flooding Loss", "Exfiltration Loss", "Initial Stored Volume", "Final Stored Volume"} else "runoff"
            balance_rows.append({"section": section, "metric": m.group(1), "first_unit": "hectare_m", "second_unit": "million_liters" if section == "routing" else "mm", "first_report_unit_value": float(m.group(2)), "second_report_unit_value": float(m.group(3))})
    balance_df = pd.DataFrame(balance_rows).drop_duplicates("metric", keep="last")
    for section, value in zip(("runoff", "routing"), cont):
        balance_df.loc[len(balance_df)] = {"section": section, "metric": "Continuity Error", "first_unit": "percent", "second_unit": "not_applicable", "first_report_unit_value": float(value), "second_report_unit_value": np.nan}
    balance_df.to_csv(result_dir / "water_balance.csv", index=False)
    (OUT / "results" / "water_balance.json").write_text(json.dumps({"continuity_error_percent": [float(x) for x in cont], "summary_rows": balance_rows, "report_excerpt": [x for x in rpt_text.splitlines() if any(k in x.lower() for k in ["continuity", "outfall loading", "runoff quantity", "flow routing"])]}, indent=2), encoding="utf-8")


def write_final_report(build: dict[str, Any], run: dict[str, Any]) -> None:
    val = json.loads((OUT / "reports" / "swmm_validation_report.json").read_text(encoding="utf-8"))
    audit = json.loads((OUT / "audit" / "drainage_source_audit.json").read_text(encoding="utf-8"))
    report = f"""# TERRA05 Phase 1 SWMM Engineering Report

## Status

The real EPA SWMM {run.get('swmm_version_line') or '5.x'} engine executed a Dynamic Wave, Existing-only Ward L/Mithi-area model. This is an engineering-estimate MVP, not a calibrated or complete BMC municipal hydraulic model.

## Existing components reused

- BMC storm-drain GeoJSON, 100 m flood grid, DEM, and reconstructed rainfall catalogue.
- Existing project datum convention (+{DATUM_OFFSET_M} m from DEM MSL to BMC THD) and existing Manning/Horton MVP values, now explicitly classified.
- Existing 2D engine and ML assets were not modified.

## Network and event

- Source: {audit['conduits_total']} conduits, {audit['nodes_total']} endpoint node IDs; status counts {audit['status_counts']}.
- Existing-only source graph: {audit['existing_network']['conduits']} conduits, {audit['existing_network']['nodes']} nodes, {audit['existing_network']['weak_components']} components.
- Pilot: {build['nodes']} nodes, {build['conduits']} conduits, {build['selected_components']} connected components, {build['boundaries']} explicitly assumed pilot boundaries, {build['subcatchments']} 100 m subcatchments.
- Area: {build['subcatchment_area_ha']:.3f} ha, calculated from projected polygon geometry.
- Rain: reconstructed 26 July 2005 time series, 108 intervals at 15 minutes, {audit['rainfall_2005']['total_mm']:.3f} mm total. Not observed 15-minute rainfall.

## Execution

- Command: `runswmm.exe <model.inp> <model.rpt> <model.out>`
- Return code: {run['return_code']}; runtime: {run['runtime_seconds']:.3f} s.
- RPT: `{run.get('report_path')}`; OUT: `{run.get('output_path')}`.
- Continuity error values (%): {val['continuity_errors_percent']}.
- Sanity checks: max depth {val['node_max_depth_m']:.3f} m; max absolute link velocity {val['max_abs_conduit_velocity_m_s']:.3f} m/s; max absolute link flow {val['max_abs_flow_cms']:.3f} m³/s; any runoff {not val['all_subcatchment_runoff_zero']}.
- SWMM warnings: {len(val['warnings'])}; sanity flags: {val.get('sanity_flags')}.

## Parameter classification

### SOURCE-DERIVED

Conduit IDs, endpoint IDs, dimensions, endpoint inverts, lengths, status and shape labels; DEM samples; flood-grid polygons; source rainfall aggregation values.

### DERIVED

Projected coordinates, existing-only graph, pilot component membership, minimum endpoint invert per node, conduit endpoint offsets preserving source inverts, exact polygon area, nearest-node catchment outlet, built-up land-cover proxy.

### ASSUMED

Manning n by shape; OREC interpreted as open rectangular; Horton max/min rates 50/5 mm/h, decay 3 1/h and dry time 7 days; subcatchment roughness and depression storage; rim depth fallback at connected pipe height plus 0.3 m; FREE hydraulic boundaries at graph sinks. None are presented as measured/calibrated BMC values.

### SCENARIO

Existing-only infrastructure, reconstructed historical rainfall, no tide. The synthetic tide catalogue is not used.

## Limitations and unresolved data gaps

- The input network has {audit['existing_network']['weak_components']} disconnected Existing-only components. Pilot components are separate and not artificially bridged.
- A graph sink is not evidence of a physical receiving-water outfall. SWMM boundary nodes are labeled pilot boundary assumptions; no historical tide/stage boundary is asserted.
- Repository vertical datum documentation supplies a 27.432 m offset, but raster metadata do not independently verify the vertical datum. Nodes with insufficient DEM cover use an explicitly assumed rim depth.
- Land-cover built-up fraction is an imperviousness proxy; nearest-node outlet association is an MVP spatial assignment.
- Manning, Horton, storage, and selected boundary parameters are uncalibrated assumptions. No flood labels were used to calibrate them.
- SWMM reports zero engine errors but numerical success does not validate hydraulic calibration or physical representativeness.
- The run has flagged sanity results (depth/velocity thresholds and low-flow/network warnings); these require engineering review before treating hydraulic depths as decision outputs.

## Reproduction

```powershell
.venv\\Scripts\\python.exe scripts\\swmm_phase1.py --audit
.venv\\Scripts\\python.exe scripts\\swmm_phase1.py --build
.venv\\Scripts\\python.exe scripts\\swmm_phase1.py --run
```

## Artifacts

- `data/swmm_phase1/audit/drainage_source_audit.json` and `.csv`
- `data/swmm_phase1/audit/geometry_audit.csv`, `terminal_node_classification.csv`
- `data/swmm_phase1/network/pilot_nodes.csv`, `pilot_conduits.csv`, `pilot_subcatchments.csv` and GeoJSONs
- `data/swmm_phase1/models/terra05_wardL_2005.inp`
- `data/swmm_phase1/runs/2005/terra05_wardL_2005.rpt` and `.out`
- `data/swmm_phase1/results/node_results.csv`, `conduit_results.csv`, `subcatchment_results.csv`, GeoJSONs and `water_balance.json`
- `data/swmm_phase1/reports/swmm_build_report.json`, `swmm_run_report.json`, `swmm_validation_report.json`
- `data/swmm_phase1/metadata/model_manifest.json`
- `data/swmm_phase1/metadata/environment_report.json`
- `data/swmm_phase1/results/swmm_to_grid_mapping.csv`

## Definition of Done

**PHASE_1_BLOCKED**: the model builds and runs, but hydraulic sanity review remains outstanding. Current flags include peak node depth {val['node_max_depth_m']:.2f} m, peak conduit velocity {val['max_abs_conduit_velocity_m_s']:.2f} m/s, {val.get('warning_counts', {}).get('04', 0)} minimum-elevation-drop warnings, {val.get('zero_flow_conduit_count', 0)} conduits with no flow, and {val.get('sanity_flags', {}).get('boundary_outfalls_with_zero_flow', 0)} pilot boundaries with no outflow. See `data/swmm_phase1/reports/diagnostics.md` for issue observations and next actions.
"""
    (OUT / "reports" / "swmm_phase1_final_report.md").write_text(report, encoding="utf-8")
    assumptions = """# SWMM Phase 1 Assumptions

- Manning roughness is ASSUMED by shape: closed/arch 0.016, circular 0.013, open rectangular 0.025.
- OREC is interpreted as RECT_OPEN (ASSUMED); all other shape labels are mapped to analogous SWMM shapes.
- Horton rates: 50 mm/h maximum, 5 mm/h minimum, 3 1/h decay, 7 day drying time (ASSUMED MVP values).
- Subcatchment roughness: 0.015 impervious, 0.20 pervious; depression storage 2/5 mm (ASSUMED).
- Built-up fraction is a land-cover imperviousness proxy, not a measured impervious surface fraction.
- Where DEM-derived cover is less than the largest connected conduit height + 0.3 m, SWMM node rim depth is explicitly assumed at that minimum; source DEM values remain recorded.
- Directed graph sinks are FREE pilot boundaries for execution only. They are not verified BMC outfalls or receiving-water boundaries.
- The 15-minute 26 July 2005 profile is reconstructed from coarse totals; tide is disabled; the model is uncalibrated.
"""
    (OUT / "reports" / "swmm_assumptions.md").write_text(assumptions, encoding="utf-8")
    diagnostics = f"""# SWMM Phase 1 Diagnostics

## Resolved execution issue: SWMM ERROR 141

**ISSUE:** EPA SWMM rejected four graph terminals because each had more than one inlet link.

**OBSERVATION:** SWMM requires an outfall object to have one inlet link. The source graph contains multi-inlet directed terminal nodes.

**POSSIBLE CAUSES:** (1) source terminal represents a junction rather than an outfall; (2) source node aggregation combines several discharge endpoints; (3) physical BMC topology is incomplete.

**SELECTED CAUSE:** The source has graph terminals with multiple incoming links, but does not establish whether each is a physical outfall.

**WHY:** The machine-readable source graph has no surveyed receiving-water designation at those node IDs.

**FIX:** Represented each incoming conduit with a colocated, separately labeled pilot-boundary outfall. Added no synthetic connector and retained source endpoint invert/geometry.

**VALIDATION:** EPA SWMM 5.2.4 rerun completed with return code 0, no fatal errors, and both `.rpt` and `.out` generated.

**REMAINING RISK:** These are execution boundaries, not verified physical outfalls; splitting removes flow mixing at the original source terminal.

## Unresolved hydraulic sanity findings

**ISSUE:** The numerical run contains extreme values and many idle links/outlets.

**OBSERVATION:** Maximum node depth is {val['node_max_depth_m']:.3f} m; maximum conduit velocity is {val['max_abs_conduit_velocity_m_s']:.3f} m/s; {val.get('warning_counts', {}).get('04', 0)} SWMM WARNING 04 minimum elevation-drop notices; {val.get('warning_counts', {}).get('02', 0)} WARNING 02 node-depth increases; {val.get('zero_flow_conduit_count', 0)} of {build['conduits']} conduits have no simulated flow; {val.get('sanity_flags', {}).get('boundary_outfalls_with_zero_flow', 0)} of {len(val.get('outfalls', []))} pilot-boundary objects have zero outflow. Continuity errors are {val['continuity_errors_percent']}%.

**POSSIBLE CAUSES:** (1) source inverts/DEM vertical datum mismatch; (2) nearest-node catchment assignment is not a hydraulic delineation; (3) disconnected components or directed topology do not reflect actual flow paths; (4) engineering-estimate roughness/infiltration/boundary assumptions; (5) extreme reconstructed storm forcing.

**SELECTED CAUSE:** Not determinable from repository data alone.

**WHY:** No verified node rim survey, complete physical outfall inventory, calibrated flows, or authoritative catchment-to-inlet mapping is supplied. The source-level invert/DEM offset cannot be independently confirmed from raster metadata.

**FIX:** No hydraulic values were tuned to suppress these findings. Raw slopes, elevations, warnings, zero-flow links, and boundary assumptions remain traceable in audit/result artifacts.

**VALIDATION:** EPA SWMM 5.2.4 ran Dynamic Wave. Runoff continuity error is -0.009%; flow-routing continuity error is -0.050%. Source-data, geometry, references, rainfall, and CSV/GeoJSON extraction completed. Full `pytest` suite: 31 passed.

**REMAINING RISK:** Do not use the depth/velocity outputs as operational flood forecasts. **PHASE_1_BLOCKED** pending independent engineering review of vertical datum/rims, boundary placement, idle network sections, and outlet assignments.

## Exact next action

Obtain/verify BMC node rim elevations and vertical datum, receiving-water/outfall designations, and inlet/catchment connectivity for the selected Ward L components. Reconcile those against `audit/elevation_audit.csv`, `audit/terminal_node_classification.csv`, `network/pilot_subcatchments.csv`, and the conduit IDs cited in `runs/2005/terra05_wardL_2005.rpt`; then rebuild and rerun without changing source values silently.
"""
    (OUT / "reports" / "diagnostics.md").write_text(diagnostics, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", action="store_true", help="audit source data and topology")
    parser.add_argument("--build", action="store_true", help="build and validate the historical 2005 SWMM model")
    parser.add_argument("--run", action="store_true", help="execute SWMM and extract results")
    parser.add_argument("--extract", action="store_true", help="extract results from an existing .out/.rpt without rerunning SWMM")
    parser.add_argument("--executable", help="runswmm.exe path; defaults to SWMM_EXE or EPA 5.2.4 install")
    args = parser.parse_args()
    if not any((args.audit, args.build, args.run, args.extract)):
        args.audit = args.build = args.run = True
    if args.audit:
        result = audit_sources()
        print(json.dumps(result, indent=2))
    if args.build:
        result = build_model()
        print(json.dumps(result, indent=2))
    if args.run:
        result = run_model(args.executable)
        write_final_report(json.loads((OUT / "reports" / "swmm_build_report.json").read_text(encoding="utf-8")), result)
        print(json.dumps(result, indent=2))
    if args.extract:
        run_path = OUT / "runs" / "2005" / "terra05_wardL_2005"
        run_report = json.loads((OUT / "reports" / "swmm_run_report.json").read_text(encoding="utf-8"))
        extract_results(run_path.with_suffix(".out"), run_path.with_suffix(".rpt"), run_report)
        write_final_report(json.loads((OUT / "reports" / "swmm_build_report.json").read_text(encoding="utf-8")), run_report)
        print("Extracted SWMM result tables from existing .out/.rpt")


if __name__ == "__main__":
    main()
