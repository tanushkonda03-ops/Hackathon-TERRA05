"""
prepare_swmm_datasets.py
========================
Fulfills the dataset requirements for the EPA-SWMM stormwater hydraulic model:
1. Nodes (Junctions & Outfalls) with UTM43 coordinates, WGS84 coordinates, inverts,
   DEM rim elevations, maximum depth, ponded area.
2. Conduits with SWMM-standard cross-section shapes (RECT_CLOSED, RECT_OPEN, CIRCULAR, ARCH),
   metric dimensions, Manning's roughness, slopes, and theoretical full capacity.
3. Subcatchments generated from 100m grid cells mapped to nearest drainage junctions,
   with % impervious, slope, width, depression storage, and Horton infiltration parameters.
4. Rainfall Hyetographs (15-minute resolution for 26 July 2005 944.2mm event and design storms).
5. Isolated Pilot Sample City Area (Ward L - Kurla/Kalina) network for immediate testing.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import geopandas as gpd
from scipy.spatial import cKDTree
import rasterio

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DERIVED_DIR = DATA_DIR / "derived"

SWMM_OUT_DIR = DATA_DIR / "swmm_ready"
PILOT_OUT_DIR = SWMM_OUT_DIR / "pilot_ward_L"
SWMM_OUT_DIR.mkdir(parents=True, exist_ok=True)
PILOT_OUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 75)
print("PREPARING EPA-SWMM STORMWATER MODELING DATASETS")
print("=" * 75)

# ---------------------------------------------------------------------------
# 1. LOAD BMC DRAINAGE NETWORK
# ---------------------------------------------------------------------------
print("\n[1/6] Loading BMC drainage network (EPSG:32643)...")
drain_file = DERIVED_DIR / "bmc_storm_drains_engineering_utm43.geojson"
gdf_drains = gpd.read_file(drain_file)
print(f"Loaded {len(gdf_drains):,} conduit features.")

# Also load WGS84 version to have Lat/Lon coordinates
gdf_drains_wgs = gdf_drains.to_crs("EPSG:4326")

# ---------------------------------------------------------------------------
# 2. EXTRACT & STANDARDIZE NODES (JUNCTIONS & OUTFALLS)
# ---------------------------------------------------------------------------
print("\n[2/6] Extracting network nodes, sampling DEM rim elevations, identifying outfalls...")

# Gather node coordinates and inverts
node_info = {}

for idx in range(len(gdf_drains)):
    row = gdf_drains.iloc[idx]
    row_wgs = gdf_drains_wgs.iloc[idx]
    
    u_id = str(row["US_NODE_ID"]).strip()
    d_id = str(row["DS_NODE_ID"]).strip()
    
    u_coords_utm = row.geometry.coords[0]
    d_coords_utm = row.geometry.coords[-1]
    
    u_coords_wgs = row_wgs.geometry.coords[0]
    d_coords_wgs = row_wgs.geometry.coords[-1]
    
    u_inv = float(row["US_INVERT"])
    d_inv = float(row["DS_INVERT"])
    
    # Store US node
    if u_id not in node_info:
        node_info[u_id] = {
            "x_utm": u_coords_utm[0],
            "y_utm": u_coords_utm[1],
            "lon": u_coords_wgs[0],
            "lat": u_coords_wgs[1],
            "inverts": [],
            "as_us_count": 0,
            "as_ds_count": 0,
            "max_conduit_height_m": 0.0
        }
    node_info[u_id]["inverts"].append(u_inv)
    node_info[u_id]["as_us_count"] += 1
    node_info[u_id]["max_conduit_height_m"] = max(node_info[u_id]["max_conduit_height_m"], float(row["CONDUIT_HE"]) / 1000.0)
    
    # Store DS node
    if d_id not in node_info:
        node_info[d_id] = {
            "x_utm": d_coords_utm[0],
            "y_utm": d_coords_utm[1],
            "lon": d_coords_wgs[0],
            "lat": d_coords_wgs[1],
            "inverts": [],
            "as_us_count": 0,
            "as_ds_count": 0,
            "max_conduit_height_m": 0.0
        }
    node_info[d_id]["inverts"].append(d_inv)
    node_info[d_id]["as_ds_count"] += 1
    node_info[d_id]["max_conduit_height_m"] = max(node_info[d_id]["max_conduit_height_m"], float(row["CONDUIT_HE"]) / 1000.0)

node_ids = list(node_info.keys())
print(f"Total unique nodes identified: {len(node_ids):,}")

# Sample DEM elevations for all nodes
dem_file = RAW_DIR / "external" / "dem_mumbai_utm43.tif"
node_pts_utm = [(node_info[nid]["x_utm"], node_info[nid]["y_utm"]) for nid in node_ids]

with rasterio.open(dem_file) as src:
    dem_samples = [v[0] for v in src.sample(node_pts_utm)]

# Prepare Node Records
# Note on Datum: BMC inverts are in Town Hall Datum (THD) where THD ~ 27.43m ≈ 0.0m GTS/MSL.
# If Invert THD is ~25-30m and DEM MSL is ~2-15m, Ground_THD = DEM_MSL + 27.432m
# This ensures Ground_THD is always above Invert_THD, preserving physical manhole depths (1.5 - 4.0 m).
DATUM_OFFSET = 27.432  # meters (THD to MSL offset)

junction_records = []
outfall_records = []

for idx, nid in enumerate(node_ids):
    info = node_info[nid]
    inv = float(min(info["inverts"]))
    dem_val = dem_samples[idx]
    
    # Ground elevation in MSL
    if np.isfinite(dem_val) and dem_val > -100:
        ground_msl = float(dem_val)
    else:
        # Fallback for coastline border
        ground_msl = max(0.5, inv - DATUM_OFFSET + 1.5)
        
    ground_thd = ground_msl + DATUM_OFFSET
    
    # Physical depth constraint
    conduit_h = info["max_conduit_height_m"]
    min_depth = max(conduit_h + 0.3, 1.2)  # at least conduit height + 0.3m cover or 1.2m
    
    if ground_thd - inv < min_depth:
        ground_thd = inv + min_depth
        ground_msl = ground_thd - DATUM_OFFSET
        
    max_depth = ground_thd - inv
    
    # Outfall test: node is downstream of conduits but never upstream of any conduit
    is_outfall = (info["as_ds_count"] > 0) and (info["as_us_count"] == 0)
    
    if is_outfall:
        outfall_records.append({
            "outfall_id": nid,
            "x_utm43": round(info["x_utm"], 2),
            "y_utm43": round(info["y_utm"], 2),
            "lon": round(info["lon"], 6),
            "lat": round(info["lat"], 6),
            "invert_elev_thd_m": round(inv, 3),
            "invert_elev_msl_m": round(inv - DATUM_OFFSET, 3),
            "ground_elev_thd_m": round(ground_thd, 3),
            "ground_elev_msl_m": round(ground_msl, 3),
            "outfall_type": "FREE",  # FREE, NORMAL, or TIDAL
            "tide_curve_name": "TIDE_ARABIAN_SEA",
            "gated": "NO"
        })
    else:
        junction_records.append({
            "junction_id": nid,
            "x_utm43": round(info["x_utm"], 2),
            "y_utm43": round(info["y_utm"], 2),
            "lon": round(info["lon"], 6),
            "lat": round(info["lat"], 6),
            "invert_elev_thd_m": round(inv, 3),
            "invert_elev_msl_m": round(inv - DATUM_OFFSET, 3),
            "ground_elev_thd_m": round(ground_thd, 3),
            "ground_elev_msl_m": round(ground_msl, 3),
            "max_depth_m": round(max_depth, 3),
            "init_depth_m": 0.0,
            "surcharge_depth_m": 0.0,
            "ponded_area_m2": 100.0  # allows SWMM to simulate surface ponding on street
        })

df_junctions = pd.DataFrame(junction_records)
df_outfalls = pd.DataFrame(outfall_records)

df_junctions.to_csv(SWMM_OUT_DIR / "swmm_junctions_citywide.csv", index=False)
df_outfalls.to_csv(SWMM_OUT_DIR / "swmm_outfalls_citywide.csv", index=False)
print(f"Saved {len(df_junctions):,} junctions -> {SWMM_OUT_DIR / 'swmm_junctions_citywide.csv'}")
print(f"Saved {len(df_outfalls):,} outfalls -> {SWMM_OUT_DIR / 'swmm_outfalls_citywide.csv'}")

# ---------------------------------------------------------------------------
# 3. CONDUITS WITH SWMM HYDRAULIC PARAMETERS
# ---------------------------------------------------------------------------
print("\n[3/6] Standardizing SWMM conduits, cross-sections, roughness and slopes...")

# Mapping shapes to SWMM keywords
# RECT -> RECT_CLOSED (Box culvert/drain)
# OREC -> RECT_OPEN (Open nullah/channel)
# CIRC -> CIRCULAR (Circular pipe)
# ARCH -> ARCH (Arch culvert)
shape_map = {
    "RECT": "RECT_CLOSED",
    "rect": "RECT_CLOSED",
    "OREC": "RECT_OPEN",
    "CIRC": "CIRCULAR",
    "circ": "CIRCULAR",
    "ARCH": "ARCH"
}

conduit_records = []

for idx, row in gdf_drains.iterrows():
    cid = f"C_{row['OBJECTID']}"
    u_id = str(row["US_NODE_ID"]).strip()
    d_id = str(row["DS_NODE_ID"]).strip()
    
    length_m = max(float(row["CONDUIT_LE"]), 1.0)
    raw_shape = str(row["SHAPE_1"]).strip()
    swmm_shape = shape_map.get(raw_shape, "RECT_CLOSED")
    
    width_m = max(float(row["CONDUIT_WI"]) / 1000.0, 0.23)
    height_m = max(float(row["CONDUIT_HE"]) / 1000.0, 0.23)
    
    u_inv = float(row["US_INVERT"])
    d_inv = float(row["DS_INVERT"])
    
    # Manning's roughness n
    if swmm_shape == "RECT_OPEN":
        manning_n = 0.025  # Open concrete/masonry nullah with sediment
    elif swmm_shape == "CIRCULAR":
        manning_n = 0.013  # Smooth RCC concrete or HDPE pipe
    else:
        manning_n = 0.016  # Closed concrete box drain
        
    slope = max((u_inv - d_inv) / length_m, 0.0001)
    
    # Full-flow hydraulic capacity estimate Q = (1/n) * A * R^(2/3) * S^(1/2)
    if swmm_shape == "CIRCULAR":
        diam = height_m
        area = np.pi * (diam / 2.0) ** 2
        p_wet = np.pi * diam
    elif swmm_shape == "RECT_OPEN":
        area = width_m * height_m
        p_wet = width_m + 2.0 * height_m
    else:  # RECT_CLOSED & ARCH
        area = width_m * height_m
        p_wet = 2.0 * (width_m + height_m)
        
    r_hyd = area / max(p_wet, 0.01)
    q_capacity_m3s = (1.0 / manning_n) * area * (r_hyd ** (2.0 / 3.0)) * np.sqrt(slope)
    
    conduit_records.append({
        "conduit_id": cid,
        "us_node_id": u_id,
        "ds_node_id": d_id,
        "length_m": round(length_m, 2),
        "manning_n": manning_n,
        "shape": swmm_shape,
        "geom1_height_m": round(height_m, 3),
        "geom2_width_m": round(width_m, 3),
        "geom3_m": 0.0,
        "geom4_m": 0.0,
        "barrels": 1,
        "us_invert_thd_m": round(u_inv, 3),
        "ds_invert_thd_m": round(d_inv, 3),
        "slope_m_per_m": round(slope, 6),
        "full_capacity_m3s": round(q_capacity_m3s, 3),
        "status": row.get("USER_TEXT2", "Existing")
    })

df_conduits = pd.DataFrame(conduit_records)
df_conduits.to_csv(SWMM_OUT_DIR / "swmm_conduits_citywide.csv", index=False)
print(f"Saved {len(df_conduits):,} conduits -> {SWMM_OUT_DIR / 'swmm_conduits_citywide.csv'}")

# ---------------------------------------------------------------------------
# 4. SUBCATCHMENTS (MAPPING 47,758 GRID CELLS TO SWMM JUNCTIONS)
# ---------------------------------------------------------------------------
print("\n[4/6] Delineating subcatchments and assigning to SWMM drainage junctions via KDTree...")

df_grid = pd.read_csv(PROCESSED_DIR / "flood_grid_100m.csv")
df_soil = pd.read_csv(PROCESSED_DIR / "soil_100m.csv")
gdf_grid = gpd.read_file(PROCESSED_DIR / "flood_grid_100m.geojson")

grid_centroids_utm = np.array([(g.centroid.x, g.centroid.y) for g in gdf_grid.geometry])

# Build KDTree of junction nodes
junc_pts = np.array([[row["x_utm43"], row["y_utm43"]] for idx, row in df_junctions.iterrows()])
junc_ids = df_junctions["junction_id"].tolist()

tree = cKDTree(junc_pts)
distances_to_node, node_indices = tree.query(grid_centroids_utm)

assigned_nodes = [junc_ids[idx] for idx in node_indices]

subcatchment_records = []
for idx, row in df_grid.iterrows():
    gid = int(row["grid_id"])
    built_up = float(row.get("built_up_fraction", 0.0))
    slope_deg = float(row.get("slope_mean", 1.0))
    pct_slope = float(np.tan(np.radians(slope_deg)) * 100.0)
    
    # % Impervious
    pct_imperv = min(max(built_up * 100.0, 5.0), 95.0)
    
    # Infiltration params (Horton method)
    # Loam / Urban Mumbai soil baseline:
    infil_proxy = float(df_soil.iloc[idx].get("infiltration_proxy", 0.4))
    max_rate_mmhr = round(30.0 + infil_proxy * 50.0, 1)  # 50 - 70 mm/hr
    min_rate_mmhr = round(3.0 + infil_proxy * 8.0, 1)    # 5 - 10 mm/hr
    
    subcatchment_records.append({
        "subcatchment_id": f"SC_{gid}",
        "raingage_id": "RG_SANTACRUZ",
        "outlet_node_id": assigned_nodes[idx],
        "area_ha": 1.0,  # 100m x 100m = 1.0 hectare
        "pct_imperv": round(pct_imperv, 1),
        "width_m": 100.0,
        "pct_slope": round(pct_slope, 2),
        "n_imperv": 0.015,
        "n_perv": 0.20,
        "s_imperv_mm": 2.0,
        "s_perv_mm": 5.0,
        "pct_zero_imperv": 25.0,
        "subarea_routing": "OUTLET",
        "horton_max_rate_mmhr": max_rate_mmhr,
        "horton_min_rate_mmhr": min_rate_mmhr,
        "horton_decay_rate_hr": 3.0,
        "horton_dry_time_days": 7.0,
        "distance_to_outlet_m": round(float(distances_to_node[idx]), 1),
        "ward": row.get("ward", "Unknown")
    })

df_subcatchments = pd.DataFrame(subcatchment_records)
df_subcatchments.to_csv(SWMM_OUT_DIR / "swmm_subcatchments_citywide.csv", index=False)
print(f"Saved {len(df_subcatchments):,} subcatchments -> {SWMM_OUT_DIR / 'swmm_subcatchments_citywide.csv'}")

# ---------------------------------------------------------------------------
# 5. HIGH-RESOLUTION RAINFALL HYETOGRAPHS FOR SWMM
# ---------------------------------------------------------------------------
print("\n[5/6] Generating 15-minute rainfall hyetographs for 2005 event and design storm scenarios...")

# (A) 26 July 2005 944.2 mm Event (Reconstructed 15-minute hyetograph from IMD 3h increments)
# Verified IMD 3-hour increments:
# 03:00 - 0.9 mm
# 06:00 - 0.0 mm
# 09:00 - 17.5 mm
# 12:00 - 431.7 mm (2:30 PM - 5:30 PM IST, the deluge peak!)
# 15:00 - 217.6 mm
# 18:00 - 101.2 mm
# 21:00 - 116.1 mm
# 00:00 - 11.0 mm
# 03:00 - 48.2 mm
# Total: 944.2 mm

intervals_3h = [
    ("2005-07-26 00:00", "2005-07-26 03:00", 0.9),
    ("2005-07-26 03:00", "2005-07-26 06:00", 0.0),
    ("2005-07-26 06:00", "2005-07-26 09:00", 17.5),
    ("2005-07-26 09:00", "2005-07-26 12:00", 431.7),
    ("2005-07-26 12:00", "2005-07-26 15:00", 217.6),
    ("2005-07-26 15:00", "2005-07-26 18:00", 101.2),
    ("2005-07-26 18:00", "2005-07-26 21:00", 116.1),
    ("2005-07-26 21:00", "2005-07-27 00:00", 11.0),
    ("2005-07-27 00:00", "2005-07-27 03:00", 48.2)
]

# Triangular 12-step weight profile within each 3h block (12 * 15min = 3 hours)
w = np.array([0.02, 0.04, 0.06, 0.09, 0.13, 0.16, 0.16, 0.13, 0.09, 0.06, 0.04, 0.02])
w = w / w.sum()

ts_lines = [";SWMM 15-Minute Rainfall Timeseries: Mumbai 26 July 2005 (944.2 mm Total)",
            ";Date       Time     Rainfall_mm"]

hyetograph_records = []
current_time = pd.Timestamp("2005-07-26 00:00")

for start_str, end_str, block_mm in intervals_3h:
    sub_15min_mm = block_mm * w
    for step_mm in sub_15min_mm:
        date_str = current_time.strftime("%m/%d/%Y")
        time_str = current_time.strftime("%H:%M")
        val = round(float(step_mm), 3)
        ts_lines.append(f"TS_2005_JULY26 {date_str} {time_str} {val}")
        hyetograph_records.append({
            "timeseries_id": "TS_2005_JULY26",
            "datetime": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "rainfall_15min_mm": val,
            "intensity_mm_per_hr": round(val * 4.0, 2)
        })
        current_time += pd.Timedelta(minutes=15)

with open(SWMM_OUT_DIR / "timeseries_2005_july26.dat", "w") as f:
    f.write("\n".join(ts_lines) + "\n")


# (B) Design Storms: intensity warnings AND total-depth scenarios.
# Synthetic scenarios only; these are not observed rainfall events.
# Each value written below is rainfall DEPTH in a 15-minute interval (mm).
# Peak intensity (mm/hour) = maximum interval depth * 4.

design_storms = {
    "DESIGN_YELLOW_25MM": 25.0,
    "DESIGN_ORANGE_50MM": 50.0,
    "DESIGN_RED_100MM": 100.0,
    "DESIGN_CLOUDBURST_150MM": 150.0,
}

unit_dist = np.array(
    [0.03, 0.05, 0.08, 0.12, 0.18, 0.24,
     0.14, 0.07, 0.04, 0.02, 0.02, 0.01],
    dtype=float,
)
unit_dist = unit_dist / unit_dist.sum()
max_weight = float(unit_dist.max())

intensity_lines = [
    "; SYNTHETIC DESIGN SCENARIOS - NOT OBSERVED RAINFALL",
    "; IDs retain legacy names; numbers represent PEAK INTENSITY in mm/hour",
    "; Format: Series_Name Date Time Interval_Depth_mm",
]

depth_lines = [
    "; SYNTHETIC 3-HOUR TOTAL-DEPTH SCENARIOS - NOT OBSERVED RAINFALL",
    "; IDs specify target total depth in mm over 3 hours",
    "; Format: Series_Name Date Time Interval_Depth_mm",
]

scenario_start = pd.Timestamp("2026-07-01 00:00")

def write_scenario(series_id, total_depth_mm, output_lines):
    scenario_time = scenario_start
    interval_depths = total_depth_mm * unit_dist

    for interval_depth in interval_depths:
        value_mm = round(float(interval_depth), 6)
        date_str = scenario_time.strftime("%m/%d/%Y")
        time_str = scenario_time.strftime("%H:%M")
        output_lines.append(
            f"{series_id} {date_str} {time_str} {value_mm}"
        )

        hyetograph_records.append({
            "timeseries_id": series_id,
            "datetime": scenario_time.strftime("%Y-%m-%d %H:%M:%S"),
            "rainfall_15min_mm": value_mm,
            "intensity_mm_per_hr": round(value_mm * 4.0, 6),
        })
        scenario_time += pd.Timedelta(minutes=15)

# A. Peak-intensity scenarios: exact target peak in mm/hour.
for series_id, target_peak_mmhr in design_storms.items():
    total_depth_mm = target_peak_mmhr / (4.0 * max_weight)
    write_scenario(series_id, total_depth_mm, intensity_lines)

# B. Total-depth scenarios: exact target total over 3 hours.
for target_depth_mm in (25.0, 50.0, 100.0, 150.0):
    series_id = f"DEPTH_{int(target_depth_mm)}MM_3H"
    write_scenario(series_id, target_depth_mm, depth_lines)

with open(SWMM_OUT_DIR / "timeseries_design_storms.dat", "w",
          encoding="utf-8") as f:
    f.write("\n".join(intensity_lines) + "\n")

with open(SWMM_OUT_DIR / "timeseries_depth_scenarios.dat", "w",
          encoding="utf-8") as f:
    f.write("\n".join(depth_lines) + "\n")

pd.DataFrame(hyetograph_records).to_csv(
    SWMM_OUT_DIR / "swmm_rainfall_catalog.csv", index=False
)

print("Saved intensity scenarios:", SWMM_OUT_DIR / "timeseries_design_storms.dat")
print("Saved total-depth scenarios:", SWMM_OUT_DIR / "timeseries_depth_scenarios.dat")
print("Updated rainfall catalogue:", SWMM_OUT_DIR / "swmm_rainfall_catalog.csv")

# 6. EXTRACT PILOT SAMPLE CITY AREA (WARD L - KURLA / KALINA / MITHI CORRIDOR)
# ---------------------------------------------------------------------------
print("\n[6/6] Extracting Pilot Sample City Area (Ward L - Kurla/Kalina/Mithi corridor)...")

# Ward L subcatchments
df_sc_pilot = df_subcatchments[df_subcatchments["ward"] == "L"].copy()
pilot_node_ids = set(df_sc_pilot["outlet_node_id"])

# Conduits connected to pilot nodes or inside Ward L
df_conduits_pilot = df_conduits[df_conduits["us_node_id"].isin(pilot_node_ids) | df_conduits["ds_node_id"].isin(pilot_node_ids)].copy()

all_pilot_node_ids = set(df_conduits_pilot["us_node_id"]).union(set(df_conduits_pilot["ds_node_id"])).union(pilot_node_ids)

df_junctions_pilot = df_junctions[df_junctions["junction_id"].isin(all_pilot_node_ids)].copy()
df_outfalls_pilot = df_outfalls[df_outfalls["outfall_id"].isin(all_pilot_node_ids)].copy()

df_sc_pilot.to_csv(PILOT_OUT_DIR / "swmm_subcatchments_ward_L.csv", index=False)
df_conduits_pilot.to_csv(PILOT_OUT_DIR / "swmm_conduits_ward_L.csv", index=False)
df_junctions_pilot.to_csv(PILOT_OUT_DIR / "swmm_junctions_ward_L.csv", index=False)
df_outfalls_pilot.to_csv(PILOT_OUT_DIR / "swmm_outfalls_ward_L.csv", index=False)

print(f"Ward L Pilot Dataset extracted:")
print(f"  - Subcatchments: {len(df_sc_pilot):,} (100m cells)")
print(f"  - Conduits:      {len(df_conduits_pilot):,}")
print(f"  - Junctions:     {len(df_junctions_pilot):,}")
print(f"  - Outfalls:      {len(df_outfalls_pilot):,}")
print(f"  -> Saved in {PILOT_OUT_DIR}")

print("\n" + "=" * 75)
print("EPA-SWMM DATASET PREPARATION COMPLETE!")
print("=" * 75)
