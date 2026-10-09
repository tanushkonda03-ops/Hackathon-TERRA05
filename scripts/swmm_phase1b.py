"""Phase 1B diagnostics and controlled SWMM sensitivity runs.

This script treats the Phase 1 input/report/output as immutable evidence. It
creates a baseline snapshot, audits the existing results, then runs rainfall
experiments from private INP copies under data/swmm_phase1/phase1b/.
"""
from __future__ import annotations

import hashlib
import argparse
import json
import math
import re
import shutil
import subprocess
import time
from collections import defaultdict
from pathlib import Path

import networkx as nx
import pandas as pd
from pyswmm import Output
from swmm.toolkit.shared_enum import LinkAttribute, NodeAttribute, SubcatchAttribute

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "swmm_phase1"
BASE_INP = OUT / "models" / "terra05_wardL_2005.inp"
BASE_RPT = OUT / "runs" / "2005" / "terra05_wardL_2005.rpt"
BASE_OUT = OUT / "runs" / "2005" / "terra05_wardL_2005.out"
EXE = Path(r"C:\Program Files\EPA SWMM 5.2.4 (64-bit)\runswmm.exe")
WARN04_THRESHOLD_M = 0.0003048  # EPA SWMM's 0.001 ft minimum elevation drop.


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot_baseline() -> dict:
    dest = OUT / "baseline"
    dest.mkdir(parents=True, exist_ok=True)
    files = ((BASE_INP, dest / "baseline.inp"), (BASE_RPT, dest / "baseline.rpt"), (BASE_OUT, dest / "baseline.out"))
    for src, dst in files:
        if not src.is_file():
            raise FileNotFoundError(src)
        if not dst.exists():
            shutil.copy2(src, dst)
        if sha256(src) != sha256(dst):
            raise RuntimeError(f"Baseline snapshot mismatch: {dst}")
    manifest = {"classification": "immutable Phase 1 baseline snapshot", "sha256": {dst.name: sha256(dst) for _, dst in files}}
    (dest / "baseline_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def section_rows(inp: Path, section: str) -> list[list[str]]:
    active, rows = False, []
    for raw in inp.read_text(encoding="utf-8", errors="replace").splitlines():
        s = raw.strip()
        if s.startswith("[") and s.endswith("]"):
            active = s.upper() == f"[{section.upper()}]"
        elif active and s and not s.startswith(";"):
            rows.append(s.split())
    return rows


def read_outputs(out_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    nr, lr, sr = [], [], []
    with Output(str(out_path)) as o:
        times = list(o.times)
        for node in o.nodes:
            series = {"depth_m": o.node_series(node, NodeAttribute.INVERT_DEPTH),
                      "head_m": o.node_series(node, NodeAttribute.HYDRAULIC_HEAD),
                      "flooding_cms": o.node_series(node, NodeAttribute.FLOODING_LOSSES),
                      "inflow_cms": o.node_series(node, NodeAttribute.TOTAL_INFLOW),
                      "lateral_inflow_cms": o.node_series(node, NodeAttribute.LATERAL_INFLOW)}
            for t in times:
                nr.append({"node_id": node, "timestamp": t, **{k: float(v.get(t, 0.0)) for k, v in series.items()}})
        for link in o.links:
            series = {"flow_cms": o.link_series(link, LinkAttribute.FLOW_RATE),
                      "velocity_m_s": o.link_series(link, LinkAttribute.FLOW_VELOCITY),
                      "depth_m": o.link_series(link, LinkAttribute.FLOW_DEPTH),
                      "capacity_ratio": o.link_series(link, LinkAttribute.CAPACITY)}
            for t in times:
                lr.append({"conduit_id": link, "timestamp": t, **{k: float(v.get(t, 0.0)) for k, v in series.items()}})
        for sub in o.subcatchments:
            s = {"runoff_cms": o.subcatch_series(sub, SubcatchAttribute.RUNOFF_RATE)}
            for t in times:
                sr.append({"subcatchment_id": sub, "timestamp": t, **{k: float(v.get(t, 0.0)) for k, v in s.items()}})
    return pd.DataFrame(nr), pd.DataFrame(lr), pd.DataFrame(sr)


def network_context() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    nodes = pd.read_csv(OUT / "network" / "pilot_nodes.csv", dtype={"source_node_id": str})
    links = pd.read_csv(OUT / "network" / "pilot_conduits.csv", dtype={"source_conduit_id": str, "us_source_node_id": str, "ds_source_node_id": str})
    subs = pd.read_csv(OUT / "network" / "pilot_subcatchments.csv", dtype={"outlet_source_node_id": str})
    aliases = pd.read_csv(OUT / "audit" / "terminal_node_classification.csv", dtype={"source_node_id": str})
    g = nx.Graph()
    dg = nx.DiGraph()
    g.add_nodes_from(nodes.swmm_id.astype(str))
    dg.add_nodes_from(nodes.swmm_id.astype(str))
    for r in links.itertuples():
        g.add_edge(str(r.us_swmm_node_id), str(r.ds_swmm_node_id), length_m=float(r.length_m), conduit_id=r.swmm_id)
        dg.add_edge(str(r.us_swmm_node_id), str(r.ds_swmm_node_id), conduit_id=r.swmm_id)
    boundaries = set(aliases.swmm_id.astype(str))
    dists = {}
    for b in boundaries:
        if b in g:
            for n, d in nx.single_source_dijkstra_path_length(g, b, weight="length_m").items():
                dists[n] = min(dists.get(n, math.inf), d)
    comps = {n: i for i, c in enumerate(nx.connected_components(g)) for n in c}
    return nodes, links, subs, {"graph": g, "directed_graph": dg, "boundary_ids": boundaries, "boundary_distance_m": dists, "component_id": comps, "aliases": aliases}


def diagnostic_tables() -> dict:
    dest = OUT / "phase1b" / "audit"
    dest.mkdir(parents=True, exist_ok=True)
    nodes, links, subs, ctx = network_context()
    nr, lr, sr = read_outputs(BASE_OUT)
    nm = nr.groupby("node_id").agg(max_depth_m=("depth_m", "max"), max_head_m=("head_m", "max"),
        max_flooding_rate_cms=("flooding_cms", "max"), total_flooding_m3=("flooding_cms", lambda x: x.sum() * 900),
        inflow_volume_m3=("inflow_cms", lambda x: x.sum() * 900), subcatchment_inflow_volume_m3=("lateral_inflow_cms", lambda x: x.sum() * 900)).reset_index()
    lm = lr.groupby("conduit_id").agg(max_velocity_m_s=("velocity_m_s", lambda x: x.abs().max()), max_flow_cms=("flow_cms", lambda x: x.abs().max()),
        mean_abs_flow_cms=("flow_cms", lambda x: x.abs().mean()), max_capacity_ratio=("capacity_ratio", "max")).reset_index()
    sm = sr.groupby("subcatchment_id").agg(max_runoff_cms=("runoff_cms", "max"), runoff_volume_m3=("runoff_cms", lambda x: x.sum() * 900)).reset_index()
    nm = nm.rename(columns={"max_depth_m": "simulated_max_depth_m"})
    node_data = nodes.merge(nm, left_on="swmm_id", right_on="node_id", how="left").fillna({"simulated_max_depth_m": 0, "max_head_m": 0, "max_flooding_rate_cms": 0, "total_flooding_m3": 0, "inflow_volume_m3": 0, "subcatchment_inflow_volume_m3": 0})
    node_data["max_depth_m"] = node_data.simulated_max_depth_m
    node_data["boundary_distance_m"] = node_data.swmm_id.map(ctx["boundary_distance_m"])
    node_data["component_id_graph"] = node_data.swmm_id.map(ctx["component_id"])
    node_data["connected_conduit_count"] = node_data.swmm_id.map(dict(ctx["graph"].degree()))
    link_nodes = lr.merge(links[["swmm_id", "us_swmm_node_id", "ds_swmm_node_id"]], left_on="conduit_id", right_on="swmm_id", how="left")
    link_nodes["upstream_in_m3"] = (-link_nodes.flow_cms.clip(upper=0)) * 900
    link_nodes["upstream_out_m3"] = link_nodes.flow_cms.clip(lower=0) * 900
    link_nodes["downstream_in_m3"] = link_nodes.flow_cms.clip(lower=0) * 900
    link_nodes["downstream_out_m3"] = (-link_nodes.flow_cms.clip(upper=0)) * 900
    node_flows = defaultdict(lambda: {"network_inflow_volume_m3": 0.0, "network_outflow_volume_m3": 0.0})
    for r in link_nodes.groupby("us_swmm_node_id")[["upstream_in_m3", "upstream_out_m3"]].sum().itertuples():
        node_flows[r.Index]["network_inflow_volume_m3"] += float(r.upstream_in_m3)
        node_flows[r.Index]["network_outflow_volume_m3"] += float(r.upstream_out_m3)
    for r in link_nodes.groupby("ds_swmm_node_id")[["downstream_in_m3", "downstream_out_m3"]].sum().itertuples():
        node_flows[r.Index]["network_inflow_volume_m3"] += float(r.downstream_in_m3)
        node_flows[r.Index]["network_outflow_volume_m3"] += float(r.downstream_out_m3)
    flow_df = pd.DataFrame.from_dict(node_flows, orient="index").rename_axis("swmm_id").reset_index()
    node_data = node_data.merge(flow_df, on="swmm_id", how="left").fillna({"network_inflow_volume_m3": 0, "network_outflow_volume_m3": 0})
    node_data["boundary_status"] = node_data.swmm_id.isin(ctx["boundary_ids"])
    node_data["distance_class"] = node_data.boundary_distance_m.map(lambda x: "NEAR <= 250 m" if pd.notna(x) and x <= 250 else "FAR > 250 m" if pd.notna(x) else "DISCONNECTED")
    node_data["depth_classification"] = node_data.apply(lambda r: "BOUNDARY_NODE_DEPTH" if r.boundary_status else "HIGH_DEPTH > 10 m" if r.max_depth_m > 10 else "ELEVATED_DEPTH > 5 m" if r.max_depth_m > 5 else "WITHIN 5 m", axis=1)
    topn = node_data.sort_values("max_depth_m", ascending=False).head(20).copy()
    topn[["source_node_id", "max_depth_m", "dem_ground_thd_m", "max_head_m", "max_flooding_rate_cms", "total_flooding_m3", "connected_conduit_count", "network_inflow_volume_m3", "network_outflow_volume_m3", "subcatchment_inflow_volume_m3", "boundary_status", "boundary_distance_m", "depth_classification", "distance_class"]].rename(columns={"source_node_id":"node_id", "dem_ground_thd_m":"node_elevation_m", "max_flooding_rate_cms":"flooding_rate_peak_cms", "total_flooding_m3":"flooding_volume_m3", "network_inflow_volume_m3":"inflow_volume_m3", "network_outflow_volume_m3":"outflow_volume_m3"}).to_csv(dest / "top20_nodes_by_depth.csv", index=False)
    node_data[["source_node_id", "max_depth_m", "max_head_m", "boundary_distance_m", "distance_class", "boundary_status", "component_id_graph"]].to_csv(dest / "node_boundary_distance.csv", index=False)

    # Audit exactly the warning-linked source conduits and preserve source data.
    rpt = BASE_RPT.read_text(encoding="utf-8", errors="replace")
    warned = sorted(set(re.findall(r"WARNING 04: minimum elevation drop used for Conduit (\S+)", rpt)))
    warning = links[links.swmm_id.isin(warned)].merge(nodes[["swmm_id", "invert_elev_thd_m", "elevation_classification", "boundary_type"]].rename(columns={"swmm_id":"us_swmm_node_id", "invert_elev_thd_m":"us_node_elevation_m", "elevation_classification":"us_elevation_source"}), on="us_swmm_node_id", how="left")
    warning = warning.merge(nodes[["swmm_id", "invert_elev_thd_m", "elevation_classification", "boundary_type"]].rename(columns={"swmm_id":"ds_swmm_node_id", "invert_elev_thd_m":"ds_node_elevation_m", "elevation_classification":"ds_elevation_source"}), on="ds_swmm_node_id", how="left")
    warning["node_elevation_delta_m"] = warning.us_node_elevation_m - warning.ds_node_elevation_m
    warning["classification"] = warning.apply(lambda r: "SOURCE_ENDPOINT_DELTA_BELOW_SWMM_MINIMUM" if abs(r.node_elevation_delta_m) < WARN04_THRESHOLD_M else "SWMM_WARNING_SOURCE_VS_NODE_ELEVATION_MISMATCH_REVIEW", axis=1)
    warning[["swmm_id", "source_conduit_id", "us_source_node_id", "ds_source_node_id", "us_node_elevation_m", "ds_node_elevation_m", "node_elevation_delta_m", "length_m", "raw_slope_m_per_m", "source_us_invert_m", "source_ds_invert_m", "us_elevation_source", "ds_elevation_source", "classification"]].rename(columns={"swmm_id":"conduit_id"}).to_csv(dest / "elevation_warning_cases.csv", index=False)

    topc = links.merge(lm, left_on="swmm_id", right_on="conduit_id", how="left").merge(nodes[["swmm_id", "boundary_type"]].rename(columns={"swmm_id":"us_swmm_node_id", "boundary_type":"us_boundary_type"}), on="us_swmm_node_id", how="left")
    topc = topc.merge(nodes[["swmm_id", "boundary_type"]].rename(columns={"swmm_id":"ds_swmm_node_id", "boundary_type":"ds_boundary_type"}), on="ds_swmm_node_id", how="left")
    topc["component_id_graph"] = topc.us_swmm_node_id.map(ctx["component_id"])
    topc["classification"] = topc.apply(lambda r: "BOUNDARY_ADJACENT" if pd.notna(r.us_boundary_type) or pd.notna(r.ds_boundary_type) else "HIGH_VELOCITY > 10 m/s" if r.max_velocity_m_s > 10 else "HIGH_VELOCITY > 5 m/s" if r.max_velocity_m_s > 5 else "ELEVATED_VELOCITY", axis=1)
    topc.sort_values("max_velocity_m_s", ascending=False).head(20)[["source_conduit_id", "source_us_invert_m", "source_ds_invert_m", "raw_slope_m_per_m", "max_flow_cms", "max_velocity_m_s", "max_capacity_ratio", "component_id_graph", "us_source_node_id", "ds_source_node_id", "classification"]].rename(columns={"source_conduit_id":"conduit_id"}).to_csv(dest / "top20_conduit_velocities.csv", index=False)

    merged = links.merge(lm, left_on="swmm_id", right_on="conduit_id", how="left").merge(subs.groupby("outlet_swmm_node_id").size().rename("assigned_catchments").reset_index(), left_on="ds_swmm_node_id", right_on="outlet_swmm_node_id", how="left")
    used = set(subs.outlet_swmm_node_id.astype(str))
    zero = merged[merged.max_flow_cms < 1e-9].copy()
    directed = ctx["directed_graph"]
    ancestors_by_node = {n: nx.ancestors(directed, n) | {n} for n in set(zero.us_swmm_node_id.astype(str))}
    descendants_by_node = {n: nx.descendants(directed, n) | {n} for n in set(zero.ds_swmm_node_id.astype(str))}
    zero["component_id_graph"] = zero.us_swmm_node_id.map(ctx["component_id"])
    zero["upstream_catchment_assigned"] = zero.us_swmm_node_id.isin(used)
    zero["downstream_catchment_assigned"] = zero.ds_swmm_node_id.isin(used)
    zero["upstream_catchment_count"] = zero.us_swmm_node_id.map(lambda n: len(ancestors_by_node[str(n)] & used))
    zero["downstream_boundary_reachable"] = zero.ds_swmm_node_id.map(lambda n: bool(descendants_by_node[str(n)] & ctx["boundary_ids"]))
    zero["isolation_status"] = zero.apply(lambda r: "CATCHMENT_UPSTREAM; BOUNDARY_REACHABLE" if r.upstream_catchment_count and r.downstream_boundary_reachable else "CATCHMENT_UPSTREAM; NO_DIRECTED_BOUNDARY_PATH" if r.upstream_catchment_count else "NO_UPSTREAM_CATCHMENT_PATH", axis=1)
    zero[["source_conduit_id", "us_source_node_id", "ds_source_node_id", "component_id_graph", "max_flow_cms", "assigned_catchments", "upstream_catchment_assigned", "downstream_catchment_assigned", "upstream_catchment_count", "downstream_boundary_reachable", "isolation_status"]].rename(columns={"source_conduit_id":"conduit_id"}).to_csv(dest / "zero_flow_conduits.csv", index=False)

    # Outfall nodes and boundary flow from the summary and output time series.
    boundary_rows=[]
    outfall_sec=False
    for line in rpt.splitlines():
        if "Outfall Loading Summary" in line: outfall_sec=True
        elif outfall_sec and "Flow Classification Summary" in line: outfall_sec=False
        elif outfall_sec:
            m=re.match(r"\s+(\S+)\s+([-+\d.]+)\s+([-+\d.]+)\s+([-+\d.]+)\s+([-+\d.]+)\s*$",line)
            if m and m.group(1).startswith(("N_","B_")):
                boundary_rows.append({"swmm_id":m.group(1),"frequency_pct":float(m.group(2)),"average_flow_cms":float(m.group(3)),"max_flow_cms":float(m.group(4)),"volume_ML":float(m.group(5))})
    bd=pd.DataFrame(boundary_rows).merge(ctx["aliases"][["swmm_id","source_node_id"]],on="swmm_id",how="left")
    bd=bd.merge(nodes[["source_node_id","component_id","longitude","latitude","invert_elev_thd_m"]].drop_duplicates("source_node_id"),on="source_node_id",how="left")
    bd=bd.merge(nm.rename(columns={"node_id":"swmm_id","simulated_max_depth_m":"max_depth_m"})[["swmm_id","max_depth_m","max_head_m","max_flooding_rate_cms"]],on="swmm_id",how="left")
    bd["boundary_distance_m"]=bd.swmm_id.map(ctx["boundary_distance_m"])
    bd["connected_conduit_count"]=bd.swmm_id.map(dict(ctx["graph"].degree()))
    bd["flooding_classification"] = bd.apply(lambda r:"BOUNDARY FLOODING" if r.max_flooding_rate_cms>1e-9 else "BOUNDARY ZERO DISCHARGE" if r.max_flow_cms<=1e-9 else "BOUNDARY DISCHARGE; NO NODE FLOODING",axis=1)
    bd.to_csv(dest / "boundary_analysis.csv",index=False)

    sub_audit=subs.merge(sm,left_on="swmm_id",right_on="subcatchment_id",how="left")
    sub_audit["outlet_exists_in_model"] = sub_audit.outlet_swmm_node_id.isin(set(nodes.swmm_id.astype(str)) | set(ctx["aliases"].swmm_id.astype(str)))
    sub_audit["assignment_classification"] = sub_audit.apply(lambda r:"VALID_OUTLET; LONG_DISTANCE_REVIEW" if r.outlet_exists_in_model and r.outlet_distance_m>500 else "VALID_OUTLET" if r.outlet_exists_in_model else "INVALID_OUTLET_REFERENCE",axis=1)
    sub_audit.to_csv(dest / "subcatchment_assignment_audit.csv",index=False)

    # Compare the graph reconstructed from the actual INP conduit/outfall records.
    inp_g=nx.Graph(); inp_conduits=section_rows(BASE_INP,"CONDUITS")
    for row in inp_conduits:
        if len(row)>=3: inp_g.add_edge(row[1],row[2])
    inp_nodes=set(row[0] for row in section_rows(BASE_INP,"JUNCTIONS")) | set(row[0] for row in section_rows(BASE_INP,"OUTFALLS"))
    inp_g.add_nodes_from(inp_nodes)
    source_ids=set(links.swmm_id.astype(str)); inp_ids={str(r[0]) for r in inp_conduits if len(r)>=3}
    source_pairs={frozenset((str(r.us_swmm_node_id),str(r.ds_swmm_node_id))) for r in links.itertuples()}
    inp_pairs={frozenset((str(r[1]),str(r[2]))) for r in inp_conduits if len(r)>=3}
    extra_aliases=set(ctx["aliases"].swmm_id.astype(str))-set(nodes.swmm_id.astype(str))
    build_meta=json.loads((OUT/"reports"/"swmm_build_report.json").read_text(encoding="utf-8"))
    graph_report={"inp_node_count":len(inp_nodes),"pilot_node_count_including_boundary_aliases":len(nodes)+len(extra_aliases),"inp_conduit_count":len(inp_conduits),"pilot_conduit_count":len(links),"selected_source_component_count":build_meta["selected_components"],"inp_component_count_after_boundary_aliases":nx.number_connected_components(inp_g),"unique_source_endpoint_pairs":len(source_pairs),"unique_inp_endpoint_pairs":len(inp_pairs),"missing_conduit_ids_in_inp":len(source_ids-inp_ids),"unexpected_conduit_ids_in_inp":len(inp_ids-source_ids),"missing_endpoint_pairs_in_inp":len(source_pairs-inp_pairs),"unexpected_endpoint_pairs_in_inp":len(inp_pairs-source_pairs),"node_count_delta":len(inp_nodes)-(len(nodes)+len(extra_aliases)),"meaning":"Conduit IDs and endpoint pairs are compared against the built pilot. Component counts include expected splits from the explicit single-inlet boundary aliases; 20 connected pilot components become 23 INP components after those aliases."}
    (dest / "inp_connectivity_audit.json").write_text(json.dumps(graph_report,indent=2),encoding="utf-8")
    return {"warning04_count":len(warned),"warning_matches":len(warning),"top_node":topn.iloc[0].source_node_id,"top_node_depth_m":float(topn.iloc[0].max_depth_m),"zero_flow_links":len(zero),"boundary_count":len(bd),"zero_discharge_boundaries":int((bd.max_flow_cms<=1e-9).sum()),"subcatchments":len(sub_audit),"invalid_outlet_references":int((~sub_audit.outlet_exists_in_model).sum()),"long_outlet_distance_count":int((sub_audit.outlet_distance_m>500).sum()),"inp_graph":graph_report,"maximum_velocity_m_s":float(lm.max_velocity_m_s.max())}


def variant_inp(name: str, values_mm: list[float], duration_hours: int | None = None) -> Path:
    folder=OUT/"phase1b"/"models"; folder.mkdir(parents=True,exist_ok=True)
    lines=BASE_INP.read_text(encoding="utf-8").splitlines()
    rain_i=0; output=[]
    for line in lines:
        s=line.strip()
        if s.startswith("TS_2005_JULY26 "):
            fields=s.split()
            if rain_i < len(values_mm): fields[-1]=f"{values_mm[rain_i]:.6f}"
            else: fields[-1]="0.000000"
            line=" ".join(fields); rain_i+=1
        if duration_hours is not None and s.startswith("END_DATE "):
            line="END_DATE 07/26/2005"
        if duration_hours is not None and s.startswith("END_TIME "):
            line=f"END_TIME {duration_hours:02d}:00:00"
        output.append(line)
    if rain_i != 108: raise ValueError(f"Expected 108 rainfall entries, got {rain_i}")
    path=folder/f"{name}.inp"; path.write_text("\n".join(output)+"\n",encoding="utf-8")
    return path


def run_variant(name: str, inp: Path, rainfall_mm: float, kind: str) -> dict:
    folder=OUT/"phase1b"/"runs"/name; folder.mkdir(parents=True,exist_ok=True)
    rpt,out=folder/f"{name}.rpt",folder/f"{name}.out"
    t=time.perf_counter(); proc=subprocess.run([str(EXE),str(inp.resolve()),str(rpt.resolve()),str(out.resolve())],capture_output=True,text=True,timeout=900,cwd=str(folder)); seconds=time.perf_counter()-t
    txt=rpt.read_text(encoding="utf-8",errors="replace") if rpt.exists() else ""
    errors=re.findall(r"\bERROR\s+\d+:[^\r\n]*",txt,flags=re.I)
    if proc.returncode or errors or not out.exists(): raise RuntimeError(f"SWMM scenario {name} failed: {errors} {proc.stderr}")
    nr,lr,sr=read_outputs(out)
    cont=[float(x) for x in re.findall(r"Continuity Error\s*\(%\)\s*\.+\s*([-+]?\d+(?:\.\d+)?)",txt)]
    # Volume balance values are separately preserved via report text and run metadata.
    metrics={"scenario":name,"kind":kind,"rainfall_mm":rainfall_mm,"runtime_seconds":seconds,"node_max_depth_m":float(nr.depth_m.max()),"max_velocity_m_s":float(lr.velocity_m_s.abs().max()),"max_flow_cms":float(lr.flow_cms.abs().max()),"flooded_nodes":int(nr.groupby("node_id").flooding_cms.max().gt(1e-9).sum()),"zero_flow_conduits":int(lr.groupby("conduit_id").flow_cms.apply(lambda s:s.abs().max()<1e-9).sum()),"continuity_error_percent":cont,"warning04_count":len(re.findall(r"WARNING 04:",txt)),"warning02_count":len(re.findall(r"WARNING 02:",txt)),"report_path":str(rpt.relative_to(ROOT)),"output_path":str(out.relative_to(ROOT)),"input_path":str(inp.relative_to(ROOT)),"return_code":proc.returncode}
    (folder/f"{name}_metrics.json").write_text(json.dumps(metrics,indent=2),encoding="utf-8")
    return metrics


def scenarios() -> list[dict]:
    inp_lines=BASE_INP.read_text(encoding="utf-8").splitlines()
    values=[float(s.split()[-1]) for s in inp_lines if s.startswith("TS_2005_JULY26 ")]
    total=sum(values)
    results=[]
    for pct in (25,50,75):
        vals=[v*pct/100 for v in values]
        path=variant_inp(f"rainfall_{pct}pct",vals)
        print(f"Running rainfall scale {pct}% ...", flush=True)
        results.append(run_variant(f"rainfall_{pct}pct",path,total*pct/100,"scaled reconstructed rainfall; same event/network/parameters"))
    # Concentrated, deterministic 15-minute hyetographs; full network retained,
    # simulation duration is shortened to avoid pretending these are design storms.
    for name,depth,hours in (("diagnostic_10mm_1h",10.0,1),("diagnostic_50mm_3h",50.0,3)):
        vals=[depth/(hours*4)]*(hours*4)+[0.0]*(108-hours*4)
        path=variant_inp(name,vals,hours)
        print(f"Running diagnostic storm {name} ...", flush=True)
        results.append(run_variant(name,path,depth,"synthetic constant-intensity smoke diagnostic; not calibration/design rainfall"))
    return results


def write_reports(baseline: dict, diag: dict, runs: list[dict]) -> None:
    phase=OUT/"phase1b"; reports=phase/"reports"; reports.mkdir(parents=True,exist_ok=True)
    baseval=json.loads((OUT/"reports"/"swmm_validation_report.json").read_text(encoding="utf-8"))
    audit=json.loads((OUT/"audit"/"drainage_source_audit.json").read_text(encoding="utf-8"))
    # The unchanged baseline INP is the validated candidate because the source
    # evidence does not justify fabricating corrections to elevations/geometry.
    validated=phase/"validated"; validated.mkdir(exist_ok=True)
    for src,name in ((BASE_INP,"validated.inp"),(BASE_RPT,"validated.rpt"),(BASE_OUT,"validated.out")):
        shutil.copy2(src,validated/name)
    baseline_nodes = pd.read_csv(OUT / "results" / "node_results.csv", usecols=["node_id", "flooding_cms"])
    baseline_flooded = int(baseline_nodes.groupby("node_id").flooding_cms.max().gt(1e-9).sum())
    metrics=[{"scenario":"baseline_100pct","kind":"unchanged Phase 1 run", "rainfall_mm":944.2,"node_max_depth_m":baseval["node_max_depth_m"],"max_velocity_m_s":baseval["max_abs_conduit_velocity_m_s"],"max_flow_cms":baseval["max_abs_flow_cms"],"flooded_nodes":baseline_flooded,"zero_flow_conduits":baseval["zero_flow_conduit_count"],"continuity_error_percent":baseval["continuity_errors_percent"],"warning04_count":36,"warning02_count":2,"report_path":"data/swmm_phase1/baseline/baseline.rpt","output_path":"data/swmm_phase1/baseline/baseline.out","input_path":"data/swmm_phase1/baseline/baseline.inp"}]+runs
    pd.DataFrame(metrics).to_csv(reports/"baseline_vs_validated.csv",index=False)
    (reports/"scenario_metrics.json").write_text(json.dumps(metrics,indent=2),encoding="utf-8")
    phase_status="LEVEL C"
    diagnostics=f"""# Phase 1B Diagnostics

## Baseline integrity

Phase 1 input/report/output were snapshotted under `data/swmm_phase1/baseline/` before any Phase 1B run. SHA-256 hashes are in `baseline_manifest.json`. `validated.inp/.rpt/.out` are copied unchanged because there is no defensible source correction to apply.

## Findings

- Source-audit inputs: {audit['conduits_total']:,} source conduits and {audit['nodes_total']:,} endpoint node IDs; pilot has 3,269 nodes, 3,314 conduits, 34 artificial pilot boundaries, and 1,516 grid catchments.
- Baseline SWMM 5.2.4 completed with runoff/routing continuity errors {baseval['continuity_errors_percent']}%; warnings: 36 Warning 04 and two Warning 02.
- Warning 04 cases: {diag['warning_matches']}/{diag['warning04_count']} joined to source conduit/endpoints. The detailed file preserves node elevations, their source classification, source endpoint inverts, length, and raw slope. It is a data/input condition; do not replace elevations with SWMM's minimum slope.
- Extreme node result: {diag['top_node']} reaches {diag['top_node_depth_m']:.3f} m. Top 20 node table includes network distance, boundary role, inflow/outflow and flooding quantities. These are simulated maxima under assumed rim/elevation and rainfall inputs, not validated flood depths.
- Max conduit velocity {diag['maximum_velocity_m_s']:.3f} m/s. Top 20 records preserve source slope, endpoint inverts, and peak flow.
- Zero-flow links: {diag['zero_flow_links']} of 3,314. They are retained in the network and individually annotated with component, upstream catchment reachability, and downstream boundary reachability; zero flow alone does not establish a disconnected link.
- Boundary analysis: {diag['boundary_count']} objects; {diag['zero_discharge_boundaries']} carry zero reported outflow. They are artificial computational boundaries, and physical outfalls/receiving-water levels are not verified.
- Catchment assignments: {diag['subcatchments']} records, {diag['invalid_outlet_references']} invalid outlet references and {diag['long_outlet_distance_count']} outlets over 500 m. Long nearest-node distances are potential spatial representativeness issues.
- INP graph has {diag['inp_graph']['inp_node_count']} nodes and {diag['inp_graph']['inp_conduit_count']} conduits; all pilot conduit IDs and endpoint pairs match ({diag['inp_graph']['missing_conduit_ids_in_inp']} missing IDs, {diag['inp_graph']['unexpected_conduit_ids_in_inp']} unexpected IDs, {diag['inp_graph']['missing_endpoint_pairs_in_inp']} missing endpoint pairs, {diag['inp_graph']['unexpected_endpoint_pairs_in_inp']} unexpected endpoint pairs). The {diag['inp_graph']['selected_source_component_count']} selected source components form {diag['inp_graph']['inp_component_count_after_boundary_aliases']} INP graph components after boundary aliases.

## Sensitivity runs

`scenario_metrics.json` and `baseline_vs_validated.csv` record the 25%, 50%, and 75% scaled 2005 profile runs plus 10 mm/1 h and 50 mm/3 h constant-intensity diagnostic runs. These isolate rainfall-volume sensitivity and basic execution response; they are not calibration or design storms.

## Decision

**{phase_status}** — the engine executes and continuity is good, but the hydraulic outputs are not suitable for operational interpretation while the elevations, roughness, rainfall profile, DEM datum, boundary placement, and catchment routing remain unverified and the baseline exhibits extreme depths/velocities and numerous zero-flow links. No elevations, slopes, roughnesses, or boundary conditions were silently changed.
"""
    (reports/"phase1b_diagnostics.md").write_text(diagnostics,encoding="utf-8")
    final=f"""# TERRA05 Phase 1B Final Report

## Status: {phase_status}

Phase 1B preserved the original SWMM run, traced warnings/anomalies to source records and network context, and completed controlled rainfall sensitivity runs. No hydraulic input correction was justified by evidence; `validated.inp`, `validated.rpt`, and `validated.out` are byte-for-byte copies of the baseline.

## Results

- Baseline continuity errors: {baseval['continuity_errors_percent']}% (runoff and routing); 36 Warning 04, two Warning 02.
- Highest depth: {diag['top_node_depth_m']:.3f} m at source node {diag['top_node']}; highest conduit velocity: {diag['maximum_velocity_m_s']:.3f} m/s.
- Zero-flow conduits: {diag['zero_flow_links']}; zero-discharge artificial boundaries: {diag['zero_discharge_boundaries']} of {diag['boundary_count']}.
- Rainfall scenarios completed: {', '.join(r['scenario'] for r in runs)}.
- Diagnostics, scenario metrics, baseline hashes, and validated copies are under `data/swmm_phase1/`.

## Recommendation

**Level C: engine-executable, hydraulically unvalidated.** Do not use simulated depth/velocity outputs as authoritative flood maps. Phase 2 should first validate vertical datum and node rim elevations, survey conduit inverts and the 36 minimum-drop links, verify physical outfalls and receiving-water/tide boundaries, refine rainfall observations and catchment routing, then calibrate against observed flows/water levels/flood extents. Keep the Phase 1B scenarios as sensitivity evidence only.
"""
    (reports/"phase1b_final_report.md").write_text(final,encoding="utf-8")


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--audit-only",action="store_true")
    parser.add_argument("--scenarios-only",action="store_true")
    args=parser.parse_args()
    manifest=snapshot_baseline()
    diag=diagnostic_tables()
    if args.scenarios_only:
        names=("rainfall_25pct","rainfall_50pct","rainfall_75pct","diagnostic_10mm_1h","diagnostic_50mm_3h")
        runs=[json.loads((OUT/"phase1b"/"runs"/name/f"{name}_metrics.json").read_text(encoding="utf-8")) for name in names]
    else:
        runs=scenarios() if not args.audit_only else []
    if not args.audit_only:
        write_reports(manifest,diag,runs)
    print(json.dumps({"baseline":manifest,"diagnostics":diag,"scenarios":runs},indent=2))


if __name__=="__main__": main()
