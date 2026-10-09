"""
test_swmm_pilot_boundary.py
============================
Automated validation test suite for the EPA-SWMM Ward L Pilot Dataset.
Verifies referential integrity, subcatchment outlet reachability, duplicate IDs,
and hydraulic attributes.
"""

from pathlib import Path
import pandas as pd
from collections import deque

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PILOT_DIR = PROJECT_ROOT / "data" / "swmm_ready" / "pilot_ward_L"

def test_ward_L_pilot_integrity():
    print("===========================================================================")
    print("RUNNING AUTOMATED WARD L PILOT BOUNDARY & INTEGRITY VALIDATION")
    print("===========================================================================")
    
    # Load pilot tables
    df_junc = pd.read_csv(PILOT_DIR / "swmm_junctions_ward_L.csv")
    df_out = pd.read_csv(PILOT_DIR / "swmm_outfalls_ward_L.csv")
    df_cond = pd.read_csv(PILOT_DIR / "swmm_conduits_ward_L.csv")
    df_sc = pd.read_csv(PILOT_DIR / "swmm_subcatchments_ward_L.csv")
    
    junc_ids = set(df_junc["junction_id"].astype(str))
    out_ids = set(df_out["outfall_id"].astype(str))
    all_nodes = junc_ids.union(out_ids)
    
    # Check 1: Preserve 1,516 Ward L Subcatchments
    assert len(df_sc) == 1516, f"Expected 1,516 subcatchments, found {len(df_sc)}"
    print(f"[PASS] Subcatchment count: {len(df_sc)} (1,516 preserved)")
    
    # Check 2: Subcatchment Outlet Referential Integrity
    sc_outlets = set(df_sc["outlet_node_id"].astype(str))
    missing_sc_outlets = sc_outlets - all_nodes
    assert len(missing_sc_outlets) == 0, f"Subcatchment outlets missing from node set: {missing_sc_outlets}"
    print(f"[PASS] Subcatchment outlet referential integrity (0 missing outlets across {len(sc_outlets)} unique outlet nodes)")
    
    # Check 3: Conduit Endpoint Referential Integrity
    cond_us = set(df_cond["us_node_id"].astype(str))
    cond_ds = set(df_cond["ds_node_id"].astype(str))
    missing_endpoints = (cond_us.union(cond_ds)) - all_nodes
    assert len(missing_endpoints) == 0, f"Conduit endpoints missing from node set: {missing_endpoints}"
    print(f"[PASS] Conduit endpoint referential integrity (0 missing endpoints across {len(df_cond)} conduits)")
    
    # Check 4: Duplicate Identifiers
    dup_junc = len(df_junc) - len(junc_ids)
    dup_out = len(df_out) - len(out_ids)
    dup_cond = len(df_cond) - df_cond["conduit_id"].nunique()
    dup_sc = len(df_sc) - df_sc["subcatchment_id"].nunique()
    assert dup_junc == 0 and dup_out == 0 and dup_cond == 0 and dup_sc == 0, "Duplicate IDs detected!"
    print(f"[PASS] Identifier uniqueness (0 duplicate Junctions, Outfalls, Conduits, or Subcatchments)")
    
    # Check 5: 100% Directed Reachability from Subcatchment Outlets to Outfalls
    adj = {}
    for _, r in df_cond.iterrows():
        u = str(r["us_node_id"])
        v = str(r["ds_node_id"])
        if u not in adj: adj[u] = []
        adj[u].append(v)
        
    unreachable_outlets = []
    for outlet in sc_outlets:
        visited = {outlet}
        q = deque([outlet])
        has_path = False
        while q:
            curr = q.popleft()
            if curr in out_ids:
                has_path = True
                break
            for nxt in adj.get(curr, []):
                if nxt not in visited:
                    visited.add(nxt)
                    q.append(nxt)
        if not has_path:
            unreachable_outlets.append(outlet)
            
    assert len(unreachable_outlets) == 0, f"Unreachable subcatchment outlets: {unreachable_outlets}"
    print(f"[PASS] 100% Directed Reachability (All {len(sc_outlets)} unique outlets reach a legitimate outfall)")
    
    # Report Network Metrics & Adverse Slopes
    adv_slopes = df_cond[df_cond["us_invert_thd_m"] < df_cond["ds_invert_thd_m"]]
    print(f"\n--- Pilot Dataset Final Verification Summary ---")
    print(f"  Subcatchments:           {len(df_sc):,}")
    print(f"  Unique Outlet Nodes:     {len(sc_outlets):,}")
    print(f"  Junctions:               {len(df_junc):,}")
    print(f"  Outfalls:                {len(df_out):,}")
    print(f"  Conduits:                {len(df_cond):,}")
    print(f"  Inherited Adverse Slopes:{len(adv_slopes)}")
    print("===========================================================================")
    print("ALL PILOT BOUNDARY VALIDATION TESTS PASSED SUCCESSFULLY!")
    print("===========================================================================")

if __name__ == "__main__":
    test_ward_L_pilot_integrity()
