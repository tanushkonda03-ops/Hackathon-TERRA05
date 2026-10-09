"""
build_swmm_inp.py
==================
Generates a syntactically valid EPA-SWMM input file (`models/ward_L_kurla.inp`)
from the Ward L pilot CSV datasets and 2005 rainfall time series.

Key Features:
- Preserves exact source node IDs (including trailing '!') and conduit directions.
- Assembles all required SWMM sections: [OPTIONS], [RAINGAGES], [TIMESERIES],
  [JUNCTIONS], [OUTFALLS], [CONDUITS], [XSECTIONS], [SUBCATCHMENTS], [SUBAREAS],
  [INFILTRATION], [COORDINATES], [REPORT].
- Flags adverse slope conduits (e.g. C_28238, C_29481) without altering elevations.
- Performs built-in referential integrity and syntax validation checks.
- Runs simulation via PySWMM (if available) and reports dynamic wave hydraulics.
"""

from pathlib import Path
import pandas as pd
import re

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PILOT_DIR = PROJECT_ROOT / "data" / "swmm_ready" / "pilot_ward_L"
TIMESERIES_FILE = PROJECT_ROOT / "data" / "swmm_ready" / "timeseries_2005_july26.dat"
OUTPUT_INP = PROJECT_ROOT / "models" / "ward_L_kurla.inp"

