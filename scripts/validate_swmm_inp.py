"""
validate_swmm_inp.py
====================
Standalone validation test suite for generated EPA-SWMM .inp input files.

Verifies:
1. Presence of all required SWMM input file sections.
2. Referential integrity of subcatchment outlets and conduit endpoints.
3. Absence of duplicate IDs within section tables.
4. Absence of node ID collisions between junctions and outfalls.
5. Parseability of rainfall timeseries dates and values.
6. Identification and logging of adverse slope conduits (US_Invert < DS_Invert).
"""

from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INP = PROJECT_ROOT / "models" / "ward_L_kurla.inp"
PILOT_DIR = PROJECT_ROOT / "data" / "swmm_ready" / "pilot_ward_L"
RAINFALL_FILE = PROJECT_ROOT / "data" / "swmm_ready" / "timeseries_2005_july26.dat"

def validate_inp_file(inp_path=DEFAULT_INP):
    print("=" * 75)
    print(f"VALIDATING EPA-SWMM INPUT FILE: {inp_path}")
    print("=" * 75)
    
    if not inp_path.exists():
        print(f"[ERROR] Input file not found: {inp_path}")
        sys.exit(1)
        
    text = inp_path.read_text()
    
    # 1. Section Parsing
    sections = {}
    current_sec = None
    
    for line in text.splitlines():
        line_clean = line.strip()
        if not line_clean or line_clean.startswith(";"):
            continue
        if line_clean.startswith("[") and line_clean.endswith("]"):
            current_sec = line_clean[1:-1].upper()
            sections[current_sec] = []
        elif current_sec:
            sections[current_sec].append(line_clean)
            
    required_sections = [
        "OPTIONS", "RAINGAGES", "TIMESERIES", "JUNCTIONS", "OUTFALLS",
        "CONDUITS", "XSECTIONS", "SUBCATCHMENTS", "SUBAREAS", "INFILTRATION", "COORDINATES"
    ]
    
    missing_sections = [s for s in required_sections if s not in sections]
    assert len(missing_sections) == 0, f"Missing required sections: {missing_sections}"
    print(f"[PASS] All {len(required_sections)} required SWMM sections are present")
    options = {parts[0].upper(): parts[1].upper() for line in sections["OPTIONS"] if len(parts := line.split()) >= 2}
    assert options.get("FLOW_ROUTING") == "DYNWAVE", "Model is not configured for Dynamic Wave routing"
    assert options.get("INFILTRATION") == "HORTON", "Model is not configured for Horton infiltration"
    
    # 2. Node Set Uniqueness & Non-Overlap
    junc_ids = set()
    dup_juncs = set()
    junc_inverts = {}
    for l in sections["JUNCTIONS"]:
        parts = l.split()
        nid = parts[0]
        if nid in junc_ids: dup_juncs.add(nid)
        junc_ids.add(nid)
        junc_inverts[nid] = float(parts[1])
        
    out_ids = set()
    dup_outs = set()
    out_inverts = {}
    for l in sections["OUTFALLS"]:
        parts = l.split()
        nid = parts[0]
        if nid in out_ids: dup_outs.add(nid)
        out_ids.add(nid)
        out_inverts[nid] = float(parts[1])
        
    assert len(dup_juncs) == 0, f"Duplicate junction IDs found: {dup_juncs}"
    assert len(dup_outs) == 0, f"Duplicate outfall IDs found: {dup_outs}"
    
    overlap = junc_ids.intersection(out_ids)
    assert len(overlap) == 0, f"Node IDs overlap between junctions and outfalls: {overlap}"
    print(f"[PASS] Node sets non-overlapping ({len(junc_ids):,} junctions, {len(out_ids):,} outfalls)")
    
    all_nodes = junc_ids.union(out_ids)
    all_inverts = {**junc_inverts, **out_inverts}
    source_junctions = pd.read_csv(PILOT_DIR / "swmm_junctions_ward_L.csv", dtype={"junction_id": str})
    source_outfalls = pd.read_csv(PILOT_DIR / "swmm_outfalls_ward_L.csv", dtype={"outfall_id": str})
    assert junc_ids == set(source_junctions["junction_id"]), "Generated junction IDs differ from the source CSV"
    assert out_ids == set(source_outfalls["outfall_id"]), "Generated outfall IDs differ from the source CSV"
    
    # 3. Conduit Endpoints, Source Direction, and Endpoint Inverts
    cond_ids = set()
    dup_conds = set()
    adv_slopes = []
    conduits_by_id = {}

    source_conduits = pd.read_csv(PILOT_DIR / "swmm_conduits_ward_L.csv", dtype={"conduit_id": str, "us_node_id": str, "ds_node_id": str})
    for l in sections["CONDUITS"]:
        parts = l.split()
        cid, u, v, length = parts[0], parts[1], parts[2], float(parts[3])
        upstream_offset = float(parts[5])
        downstream_offset = float(parts[6])
        if cid in cond_ids: dup_conds.add(cid)
        cond_ids.add(cid)
        conduits_by_id[cid] = (u, v, length, upstream_offset, downstream_offset)
        
        assert u in all_nodes, f"Conduit {cid} upstream node {u} missing from node set!"
        assert v in all_nodes, f"Conduit {cid} downstream node {v} missing from node set!"

    source_by_id = source_conduits.set_index("conduit_id")
    assert cond_ids == set(source_by_id.index), "Generated conduit IDs differ from the source CSV"
    for cid, (u, v, length, upstream_offset, downstream_offset) in conduits_by_id.items():
        source = source_by_id.loc[cid]
        assert (u, v) == (str(source["us_node_id"]), str(source["ds_node_id"])), f"Conduit {cid} direction/endpoints changed"
        assert abs(length - float(source["length_m"])) <= 0.011, f"Conduit {cid} length changed"
        reconstructed_us = all_inverts[u] + upstream_offset
        reconstructed_ds = all_inverts[v] + downstream_offset
        assert abs(reconstructed_us - float(source["us_invert_thd_m"])) <= 0.0011, f"Conduit {cid} upstream invert changed"
        assert abs(reconstructed_ds - float(source["ds_invert_thd_m"])) <= 0.0011, f"Conduit {cid} downstream invert changed"
        if float(source["us_invert_thd_m"]) < float(source["ds_invert_thd_m"]):
            adv_slopes.append((cid, u, v, float(source["us_invert_thd_m"]), float(source["ds_invert_thd_m"]), length))
            
    assert len(dup_conds) == 0, f"Duplicate conduit IDs found: {dup_conds}"
    assert {row[0] for row in adv_slopes} == {"C_28238", "C_29481"}, f"Unexpected adverse-slope conduit set: {[row[0] for row in adv_slopes]}"
    print(f"[PASS] All {len(cond_ids):,} conduits preserve source IDs, direction, endpoints, and invert elevations")
    
    print(f"\n  [ADVERSE SLOPE AUDIT] Identified {len(adv_slopes)} adverse-slope conduits (US_Invert < DS_Invert):")
    for cid, u, v, u_inv, v_inv, length in adv_slopes:
        print(f"    - {cid}: US={u} ({u_inv:.3f}m THD) -> DS={v} ({v_inv:.3f}m THD), Length={length:.1f}m")
    print("    Note: Preserved as-is for dynamic wave backwater routing.")
    
    # 4. Cross Sections Check
    xsec_ids = set()
    source_xsecs = source_conduits.set_index("conduit_id")
    for line in sections["XSECTIONS"]:
        parts = line.split()
        assert len(parts) >= 7, f"Malformed cross-section record: {line}"
        link_id, shape = parts[0], parts[1].upper()
        assert link_id not in xsec_ids, f"Duplicate cross-section for conduit {link_id}"
        xsec_ids.add(link_id)
        assert shape in {"RECT_OPEN", "RECT_CLOSED", "CIRCULAR", "ARCH"}, f"Unsupported cross-section shape {shape}"
        assert float(parts[2]) > 0 and float(parts[6]) >= 1, f"Invalid cross-section dimensions/barrels for {link_id}"
        source = source_xsecs.loc[link_id]
        assert shape == str(source["shape"]).upper(), f"Cross-section shape changed for {link_id}"
        assert abs(float(parts[2]) - float(source["geom1_height_m"])) <= 0.0011, f"Cross-section height changed for {link_id}"
        assert abs(float(parts[3]) - float(source["geom2_width_m"])) <= 0.0011, f"Cross-section width changed for {link_id}"
        assert int(parts[6]) == int(source["barrels"]), f"Cross-section barrel count changed for {link_id}"
    assert xsec_ids == cond_ids, "Cross-section IDs do not exactly match conduit IDs"
    print(f"[PASS] All {len(cond_ids):,} conduits have one valid cross-section")
    
    # 5. Subcatchment Outlets & Raingage Check
    source_subcatchments = pd.read_csv(PILOT_DIR / "swmm_subcatchments_ward_L.csv", dtype={"subcatchment_id": str, "raingage_id": str, "outlet_node_id": str})
    raingages = {line.split()[0] for line in sections["RAINGAGES"]}
    assert len(raingages) == len(sections["RAINGAGES"]), "Duplicate rain-gage IDs"
    sc_ids = set()
    dup_scs = set()
    
    for l in sections["SUBCATCHMENTS"]:
        parts = l.split()
        sid, rg, outlet = parts[0], parts[1], parts[2]
        if sid in sc_ids: dup_scs.add(sid)
        sc_ids.add(sid)
        
        assert rg in raingages, f"Subcatchment {sid} references undefined raingage {rg}"
        assert outlet in all_nodes, f"Subcatchment {sid} outlet node {outlet} missing from node set!"
        
    assert len(dup_scs) == 0, f"Duplicate subcatchment IDs found: {dup_scs}"
    source_sc = source_subcatchments.set_index("subcatchment_id")
    assert sc_ids == set(source_sc.index), "Generated subcatchment IDs differ from the source CSV"
    for line in sections["SUBCATCHMENTS"]:
        parts = line.split()
        source = source_sc.loc[parts[0]]
        assert parts[1] == source["raingage_id"] and parts[2] == source["outlet_node_id"], f"Subcatchment {parts[0]} reference changed"
    print(f"[PASS] All {len(sc_ids):,} subcatchments reference valid rain gage and outlet nodes")
    raingage_lines = [line.split() for line in sections["RAINGAGES"]]
    assert len(raingage_lines) == len(raingages) and raingage_lines, "Missing or duplicate rain-gage definitions"
    for parts in raingage_lines:
        assert len(parts) == 6 and parts[1].upper() == "VOLUME" and parts[2] == "0:15", f"Unexpected rain-gage definition: {' '.join(parts)}"
        assert parts[4].upper() == "TIMESERIES", f"Rain gage {parts[0]} is not linked to a time series"
    
    # 6. Timeseries Date Parseability Check
    ts_rows = []
    for l in sections["TIMESERIES"]:
        parts = l.split()
        assert len(parts) == 4, f"Malformed rainfall time-series row: {l}"
        ts_rows.append((parts[0], datetime.strptime(f"{parts[1]} {parts[2]}", "%m/%d/%Y %H:%M"), float(parts[3])))

    assert ts_rows, "No parseable timeseries data found!"
    assert {row[0] for row in ts_rows} == {"TS_2005_JULY26"}, "Unexpected rainfall series identifier"
    assert len(ts_rows) == 108, f"Expected 108 reconstructed 15-minute records; found {len(ts_rows)}"
    assert all(ts_rows[index][1] - ts_rows[index - 1][1] == timedelta(minutes=15) for index in range(1, len(ts_rows))), "Rainfall records are not continuous 15-minute intervals"
    rainfall_total = sum(row[2] for row in ts_rows)
    assert abs(rainfall_total - 944.2) <= 0.01, f"Rainfall total is {rainfall_total:.3f} mm, expected 944.2 mm"
    assert ts_rows[0][1] == datetime(2005, 7, 26) and ts_rows[-1][1] == datetime(2005, 7, 27, 2, 45), "Unexpected rainfall time-series boundaries"

    source_rain = [line.split() for line in RAINFALL_FILE.read_text().splitlines() if line.strip() and not line.lstrip().startswith(";")]
    assert len(source_rain) == len(ts_rows), "Generated rainfall record count differs from source file"
    assert all(row[0] == "TS_2005_JULY26" for row in source_rain), "Unexpected series in rainfall source file"
    for generated, source in zip(ts_rows, source_rain):
        source_datetime = datetime.strptime(f"{source[1]} {source[2]}", "%m/%d/%Y %H:%M")
        assert generated[1] == source_datetime and abs(generated[2] - float(source[3])) <= 0.0001, "Generated rainfall differs from source file"
    assert all(parts[5] in {row[0] for row in ts_rows} for parts in raingage_lines), "Rain gage references undefined time series"
    print(f"[PASS] Rainfall matches source ({len(ts_rows)} continuous 15-minute depths; {rainfall_total:.1f} mm total)")

    for section_name in ("SUBAREAS", "INFILTRATION"):
        section_ids = [line.split()[0] for line in sections[section_name]]
        assert len(section_ids) == len(set(section_ids)), f"Duplicate IDs in [{section_name}]"
        assert set(section_ids) == sc_ids, f"[{section_name}] IDs do not exactly match subcatchments"
    coordinate_ids = [line.split()[0] for line in sections["COORDINATES"]]
    assert len(coordinate_ids) == len(set(coordinate_ids)) and set(coordinate_ids) == all_nodes, "Coordinates do not exactly match unique model nodes"
    print("[PASS] Subareas, infiltration, and coordinates cover all expected IDs exactly once")

    outfall_types = {line.split()[2] for line in sections["OUTFALLS"]}
    assert outfall_types == {"FREE"}, f"Unexpected MVP outfall boundary types: {outfall_types}"
    print("[PASS] Provisional FREE outfall boundaries; tide curve metadata is not used")
    
    print("=" * 75)
    print("ALL INPUT FILE VALIDATION CHECKS PASSED SUCCESSFULLY!")
    print("WARNING: This validates input consistency, not calibration or hydraulic performance.")
    print("=" * 75)

if __name__ == "__main__":
    inp_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INP
    validate_inp_file(inp_path)
