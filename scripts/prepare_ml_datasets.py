"""
prepare_ml_datasets.py
======================
Builds the complete Machine Learning & Early Warning Risk Datasets:
1. ml_master_spatial_features.csv (47,758 cells):
   - Elevation, slope, TWI, flow accumulation
   - Land cover fractions (built-up, vegetation, water, mangrove)
   - Drainage density, distance to drain, drain capacity proxy, drainage stress index
   - Building density & critical infrastructure exposure (roads, hospitals, railways)
   - Soil texture & infiltration proxy
   - 5-fold Spatial Block Cross-Validation (split by BMC administrative ward groups)
   - Historical flood labels & flood fractions (from 333 verified BMC flood spots)

2. ml_forecast_warning_scenarios.csv:
   - Multi-scenario matrix across 5 rainfall alert tiers (Normal, Yellow, Orange, Red, Extreme)
   - Combined with coastal tide factors (Low, Normal, High, Very High)
   - Physically derived SCS Curve Number & Runoff depths

3. ml_validation_2005_event.csv:
   - Real past flood event dataset (26 July 2005 944.2mm IMD storm)

4. ml_pilot_ward_L.csv:
   - Dedicated Sample City Area dataset (Ward L - Kurla/Kalina) for the MVP demo.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import geopandas as gpd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
BMC_DIR = RAW_DIR / "bmc"
PROCESSED_DIR = DATA_DIR / "processed"
DERIVED_DIR = DATA_DIR / "derived"
ML_OUT_DIR = DATA_DIR / "ml_ready"
ML_OUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 75)
print("BUILDING MACHINE LEARNING & EARLY WARNING DATASETS")
print("=" * 75)

# ---------------------------------------------------------------------------
# 1. LOAD PROCESSED BASELINE 100M LAYERS
# ---------------------------------------------------------------------------
print("\n[1/5] Loading 100m baseline spatial grid, hydrology, and soil layers...")
df_grid = pd.read_csv(PROCESSED_DIR / "flood_grid_100m.csv")
df_hydro = pd.read_csv(PROCESSED_DIR / "hydrology_100m.csv")
df_soil = pd.read_csv(PROCESSED_DIR / "soil_100m.csv")

# Merge baseline tables on grid_id
df_master = df_grid.merge(df_hydro[["grid_id", "flow_accumulation", "flow_accumulation_area_km2", "flow_accumulation_log"]], on="grid_id", how="left")
df_master = df_master.merge(df_soil[["grid_id", "clay_percent", "sand_percent", "silt_percent", "soil_class", "infiltration_proxy"]], on="grid_id", how="left")

print(f"Merged baseline shape: {df_master.shape}")

# ---------------------------------------------------------------------------
# 2. FEATURE ENGINEERING: TOPOGRAPHIC & HYDROLOGICAL INDICES
# ---------------------------------------------------------------------------
print("\n[2/5] Computing Topographic Wetness Index (TWI) & Drainage Stress...")

# (A) Topographic Wetness Index: ln(a / tan(beta))
# a = specific catchment area (m2 per unit contour width = 100m)
# beta = slope in radians
slope_rad = np.radians(np.clip(df_master["slope_mean"].values, 0.2, 85.0))
specific_catchment_area = (df_master["flow_accumulation"].values * 100.0 * 100.0) / 100.0  # m
twi = np.log(np.maximum(specific_catchment_area / np.tan(slope_rad), 1.0))
df_master["topographic_wetness_index"] = np.round(np.clip(twi, 0.0, 25.0), 3)

# (B) Drain Capacity Proxy & Drainage Stress Index
# If cell has high built-up / low drain density, drainage stress is high
built_up = df_master["built_up_fraction"].fillna(0.0).clip(0, 1)
drain_dens = df_master["drain_density"].fillna(0.0)
dist_drain = df_master["distance_to_drain"].fillna(1000.0)

# Proxy drain capacity: drain density (m/km2) * typical conduit cross section (avg 3.0 m2)
df_master["drain_capacity_proxy_m2"] = np.round(df_master["drain_density"] * 0.003, 3)

# Drainage stress: higher impervious with low drain density
drainage_stress = (built_up * 100.0) / (1.0 + (drain_dens / 1000.0))
df_master["drainage_stress_index"] = np.round(drainage_stress, 2)

# ---------------------------------------------------------------------------
# 3. CRITICAL INFRASTRUCTURE EXPOSURE (BMC LAYERS)
# ---------------------------------------------------------------------------
print("\n[3/5] Attaching critical infrastructure exposure (hospitals, railways, roads)...")

# Load BMC roads, railways, hospitals to tag exposure
roads_file = BMC_DIR / "roads.geojson"
railways_file = BMC_DIR / "railways.geojson"
hospitals_file = BMC_DIR / "hospitals.geojson"
grid_geojson = PROCESSED_DIR / "flood_grid_100m.geojson"

gdf_grid = gpd.read_file(grid_geojson)

if roads_file.exists():
    try:
        gdf_roads = gpd.read_file(roads_file).to_crs("EPSG:32643")
        # Overlay roads with grid to calculate exact road length per cell
        inter_roads = gpd.overlay(gdf_grid[["grid_id", "geometry"]], gdf_roads[["geometry"]], how="intersection", keep_geom_type=False)
        inter_roads = inter_roads[inter_roads.geometry.geom_type.isin(["LineString", "MultiLineString"])]
        inter_roads["road_len_m"] = inter_roads.geometry.length
        road_sums = inter_roads.groupby("grid_id")["road_len_m"].sum()
        df_master["road_length_m"] = df_master["grid_id"].map(road_sums).fillna(0.0).round(1)
    except Exception as e:
        print(f"Road overlay error ({e}), using default 0.0")
        df_master["road_length_m"] = 0.0
else:
    df_master["road_length_m"] = 0.0

if railways_file.exists():
    try:
        gdf_rail = gpd.read_file(railways_file).to_crs("EPSG:32643")
        sj_rail = gpd.sjoin(gdf_grid[["grid_id", "geometry"]], gdf_rail[["geometry"]], how="inner", predicate="intersects")
        rail_cells = set(sj_rail["grid_id"])
        df_master["has_railway"] = df_master["grid_id"].isin(rail_cells).astype(int)
    except Exception as e:
        df_master["has_railway"] = 0
else:
    df_master["has_railway"] = 0

if hospitals_file.exists():
    try:
        gdf_hosp = gpd.read_file(hospitals_file).to_crs("EPSG:32643")
        sj_hosp = gpd.sjoin(gdf_grid[["grid_id", "geometry"]], gdf_hosp[["geometry"]], how="inner", predicate="intersects")
        hosp_cells = set(sj_hosp["grid_id"])
        df_master["has_hospital"] = df_master["grid_id"].isin(hosp_cells).astype(int)
    except Exception as e:
        df_master["has_hospital"] = 0
else:
    df_master["has_hospital"] = 0

# Overall critical exposure flag
df_master["is_critical_asset_cell"] = (
    (df_master["has_hospital"] == 1) | 
    (df_master["has_railway"] == 1) | 
    (df_master["building_count"] > 15) | 
    (df_master["road_length_m"] > 100.0)
).astype(int)

# ---------------------------------------------------------------------------
# 4. SPATIAL BLOCK K-FOLD CROSS-VALIDATION SPLITS (LEAK-FREE)
# ---------------------------------------------------------------------------
print("\n[4/5] Assigning 5-Fold Spatial Cross-Validation Blocks by BMC Ward Groups...")

# 5 Regional Administrative Zones to prevent spatial autocorrelation leakage:
# Zone 0: Island City South (A, B, C, D, E)
# Zone 1: Island City North (F/N, F/S, G/N, G/S)
# Zone 2: Eastern Suburbs South (L, M/E, M/W)
# Zone 3: Eastern Suburbs North (N, S, T)
# Zone 4: Western Suburbs South & North (H/E, H/W, K/E, K/W, P/N, P/S, R/C, R/N, R/S)
spatial_fold_map = {
    "A": 0, "B": 0, "C": 0, "D": 0, "E": 0,
    "F/N": 1, "F/S": 1, "G/N": 1, "G/S": 1,
    "L": 2, "M/E": 2, "M/W": 2,
    "N": 3, "S": 3, "T": 3,
    "H/E": 4, "H/W": 4, "K/E": 4, "K/W": 4, "P/N": 4, "P/S": 4, "R/C": 4, "R/N": 4, "R/S": 4
}

df_master["spatial_cv_fold"] = df_master["ward"].map(spatial_fold_map).fillna(2).astype(int)

# Save Master ML Spatial Features
df_master.to_csv(ML_OUT_DIR / "ml_master_spatial_features.csv", index=False)
print(f"Saved {len(df_master):,} cells -> {ML_OUT_DIR / 'ml_master_spatial_features.csv'}")

# ---------------------------------------------------------------------------
# 5. MULTI-SCENARIO RAINFALL MATRIX & WARNING LEVELS
# ---------------------------------------------------------------------------
print("\n[5/5] Building Multi-Scenario Forecast Matrix with IMD Early Warning Levels...")

# SCS Curve Number estimation:
# Urban impervious: CN ~ 95
# Vegetated pervious loam: CN ~ 70
# Composite CN = built_up * 95 + (1 - built_up) * (70 - infil_proxy * 10)
infil_p = df_master["infiltration_proxy"].fillna(0.4).values
cn = built_up.values * 95.0 + (1.0 - built_up.values) * (72.0 - infil_p * 15.0)
cn = np.clip(cn, 60.0, 98.0)
s_potential_retention = (25400.0 / cn) - 254.0  # in mm

# 5 Operational Forecast Early Warning Scenarios:
scenarios = [
    {
        "scenario_name": "SCEN_0_DRY_BASELINE",
        "warning_tier": "Normal / Green",
        "warning_level_code": 0,
        "rainfall_1h_mm": 0.0,
        "rainfall_3h_mm": 0.0,
        "rainfall_24h_mm": 0.0,
        "tide_factor": 0.50,
        "tide_name": "NORMAL"
    },
    {
        "scenario_name": "SCEN_1_YELLOW_ADVISORY",
        "warning_tier": "Advisory / Yellow",
        "warning_level_code": 1,
        "rainfall_1h_mm": 25.0,
        "rainfall_3h_mm": 65.0,
        "rainfall_24h_mm": 115.0,
        "tide_factor": 0.50,
        "tide_name": "NORMAL"
    },
    {
        "scenario_name": "SCEN_2_ORANGE_WATCH",
        "warning_tier": "Watch / Orange",
        "warning_level_code": 2,
        "rainfall_1h_mm": 50.0,
        "rainfall_3h_mm": 130.0,
        "rainfall_24h_mm": 220.0,
        "tide_factor": 0.75,
        "tide_name": "HIGH"
    },
    {
        "scenario_name": "SCEN_3_RED_WARNING",
        "warning_tier": "Warning / Red",
        "warning_level_code": 3,
        "rainfall_1h_mm": 100.0,
        "rainfall_3h_mm": 240.0,
        "rainfall_24h_mm": 380.0,
        "tide_factor": 1.00,
        "tide_name": "VERY_HIGH"
    },
    {
        "scenario_name": "SCEN_4_2005_EXTREME_DISASTER",
        "warning_tier": "Severe / Disaster",
        "warning_level_code": 4,
        "rainfall_1h_mm": 145.0,
        "rainfall_3h_mm": 431.7,
        "rainfall_24h_mm": 944.2,
        "tide_factor": 1.00,
        "tide_name": "VERY_HIGH"
    }
]

# Generate Event-Specific Validation File: Real Past Flood (26 July 2005)
df_2005_event = df_master.copy()
df_2005_event["event_id"] = "E001_2005_JULY26"
df_2005_event["rainfall_1h_mm"] = 145.0
df_2005_event["rainfall_3h_mm"] = 431.7
df_2005_event["rainfall_6h_mm"] = 649.3
df_2005_event["rainfall_12h_mm"] = 768.9
df_2005_event["rainfall_24h_mm"] = 944.2
df_2005_event["tide_factor"] = 1.0
df_2005_event["tide_name"] = "VERY_HIGH"

# Physical Runoff depth for 2005 event: Q = (P - 0.2S)^2 / (P + 0.8S)
p_2005 = 944.2
runoff_2005 = np.where(p_2005 > 0.2 * s_potential_retention,
                       ((p_2005 - 0.2 * s_potential_retention) ** 2) / (p_2005 + 0.8 * s_potential_retention),
                       0.0)
df_2005_event["scs_runoff_depth_24h_mm"] = np.round(runoff_2005, 1)

df_2005_event.to_csv(ML_OUT_DIR / "ml_validation_2005_event.csv", index=False)
print(f"Saved real past flood validation dataset -> {ML_OUT_DIR / 'ml_validation_2005_event.csv'}")

# Generate Multi-Scenario Matrix for training & inference
scenario_rows = []
for sc in scenarios:
    p_3h = sc["rainfall_3h_mm"]
    # 3-hour runoff estimate
    runoff_3h = np.where(p_3h > 0.2 * s_potential_retention,
                         ((p_3h - 0.2 * s_potential_retention) ** 2) / (p_3h + 0.8 * s_potential_retention),
                         0.0)
    
    sc_df = pd.DataFrame({
        "grid_id": df_master["grid_id"],
        "ward": df_master["ward"],
        "scenario_name": sc["scenario_name"],
        "warning_tier": sc["warning_tier"],
        "warning_level_code": sc["warning_level_code"],
        "rainfall_1h_mm": sc["rainfall_1h_mm"],
        "rainfall_3h_mm": sc["rainfall_3h_mm"],
        "rainfall_24h_mm": sc["rainfall_24h_mm"],
        "tide_factor": sc["tide_factor"],
        "elevation_mean": df_master["elevation_mean"],
        "slope_mean": df_master["slope_mean"],
        "topographic_wetness_index": df_master["topographic_wetness_index"],
        "built_up_fraction": df_master["built_up_fraction"],
        "drain_density": df_master["drain_density"],
        "distance_to_drain": df_master["distance_to_drain"],
        "drainage_stress_index": df_master["drainage_stress_index"],
        "distance_to_water": df_master["distance_to_water"],
        "building_count": df_master["building_count"],
        "is_critical_asset_cell": df_master["is_critical_asset_cell"],
        "scs_curve_number": np.round(cn, 1),
        "scs_runoff_3h_mm": np.round(runoff_3h, 1),
        "historical_flood_label": df_master["flood_label"],
        "spatial_cv_fold": df_master["spatial_cv_fold"]
    })
    scenario_rows.append(sc_df)

df_all_scenarios = pd.concat(scenario_rows, ignore_index=True)
df_all_scenarios.to_csv(ML_OUT_DIR / "ml_forecast_warning_scenarios.csv", index=False)
print(f"Saved multi-scenario forecast matrix ({len(df_all_scenarios):,} rows) -> {ML_OUT_DIR / 'ml_forecast_warning_scenarios.csv'}")

# Extract Pilot Sample City Area (Ward L) ML Dataset
df_pilot_ml = df_master[df_master["ward"] == "L"].copy()
df_pilot_ml.to_csv(ML_OUT_DIR / "ml_pilot_ward_L.csv", index=False)
print(f"Saved Ward L pilot ML dataset ({len(df_pilot_ml):,} cells) -> {ML_OUT_DIR / 'ml_pilot_ward_L.csv'}")

# Generate Metadata Manifest
meta = {
    "dataset_package": "Mumbai Urban Stormwater Flood Prediction System",
    "spatial_resolution": "100m x 100m grid cells",
    "total_cells": len(df_master),
    "crs": "EPSG:32643 (UTM Zone 43N)",
    "flood_spots_positive_cells": int(df_master["flood_label"].sum()),
    "flood_spots_positive_rate": round(float(df_master["flood_label"].mean()), 4),
    "sample_area_pilot": {
        "ward": "L",
        "description": "Kurla / Kalina / Mithi River Basin (most flood-prone urban basin in Mumbai)",
        "cells": len(df_pilot_ml),
        "flood_positive_cells": int(df_pilot_ml["flood_label"].sum()),
        "flood_positive_pct": f"{df_pilot_ml['flood_label'].mean() * 100:.2f}%"
    },
    "warning_levels": [
        {"code": 0, "name": "Normal / Green", "threshold": "Rain < 15 mm/h", "action": "Normal drainage monitoring"},
        {"code": 1, "name": "Advisory / Yellow", "threshold": "Rain 15-35 mm/h", "action": "Alert ward control rooms; clear surface grates"},
        {"code": 2, "name": "Watch / Orange", "threshold": "Rain 35-65 mm/h", "action": "Stage portable dewatering pumps; caution low-lying roads"},
        {"code": 3, "name": "Warning / Red", "threshold": "Rain > 65 mm/h", "action": "Deploy NDRF/BMC emergency teams; divert road & rail traffic"},
        {"code": 4, "name": "Severe / Emergency", "threshold": "Extreme storm / Cloudburst", "action": "Mass evacuation of vulnerable basements and riverbanks"}
    ],
    "spatial_cv_folds": {
        "fold_0": "Island City South (Wards A, B, C, D, E)",
        "fold_1": "Island City North (Wards F/N, F/S, G/N, G/S)",
        "fold_2": "Eastern Suburbs South (Wards L, M/E, M/W)",
        "fold_3": "Eastern Suburbs North (Wards N, S, T)",
        "fold_4": "Western Suburbs (Wards H, K, P, R)"
    }
}

with open(ML_OUT_DIR / "dataset_metadata.json", "w") as f:
    json.dump(meta, f, indent=2)

print("\n" + "=" * 75)
print("MACHINE LEARNING & EARLY WARNING DATASET PREPARATION COMPLETE!")
print("=" * 75)
