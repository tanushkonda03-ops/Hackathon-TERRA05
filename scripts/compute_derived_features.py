"""
Compute derived geospatial features after the raw datasets are downloaded.

Inputs:
- data/raw/bmc/*.geojson
- existing flooding_spots.geojson
- existing storm_water_drains.geojson

External rasters:
- data/raw/external/dem_mumbai.tif
- data/raw/external/worldcover_mumbai.tif

Outputs:
- data/processed/model_grid_100m.gpkg
- data/processed/model_features.csv
"""

from pathlib import Path
import geopandas as gpd
import pandas as pd
import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.features import geometry_mask
from shapely.geometry import box
from scipy.ndimage import sobel
import json, math

ROOT = Path("data")
BMC = ROOT / "raw" / "bmc"
EXT = ROOT / "raw" / "external"
PROCESSED = ROOT / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

TARGET_CRS = "EPSG:32643"
RES = 100

def read(name):
    return gpd.read_file(BMC / name)

# Boundary
wards = read("disaster_wards.geojson")
wards = wards.to_crs(TARGET_CRS)
boundary = wards.geometry.union_all()
boundary_gdf = gpd.GeoDataFrame({"id":[1]}, geometry=[boundary], crs=TARGET_CRS)

# Existing user files
floods = gpd.read_file(ROOT / "raw" / "flooding_spots.geojson").to_crs(TARGET_CRS)
drains = gpd.read_file(ROOT / "raw" / "storm_water_drains.geojson").to_crs(TARGET_CRS)

# Clean flood labels
floods = floods[~floods["NAME"].fillna("").astype(str).str.contains("delete", case=False)]
if "FEATUREID" in floods.columns:
    floods = floods.drop_duplicates("FEATUREID")
floods["geometry"] = floods.geometry.make_valid()
floods = floods[floods.geometry.notna() & ~floods.geometry.is_empty]

# Clip drains/floods to Mumbai boundary
drains = gpd.clip(drains, boundary_gdf)
floods = gpd.clip(floods, boundary_gdf)

# Build 100m grid
minx, miny, maxx, maxy = boundary.bounds
minx = math.floor(minx / RES) * RES
miny = math.floor(miny / RES) * RES
maxx = math.ceil(maxx / RES) * RES
maxy = math.ceil(maxy / RES) * RES

cells = []
cid = 0
for x in np.arange(minx, maxx, RES):
    for y in np.arange(miny, maxy, RES):
        geom = box(x, y, x+RES, y+RES)
        if geom.intersects(boundary):
            cells.append({"cell_id": cid, "geometry": geom})
            cid += 1

grid = gpd.GeoDataFrame(cells, crs=TARGET_CRS)

# Flood label
sj = gpd.sjoin(grid[["cell_id","geometry"]], floods[["geometry"]], predicate="intersects", how="left")
positive = set(sj.loc[sj.index_right.notna(), "cell_id"])
grid["bmc_flood_label"] = grid.cell_id.isin(positive).astype("int8")

# Drain distance
cent = grid[["cell_id","geometry"]].copy()
cent["geometry"] = cent.geometry.centroid
near = gpd.sjoin_nearest(cent, drains[["geometry"]], how="left", distance_col="distance_to_drain_m")
grid["distance_to_drain_m"] = near.groupby("cell_id").distance_to_drain_m.min().reindex(grid.cell_id).to_numpy()

# Drain density: exact clipped line length inside each cell
inter = gpd.overlay(grid[["cell_id","geometry"]], drains[["geometry"]], how="intersection", keep_geom_type=False)
inter = inter[inter.geometry.geom_type.isin(["LineString","MultiLineString"])]
inter["length_m"] = inter.geometry.length
dens = inter.groupby("cell_id").length_m.sum()
grid["drain_length_m"] = dens.reindex(grid.cell_id).fillna(0).to_numpy()
grid["drain_density_m_per_km2"] = grid["drain_length_m"] / 0.01

# Building density
buildings = read("buildings.geojson").to_crs(TARGET_CRS)
buildings = gpd.clip(buildings, boundary_gdf)
bint = gpd.overlay(grid[["cell_id","geometry"]], buildings[["geometry"]], how="intersection", keep_geom_type=False)
bint = bint[bint.geometry.geom_type.isin(["Polygon","MultiPolygon"])]
barea = bint.assign(area_m2=bint.geometry.area).groupby("cell_id").area_m2.sum()
grid["building_fraction"] = (barea.reindex(grid.cell_id).fillna(0).to_numpy() / 10000).clip(0,1)

# Road density
roads = read("roads.geojson").to_crs(TARGET_CRS)
roads = gpd.clip(roads, boundary_gdf)
rint = gpd.overlay(grid[["cell_id","geometry"]], roads[["geometry"]], how="intersection", keep_geom_type=False)
rint = rint[rint.geometry.geom_type.isin(["LineString","MultiLineString"])]
rlen = rint.assign(length_m=rint.geometry.length).groupby("cell_id").length_m.sum()
grid["road_length_m"] = rlen.reindex(grid.cell_id).fillna(0).to_numpy()
grid["road_density_m_per_km2"] = grid["road_length_m"] / 0.01

# DEM -> elevation and slope sampled at grid centroids.
dem_path = EXT / "dem_mumbai.tif"
if dem_path.exists():
    with rasterio.open(dem_path) as src:
        dem = src.read(1, masked=True)
        dem_res_x, dem_res_y = src.res
        # approximate slope in degrees from DEM gradients
        arr = dem.filled(np.nan).astype("float32")
        gy, gx = np.gradient(arr, abs(dem_res_y), abs(dem_res_x))
        slope = np.degrees(np.arctan(np.sqrt(gx*gx + gy*gy)))

        pts = grid.geometry.centroid
        coords = [(p.x,p.y) for p in pts]
        grid["elevation_m"] = [v[0] for v in src.sample(coords)]
        # Sample slope using nearest DEM pixel.
        from rasterio.transform import rowcol
        vals = []
        for p in pts:
            rr, cc = rowcol(src.transform, p.x, p.y)
            vals.append(float(slope[rr,cc]) if 0 <= rr < slope.shape[0] and 0 <= cc < slope.shape[1] and np.isfinite(slope[rr,cc]) else np.nan)
        grid["slope_deg"] = vals
else:
    print("[WARN] DEM not found; elevation/slope left empty.")

# WorldCover -> built-up and vegetation fraction.
wc_path = EXT / "worldcover_mumbai.tif"
if wc_path.exists():
    with rasterio.open(wc_path) as src:
        for idx, row in grid.iterrows():
            geom = [row.geometry]
            arr, _ = mask(src, geom, crop=True, nodata=0)
            vals = arr[0]
            vals = vals[vals != 0]
            if len(vals):
                grid.loc[idx, "built_up_fraction"] = float((vals == 50).mean())
                grid.loc[idx, "vegetation_fraction"] = float(np.isin(vals, [10,20,30,40]).mean())
                grid.loc[idx, "water_fraction"] = float(np.isin(vals, [80,90]).mean())
else:
    print("[WARN] WorldCover not found; land-cover fractions left empty.")

# Save
grid.to_file(PROCESSED / "model_grid_100m.gpkg", layer="grid", driver="GPKG")
grid.drop(columns="geometry").to_csv(PROCESSED / "model_features.csv", index=False)

print("Saved:", PROCESSED / "model_grid_100m.gpkg")
print("Saved:", PROCESSED / "model_features.csv")