def generate_swmm_inp():
    print("=" * 75)
    print("GENERATING EPA-SWMM MODEL: Ward L Kurla Pilot (models/ward_L_kurla.inp)")
    print("=" * 75)
    
    OUTPUT_INP.parent.mkdir(parents=True, exist_ok=True)
    
    # Load Pilot CSV Datasets
    print("\n[1/5] Loading Ward L pilot CSV tables...")
    df_junc = pd.read_csv(PILOT_DIR / "swmm_junctions_ward_L.csv")
    df_out = pd.read_csv(PILOT_DIR / "swmm_outfalls_ward_L.csv")
    df_cond = pd.read_csv(PILOT_DIR / "swmm_conduits_ward_L.csv")
    df_sc = pd.read_csv(PILOT_DIR / "swmm_subcatchments_ward_L.csv")
    
    ts_text = TIMESERIES_FILE.read_text().strip()

    node_inverts = dict(zip(df_junc["junction_id"].astype(str), df_junc["invert_elev_thd_m"]))
    node_inverts.update(dict(zip(df_out["outfall_id"].astype(str), df_out["invert_elev_thd_m"])))
    
    print(f"  Loaded {len(df_junc):,} junctions")
    print(f"  Loaded {len(df_out):,} outfalls")
    print(f"  Loaded {len(df_cond):,} conduits")
    print(f"  Loaded {len(df_sc):,} subcatchments")
    
    # Identify adverse slope conduits
    adv_conduits = df_cond[df_cond["us_invert_thd_m"] < df_cond["ds_invert_thd_m"]]
    print(f"\n[2/5] Adverse Slope Audit:")
    print(f"  Found {len(adv_conduits)} conduits with US_Invert < DS_Invert:")
    for _, r in adv_conduits.iterrows():
        print(f"    - Conduit {r['conduit_id']}: US={r['us_node_id']} ({r['us_invert_thd_m']}m THD) -> DS={r['ds_node_id']} ({r['ds_invert_thd_m']}m THD), Length={r['length_m']}m")
    print("  Note: Original conduit directions and invert elevations are strictly preserved for Dynamic Wave routing.")
    
    print("\n[3/5] Assembling EPA-SWMM .inp file contents...")
    lines = []
    
    # 1. TITLE
    lines.append("[TITLE]")
    lines.append(";;Project: Mumbai Urban Stormwater Flood Prediction System")
    lines.append(";;Model: Ward L Kurla Hydrologic & Dynamic Wave Hydraulic Simulation")
    lines.append(";;Rainfall: 944.2 mm 3-hour totals disaggregated to 15-minute depths with static triangular weights")
    lines.append(";;Rainfall intervals are reconstructed, not measured 15-minute observations")
    lines.append(";;Outfalls: FREE boundaries as specified in source CSV; tide curve metadata ignored (no tide data)")
    lines.append("")
    
    # 2. OPTIONS
    lines.append("[OPTIONS]")
    lines.append("FLOW_UNITS           CMS")
    lines.append("INFILTRATION         HORTON")
    lines.append("FLOW_ROUTING         DYNWAVE")
    lines.append("LINK_OFFSETS         DEPTH")
    lines.append("ALLOW_PONDING        YES")
    lines.append("MIN_SLOPE            0")
    lines.append("START_DATE           07/26/2005")
    lines.append("START_TIME           00:00:00")
    lines.append("END_DATE             07/27/2005")
    lines.append("END_TIME             03:00:00")
    lines.append("REPORT_START_DATE    07/26/2005")
    lines.append("REPORT_START_TIME    00:00:00")
    lines.append("SWEEP_START          01/01")
    lines.append("SWEEP_END            12/31")
    lines.append("DRY_DAYS             0")
    lines.append("REPORT_STEP          00:15:00")
    lines.append("WET_STEP             00:05:00")
    lines.append("DRY_STEP             01:00:00")
    lines.append("ROUTING_STEP         00:00:05")
    lines.append("INERTIAL_DAMPING     PARTIAL")
    lines.append("NORMAL_FLOW_LIMITED  BOTH")
    lines.append("FORCE_MAIN_EQUATION  H-W")
    lines.append("VARIABLE_STEP        0.75")
    lines.append("MINIMUM_STEP         0.5")
    lines.append("MAX_TRIALS           8")
    lines.append("HEAD_TOLERANCE       0.001")
    lines.append("")
    
    # 3. RAINGAGES
    lines.append("[RAINGAGES]")
    lines.append(";;Name           Format     Interval Catchnum   Source")
    lines.append("RG_SANTACRUZ     VOLUME     0:15     1.0        TIMESERIES TS_2005_JULY26")
    lines.append("")
    
    # 4. JUNCTIONS
    lines.append("[JUNCTIONS]")
    lines.append(";;Name           Elevation  MaxDepth   InitDepth  SurDepth   Apond")
    for _, r in df_junc.iterrows():
        nid = str(r["junction_id"])
        inv = round(float(r["invert_elev_thd_m"]), 3)
        max_d = round(float(r["max_depth_m"]), 3)
        apond = round(float(r.get("ponded_area_m2", 100.0)), 1)
        lines.append(f"{nid:<16} {inv:<10.3f} {max_d:<10.3f} 0.000      0.000      {apond:<8.1f}")
    lines.append("")
    
    # 5. OUTFALLS
    lines.append("[OUTFALLS]")
    lines.append(";;Name           Elevation  Type       StageData  Gated")
    for _, r in df_out.iterrows():
        nid = str(r["outfall_id"])
        inv = round(float(r["invert_elev_thd_m"]), 3)
        outfall_type = str(r["outfall_type"]).strip().upper()
        if outfall_type != "FREE":
            raise ValueError(f"Unsupported source outfall type for provisional MVP: {nid}={outfall_type}")
        lines.append(f"{nid:<16} {inv:<10.3f} FREE                  {str(r['gated']).upper()}")
    lines.append("")
    
    # 6. CONDUITS
    lines.append("[CONDUITS]")
    lines.append(";;Name           From Node        To Node          Length     Roughness  InOffset   OutOffset  InitFlow   MaxFlow")
    for _, r in df_cond.iterrows():
        cid = str(r["conduit_id"])
        u_id = str(r["us_node_id"])
        d_id = str(r["ds_node_id"])
        length = round(float(r["length_m"]), 2)
        n_val = round(float(r["manning_n"]), 4)
        upstream_offset = float(r["us_invert_thd_m"]) - float(node_inverts[u_id])
        downstream_offset = float(r["ds_invert_thd_m"]) - float(node_inverts[d_id])
        if upstream_offset < -0.001 or downstream_offset < -0.001:
            raise ValueError(f"Negative SWMM depth offset for conduit {cid}; source inverts cannot be represented")
        lines.append(f"{cid:<16} {u_id:<16} {d_id:<16} {length:<10.2f} {n_val:<10.4f} {max(upstream_offset, 0):<10.3f} {max(downstream_offset, 0):<10.3f} 0.0000     0.0000")
    lines.append("")
    
    # 7. XSECTIONS
    lines.append("[XSECTIONS]")
    lines.append(";;Link           Shape            Geom1      Geom2      Geom3      Geom4      Barrels    Culvert")
    for _, r in df_cond.iterrows():
        cid = str(r["conduit_id"])
        shape = str(r["shape"]).upper()
        h = round(float(r["geom1_height_m"]), 3)
        w = round(float(r["geom2_width_m"]), 3)
        barrels = int(r.get("barrels", 1))
        lines.append(f"{cid:<16} {shape:<16} {h:<10.3f} {w:<10.3f} 0.0000     0.0000     {barrels:<10d}")
    lines.append("")
    
    # 8. SUBCATCHMENTS
    lines.append("[SUBCATCHMENTS]")
    lines.append(";;Name           Rain Gage        Outlet           Area       %Imperv    Width      %Slope     CurbLen    SnowPack")
    for _, r in df_sc.iterrows():
        sid = str(r["subcatchment_id"])
        rg = str(r.get("raingage_id", "RG_SANTACRUZ"))
        outlet = str(r["outlet_node_id"])
        area = round(float(r["area_ha"]), 4)
        imperv = round(float(r["pct_imperv"]), 2)
        width = round(float(r["width_m"]), 2)
        slope = round(float(r["pct_slope"]), 2)
        lines.append(f"{sid:<16} {rg:<16} {outlet:<16} {area:<10.4f} {imperv:<10.2f} {width:<10.2f} {slope:<10.2f} 0")
    lines.append("")
    
    # 9. SUBAREAS
    lines.append("[SUBAREAS]")
    lines.append(";;Subcatchment   N-Imperv   N-Perv     S-Imperv   S-Perv     PctZero    RouteTo    PctRouted")
    for _, r in df_sc.iterrows():
        sid = str(r["subcatchment_id"])
        n_imp = round(float(r.get("n_imperv", 0.015)), 4)
        n_perv = round(float(r.get("n_perv", 0.20)), 4)
        s_imp = round(float(r.get("s_imperv_mm", 2.0)), 2)
        s_perv = round(float(r.get("s_perv_mm", 5.0)), 2)
        pct_zero = round(float(r.get("pct_zero_imperv", 25.0)), 2)
        route_to = str(r.get("subarea_routing", "OUTLET"))
        lines.append(f"{sid:<16} {n_imp:<10.4f} {n_perv:<10.4f} {s_imp:<10.2f} {s_perv:<10.2f} {pct_zero:<10.2f} {route_to}")
    lines.append("")
    
    # 10. INFILTRATION
    lines.append("[INFILTRATION]")
    lines.append(";;Subcatchment   MaxRate    MinRate    Decay      DryTime    MaxInfil")
    for _, r in df_sc.iterrows():
        sid = str(r["subcatchment_id"])
        f_max = round(float(r.get("horton_max_rate_mmhr", 50.0)), 2)
        f_min = round(float(r.get("horton_min_rate_mmhr", 6.2)), 2)
        decay = round(float(r.get("horton_decay_rate_hr", 3.0)), 2)
        dry = round(float(r.get("horton_dry_time_days", 7.0)), 2)
        lines.append(f"{sid:<16} {f_max:<10.2f} {f_min:<10.2f} {decay:<10.2f} {dry:<10.2f} 0.00")
    lines.append("")
    
    # 11. TIMESERIES
    lines.append("[TIMESERIES]")
    lines.append(ts_text)
    lines.append("")
    
    # 12. COORDINATES
    lines.append("[COORDINATES]")
    lines.append(";;Node           X-Coord          Y-Coord")
    for _, r in df_junc.iterrows():
        nid = str(r["junction_id"])
        x = round(float(r["x_utm43"]), 2)
        y = round(float(r["y_utm43"]), 2)
        lines.append(f"{nid:<16} {x:<14.2f} {y:<14.2f}")
    for _, r in df_out.iterrows():
        nid = str(r["outfall_id"])
        x = round(float(r["x_utm43"]), 2)
        y = round(float(r["y_utm43"]), 2)
        lines.append(f"{nid:<16} {x:<14.2f} {y:<14.2f}")
    lines.append("")
    
    # 13. REPORT
    lines.append("[REPORT]")
    lines.append("INPUT                YES")
    lines.append("CONTROLS             NO")
    lines.append("SUBCATCHMENTS        ALL")
    lines.append("NODES                ALL")
    lines.append("LINKS                ALL")
    lines.append("")

    
    # Write output .inp file
    with open(OUTPUT_INP, "w") as f:
        f.write("\n".join(lines) + "\n")
        
    print(f"\n[4/5] Successfully generated EPA-SWMM model: {OUTPUT_INP}")
    print(f"  File Size: {OUTPUT_INP.stat().st_size / 1024:.1f} KB ({len(lines):,} lines)")
    print(f"  Objects: {len(df_sc):,} subcatchments, {len(df_junc):,} junctions, {len(df_out):,} outfalls, {len(df_cond):,} conduits")
    print("  Assumptions: FREE outfalls (source type); no tide curve used; static-triangle 15-minute rainfall reconstruction")
    print("  Link offsets preserve source conduit endpoint inverts; adverse-slope directions remain unchanged")

