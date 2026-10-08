from pathlib import Path
import warnings

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask
from rasterio.features import geometry_mask
from shapely.geometry import box
from shapely.ops import unary_union
from scipy.ndimage import distance_transform_edt

warnings.filterwarnings("ignore")

# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA = PROJECT_ROOT / "data"

BMC = DATA / "raw" / "bmc"
EXTERNAL = DATA / "raw" / "external"
PROCESSED = DATA / "processed"

PROCESSED.mkdir(parents=True, exist_ok=True)

# ============================================================
# INPUTS
# ============================================================

WARD_FILE = BMC / "wards.geojson"
FLOOD_FILE = DATA / "raw" / "flooding_spots_clean.geojson"
DRAIN_FILE = DATA / "raw" / "storm_water_drains.geojson"
HYDRO_FILE = BMC / "hydro_lines.geojson"
BUILDING_FILE = BMC / "buildings.geojson"

DEM_FILE = EXTERNAL / "dem_mumbai_utm43.tif"
SLOPE_FILE = EXTERNAL / "slope_mumbai_utm43.tif"
WORLDCOVER_FILE = EXTERNAL / "worldcover_mumbai_utm43.tif"

# ============================================================
# CONSTANTS
# ============================================================

TARGET_CRS = "EPSG:32643"
GRID_SIZE = 100  # metres

# ============================================================
# LOAD BOUNDARY
# ============================================================

print("=" * 70)
print("BUILDING 100m FLOOD PREDICTION GRID")
print("=" * 70)

print("\n[1/8] Loading Mumbai boundary...")

wards = gpd.read_file(WARD_FILE)

print(f"Wards loaded: {len(wards)}")

wards = wards.to_crs(TARGET_CRS)

# Dissolve all wards into one Mumbai boundary
mumbai_boundary = wards.geometry.union_all()

print(f"Boundary CRS: {TARGET_CRS}")

# ============================================================
# CREATE 100m GRID
# ============================================================

print("\n[2/8] Creating 100m × 100m grid...")

minx, miny, maxx, maxy = mumbai_boundary.bounds

xs = np.arange(minx, maxx, GRID_SIZE)
ys = np.arange(miny, maxy, GRID_SIZE)

cells = []

grid_id = 0

for x in xs:
    for y in ys:

        cell = box(
            x,
            y,
            x + GRID_SIZE,
            y + GRID_SIZE
        )

        if cell.intersects(mumbai_boundary):

            clipped = cell.intersection(mumbai_boundary)

            if not clipped.is_empty:

                cells.append({
                    "grid_id": grid_id,
                    "geometry": clipped
                })

                grid_id += 1

grid = gpd.GeoDataFrame(
    cells,
    crs=TARGET_CRS
)

print(f"Grid cells created: {len(grid)}")

# ============================================================
# ASSIGN WARD
# ============================================================

print("\n[3/8] Assigning wards...")

ward_cols = [
    c for c in wards.columns
    if c.lower() in [
        "name",
        "ward",
        "ward_name",
        "ward_no",
        "wardno"
    ]
]

if ward_cols:

    ward_col = ward_cols[0]

    centroids = grid.geometry.centroid

    centroid_gdf = gpd.GeoDataFrame(
        grid[["grid_id"]].copy(),
        geometry=centroids,
        crs=TARGET_CRS
    )

    joined = gpd.sjoin(
        centroid_gdf,
        wards[[ward_col, "geometry"]],
        how="left",
        predicate="within"
    )

    grid["ward"] = joined.set_index("grid_id")[ward_col]

else:

    print("WARNING: Ward name column not found.")

    grid["ward"] = None

# ============================================================
# HELPER: RASTER MEAN
# ============================================================

def raster_mean_per_cell(grid_gdf, raster_path):

    values = []

    with rasterio.open(raster_path) as src:

        for geom in grid_gdf.geometry:

            try:

                data, _ = mask(
                    src,
                    [geom],
                    crop=True,
                    filled=False
                )

                arr = data[0]

                if arr.count() == 0:
                    values.append(np.nan)
                else:
                    values.append(float(arr.mean()))

            except Exception:
                values.append(np.nan)

    return values


# ============================================================
# TERRAIN
# ============================================================

print("\n[4/8] Extracting terrain features...")

grid["elevation_mean"] = raster_mean_per_cell(
    grid,
    DEM_FILE
)

grid["slope_mean"] = raster_mean_per_cell(
    grid,
    SLOPE_FILE
)

print("Elevation and slope complete.")

# ============================================================
# WORLDCOVER FEATURES
# ============================================================

print("\n[5/8] Extracting land-cover features...")

worldcover_values = []

with rasterio.open(WORLDCOVER_FILE) as src:

    for i, geom in enumerate(grid.geometry):

        try:

            data, _ = mask(
                src,
                [geom],
                crop=True,
                filled=False
            )

            arr = data[0].compressed()

            if len(arr) == 0:

                worldcover_values.append(
                    (np.nan, np.nan, np.nan, np.nan)
                )

                continue

            total = len(arr)

            built = np.sum(arr == 50)
            vegetation = np.sum(
                np.isin(arr, [10, 20, 30, 40])
            )
            water = np.sum(
                np.isin(arr, [80, 90])
            )
            mangrove = np.sum(arr == 95)

            worldcover_values.append(
                (
                    built / total,
                    vegetation / total,
                    water / total,
                    mangrove / total
                )
            )

        except Exception:

            worldcover_values.append(
                (np.nan, np.nan, np.nan, np.nan)
            )