def validate_swmm_inp():
    print("\n[5/5] Running built-in validation suite on generated .inp file...")
    
    if not OUTPUT_INP.exists():
        raise FileNotFoundError(f"Input file not found: {OUTPUT_INP}")
        
    text = OUTPUT_INP.read_text()
    
    # Parse sections
    sections = {}
    current_sec = None
    
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(";;"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current_sec = line[1:-1].upper()
            sections[current_sec] = []
        elif current_sec:
            sections[current_sec].append(line)
            
    required_sections = [
        "OPTIONS", "RAINGAGES", "TIMESERIES", "JUNCTIONS", "OUTFALLS",
        "CONDUITS", "XSECTIONS", "SUBCATCHMENTS", "SUBAREAS", "INFILTRATION", "COORDINATES"
    ]
    
    for sec in required_sections:
        assert sec in sections, f"Missing required section [{sec}] in .inp file!"
    print("  [PASS] All 11 required SWMM sections present")
    
    # Check node and conduit ID sets
    junc_ids = set(l.split()[0] for l in sections["JUNCTIONS"])
    out_ids = set(l.split()[0] for l in sections["OUTFALLS"])
    all_nodes = junc_ids.union(out_ids)
    
    assert len(junc_ids.intersection(out_ids)) == 0, "Node IDs overlap between junctions and outfalls!"
    print(f"  [PASS] Node sets non-overlapping ({len(junc_ids)} junctions, {len(out_ids)} outfalls)")
    
    # Check conduit endpoints
    cond_ids = set()
    for l in sections["CONDUITS"]:
        parts = l.split()
        cid, u, v = parts[0], parts[1], parts[2]
        assert cid not in cond_ids, f"Duplicate conduit ID: {cid}"
        cond_ids.add(cid)
        assert u in all_nodes, f"Conduit {cid} upstream node {u} missing!"
        assert v in all_nodes, f"Conduit {cid} downstream node {v} missing!"
    print(f"  [PASS] All {len(cond_ids)} conduits have valid endpoint nodes")
    
    # Check subcatchment outlets
    sc_ids = set()
    for l in sections["SUBCATCHMENTS"]:
        parts = l.split()
        sid, rg, outlet = parts[0], parts[1], parts[2]
        assert sid not in sc_ids, f"Duplicate subcatchment ID: {sid}"
        sc_ids.add(sid)
        assert rg == "RG_SANTACRUZ", f"Subcatchment {sid} raingage mismatch: {rg}"
        assert outlet in all_nodes, f"Subcatchment {sid} outlet node {outlet} missing!"
    print(f"  [PASS] All {len(sc_ids)} subcatchments reference valid rain gage and outlet nodes")
    
    # Check timeseries date parsing
    ts_count = 0
    for l in sections["TIMESERIES"]:
        if l.startswith(";") or not l: continue
        parts = l.split()
        if len(parts) >= 4 and parts[0] == "TS_2005_JULY26":
            ts_count += 1
    assert ts_count > 0, "No parseable timeseries data found!"
    print(f"  [PASS] Timeseries parsed successfully ({ts_count} 15-minute hyetograph records)")

def run_simulation_if_available():
    print("\n" + "=" * 75)
    print("SIMULATION EXECUTION CHECK")
    print("=" * 75)
    
    try:
        from pyswmm import Simulation
        print("PySWMM engine detected! Executing dynamic wave simulation...")
        
        sim = Simulation(str(OUTPUT_INP))
        sim.execute()
        
        print("\n[SUCCESS] PySWMM Dynamic Wave simulation completed cleanly!")
        rpt_file = OUTPUT_INP.with_suffix(".rpt")
        if rpt_file.exists():
            print(f"  Report generated: {rpt_file} ({rpt_file.stat().st_size / 1024:.1f} KB)")
            report_text = rpt_file.read_text(errors="replace")
            warnings = re.findall(r"^\s*WARNING\s+\d+:.*$", report_text, re.MULTILINE)
            errors = re.findall(r"^\s*ERROR\s+\d+:.*$", report_text, re.MULTILINE)
            continuity = re.findall(r"Continuity Error \(%\).*?([+-]?\d+(?:\.\d+)?)\s*$", report_text, re.MULTILINE)
            print(f"  Runtime diagnostics: {len(warnings)} SWMM warnings, {len(errors)} SWMM errors")
            for warning in warnings[:3]:
                print(f"    {warning.strip()}")
            if len(warnings) > 3:
                print(f"    ... and {len(warnings) - 3} more warnings")
            if continuity:
                print(f"  Runoff/routing continuity errors: {', '.join(f'{value}%' for value in continuity)}")
            
    except ImportError:
        print("PySWMM module not installed in Python environment.")
        print("To run the simulation, install PySWMM via: pip install pyswmm")
    except Exception as e:
        print(f"[ERROR] Simulation run failed: {e}")

if __name__ == "__main__":
    generate_swmm_inp()
    validate_swmm_inp()
    run_simulation_if_available()