grid[
    [
        "built_up_fraction",
        "vegetation_fraction",
        "water_fraction",
        "mangrove_fraction"
    ]
] = pd.DataFrame(
    worldcover_values,
    index=grid.index
)

print("WorldCover features complete.")

# ============================================================
# VECTOR FEATURE HELPER
# ============================================================

print("\n[6/8] Calculating drainage / water / building features...")


def prepare_vector(path):

    gdf = gpd.read_file(path)

    print(f"Loaded {path.name}: {len(gdf)} features")

    gdf = gdf[
        gdf.geometry.notna() &
        ~gdf.geometry.is_empty
    ].copy()

    return gdf.to_crs(TARGET_CRS)


drains = prepare_vector(DRAIN_FILE)
hydro = prepare_vector(HYDRO_FILE)
buildings = prepare_vector(BUILDING_FILE)


# ============================================================
# DRAINAGE FEATURES
# ============================================================

print("Calculating drainage density...")

drain_lengths = []

for cell in grid.geometry:

    total_length = 0.0

    possible = drains[
        drains.geometry.intersects(cell)
    ]

    for geom in possible.geometry:

        intersection = geom.intersection(cell)

        if not intersection.is_empty:
            total_length += intersection.length

    # km of drain / km²
    density = (total_length / 1000.0) / 0.01

    drain_lengths.append(density)

grid["drain_density"] = drain_lengths


print("Calculating distance to nearest drain...")

drain_union = unary_union(drains.geometry)

grid["distance_to_drain"] = grid.geometry.centroid.apply(
    lambda p: p.distance(drain_union)
)


# ============================================================
# WATER DISTANCE
# ============================================================

print("Calculating distance to water...")

hydro_union = unary_union(hydro.geometry)

grid["distance_to_water"] = grid.geometry.centroid.apply(
    lambda p: p.distance(hydro_union)
)


# ============================================================
# BUILDING FEATURES
# ============================================================

print("Calculating building density...")

building_counts = []

for cell in grid.geometry:

    count = buildings.geometry.intersects(cell).sum()

    building_counts.append(count)

grid["building_count"] = building_counts

# buildings per km²
grid["building_density"] = (
    grid["building_count"] / 0.01
)


# ============================================================
# HISTORICAL FLOOD LABEL
# ============================================================

print("\n[7/8] Creating historical flood labels...")

floods = gpd.read_file(FLOOD_FILE)

floods = floods[
    floods.geometry.notna() &
    ~floods.geometry.is_empty
].copy()

floods = floods.to_crs(TARGET_CRS)

print(f"Historical flood polygons: {len(floods)}")

flood_union = unary_union(floods.geometry)

flood_fraction = []

for cell in grid.geometry:

    intersection = cell.intersection(flood_union)

    if intersection.is_empty:

        fraction = 0.0

    else:

        fraction = (
            intersection.area /
            cell.area
        )

    flood_fraction.append(fraction)

grid["flood_fraction"] = flood_fraction

# Any meaningful historical overlap = positive
grid["flood_label"] = (
    grid["flood_fraction"] > 0.05
).astype(int)


# ============================================================
# CLEAN NUMERIC DATA
# ============================================================

print("\n[8/8] Cleaning and saving dataset...")

numeric_columns = [
    "elevation_mean",
    "slope_mean",
    "built_up_fraction",
    "vegetation_fraction",
    "water_fraction",
    "mangrove_fraction",
    "drain_density",
    "distance_to_drain",
    "distance_to_water",
    "building_count",
    "building_density",
    "flood_fraction"
]

for col in numeric_columns:

    grid[col] = pd.to_numeric(
        grid[col],
        errors="coerce"
    )


# Remove cells with missing terrain
grid = grid.dropna(
    subset=[
        "elevation_mean",
        "slope_mean"
    ]
).copy()


# ============================================================
# SAVE
# ============================================================

geojson_output = (
    PROCESSED /
    "flood_grid_100m.geojson"
)

csv_output = (
    PROCESSED /
    "flood_grid_100m.csv"
)

grid.to_file(
    geojson_output,
    driver="GeoJSON"
)

grid.drop(
    columns="geometry"
).to_csv(
    csv_output,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("100m GRID COMPLETE")
print("=" * 70)

print(f"Grid cells: {len(grid):,}")

print(
    f"Flood-positive cells: "
    f"{grid['flood_label'].sum():,}"
)

print(
    f"Flood-positive %: "
    f"{grid['flood_label'].mean() * 100:.2f}%"
)

print("\nFEATURES:")

for col in grid.columns:
    print("  ", col)

print("\nOUTPUT:")
print(geojson_output)
print(csv_output)

print("=" * 70)