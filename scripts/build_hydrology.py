from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import geopandas as gpd
from pysheds.grid import Grid


# ============================================================
# NUMPY / PYSheds COMPATIBILITY
# ============================================================

# Newer NumPy versions removed np.in1d(), but the version of
# pysheds being used still calls it internally.
if not hasattr(np, "in1d"):
    np.in1d = np.isin


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DEM_FILE = (
    ROOT
    / "data"
    / "raw"
    / "external"
    / "dem_mumbai_utm43.tif"
)

GRID_FILE = (
    ROOT
    / "data"
    / "processed"
    / "flood_grid_100m.csv"
)

GRID_GEOJSON = (
    ROOT
    / "data"
    / "processed"
    / "flood_grid_100m.geojson"
)

OUTPUT_DIR = (
    ROOT
    / "data"
    / "processed"
)

FLOW_ACC_RASTER = (
    OUTPUT_DIR
    / "flow_accumulation_mumbai.tif"
)

HYDROLOGY_CSV = (
    OUTPUT_DIR
    / "hydrology_100m.csv"
)


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# HEADER
# ============================================================

print("\n==============================================")
print(" MUMBAI HYDROLOGY-LITE PROCESSING")
print("==============================================")


# ============================================================
# CHECK INPUT FILES
# ============================================================

print("\nChecking input files...")

if not DEM_FILE.exists():
    raise FileNotFoundError(
        f"DEM not found:\n{DEM_FILE}"
    )

if not GRID_FILE.exists():
    raise FileNotFoundError(
        f"Grid CSV not found:\n{GRID_FILE}"
    )

if not GRID_GEOJSON.exists():
    raise FileNotFoundError(
        f"Grid GeoJSON not found:\n{GRID_GEOJSON}"
    )

print("All input files found.")


# ============================================================
# STEP 1 — LOAD DEM
# ============================================================

print("\n[1/7] Loading DEM...")

with rasterio.open(DEM_FILE) as src:

    dem = src.read(1).astype("float64")

    profile = src.profile.copy()

    transform = src.transform

    crs = src.crs

    nodata = src.nodata

    resolution = src.res

    dem_width = src.width
    dem_height = src.height


print(f"CRS        : {crs}")
print(f"Size       : {dem_width} x {dem_height}")
print(f"Resolution : {resolution}")
print(f"NoData     : {nodata}")


# ------------------------------------------------------------
# Convert NoData to NaN
# ------------------------------------------------------------

if nodata is not None:

    dem[dem == nodata] = np.nan


valid = np.isfinite(dem)

print(f"Valid cells : {valid.sum():,}")

print(
    f"Min elevation : "
    f"{np.nanmin(dem):.2f} m"
)

print(
    f"Max elevation : "
    f"{np.nanmax(dem):.2f} m"
)


# ============================================================
# STEP 2 — CREATE PYSheds GRID
# ============================================================

print("\n[2/7] Creating hydrological grid...")

grid = Grid.from_raster(
    str(DEM_FILE)
)

dem_pysheds = grid.read_raster(
    str(DEM_FILE)
)

print("DEM loaded into pysheds.")


# ============================================================
# STEP 3 — FILL DEPRESSIONS
# ============================================================

print("\n[3/7] Filling small DEM depressions...")

filled_dem = grid.fill_depressions(
    dem_pysheds
)

filled_dem = grid.resolve_flats(
    filled_dem
)

print("Depression filling completed.")


# ============================================================
# STEP 4 — FLOW DIRECTION
# ============================================================

print("\n[4/7] Calculating flow direction...")

fdir = grid.flowdir(
    filled_dem,
    routing="d8"
)

print("Flow direction calculated.")


# ============================================================
# STEP 5 — FLOW ACCUMULATION
# ============================================================

print("\n[5/7] Calculating flow accumulation...")

acc = grid.accumulation(
    fdir,
    routing="d8"
)

acc_array = np.asarray(
    acc,
    dtype="float64"
)

# Convert invalid values to NaN
acc_array[
    ~np.isfinite(acc_array)
] = np.nan


valid_acc = np.isfinite(
    acc_array
)

print("Flow accumulation calculated.")

print(
    f"Accumulation min : "
    f"{np.nanmin(acc_array):.2f}"
)

print(
    f"Accumulation max : "
    f"{np.nanmax(acc_array):.2f}"
)

print(
    f"Accumulation mean : "
    f"{np.nanmean(acc_array):.2f}"
)


# ============================================================
# STEP 6 — SAVE FLOW ACCUMULATION RASTER
# ============================================================

print("\n[6/7] Saving flow accumulation raster...")

acc_profile = profile.copy()

acc_profile.update(
    dtype="float32",
    count=1,
    nodata=-9999.0,
    compress="lzw"
)

acc_output = np.where(
    np.isfinite(acc_array),
    acc_array,
    -9999.0
).astype("float32")


with rasterio.open(
    FLOW_ACC_RASTER,
    "w",
    **acc_profile
) as dst:

    dst.write(
        acc_output,
        1
    )


print(
    f"Saved: {FLOW_ACC_RASTER}"
)


# ============================================================
# STEP 7 — AGGREGATE TO 100m GRID
# ============================================================

print(
    "\n[7/7] Aggregating hydrology to 100m grid..."
)


# ------------------------------------------------------------
# Load existing grid
# ------------------------------------------------------------

grid_df = pd.read_csv(
    GRID_FILE
)

print(
    f"Existing grid cells: "
    f"{len(grid_df):,}"
)


# ------------------------------------------------------------
# Load grid geometry
# ------------------------------------------------------------

gdf = gpd.read_file(
    GRID_GEOJSON
)

print(
    f"Grid geometry cells: "
    f"{len(gdf):,}"
)


# ------------------------------------------------------------
# Verify grid IDs match
# ------------------------------------------------------------

if not np.array_equal(
    grid_df["grid_id"].to_numpy(),
    gdf["grid_id"].to_numpy()
):

    print(
        "Grid ordering differs between CSV and GeoJSON."
    )

    # Safely reorder GeoDataFrame to match CSV
    gdf = gdf.merge(
        grid_df[["grid_id"]],
        on="grid_id",
        how="right"
    )


# ============================================================
# GRID CENTROIDS
# ============================================================

print("\nSampling DEM at grid centroids...")

centroids = gdf.geometry.centroid

xs = centroids.x.to_numpy()
ys = centroids.y.to_numpy()


# ============================================================
# CONVERT COORDINATES → DEM ROW/COLUMN
# ============================================================

with rasterio.open(
    DEM_FILE
) as src:

    rows, cols = rasterio.transform.rowcol(
        src.transform,
        xs,
        ys
    )

    rows = np.asarray(
        rows,
        dtype=int
    )

    cols = np.asarray(
        cols,
        dtype=int
    )

    valid_points = (
        (rows >= 0)
        & (rows < src.height)
        & (cols >= 0)
        & (cols < src.width)
    )


print(
    f"Valid grid centroids: "
    f"{valid_points.sum():,} / {len(gdf):,}"
)


# ============================================================
# FLOW ACCUMULATION AT GRID CENTROIDS
# ============================================================

flow_accumulation = np.full(
    len(gdf),
    np.nan,
    dtype="float64"
)

flow_accumulation[
    valid_points
] = acc_array[
    rows[valid_points],
    cols[valid_points]
]


# ============================================================
# FLOW ACCUMULATION → AREA
# ============================================================

cell_area_m2 = (
    resolution[0]
    * resolution[1]
)

flow_area_km2 = (
    flow_accumulation
    * cell_area_m2
    / 1_000_000
)


# ============================================================
# ELEVATION AT GRID CENTROIDS
# ============================================================

print(
    "Sampling elevation at grid centroids..."
)

with rasterio.open(
    DEM_FILE
) as src:

    dem_array = src.read(
        1
    ).astype("float64")

    elevation_values = np.full(
        len(gdf),
        np.nan,
        dtype="float64"
    )

    sampled_elevation = dem_array[
        rows[valid_points],
        cols[valid_points]
    ]

    # --------------------------------------------------------
    # IMPORTANT:
    # Convert DEM NoData (-9999) to NaN.
    # Never allow -9999 into the ML dataset.
    # --------------------------------------------------------

    if src.nodata is not None:

        sampled_elevation[
            sampled_elevation == src.nodata
        ] = np.nan

    elevation_values[
        valid_points
    ] = sampled_elevation


# ============================================================
# ADD FEATURES
# ============================================================

gdf[
    "flow_accumulation"
] = flow_accumulation

gdf[
    "flow_accumulation_area_km2"
] = flow_area_km2

gdf[
    "elevation_centroid"
] = elevation_values


# ============================================================
# LOG TRANSFORM
# ============================================================

# Flow accumulation is highly skewed.
#
# Example:
#
# Most cells → accumulation close to 1–10
# Some cells → thousands or tens of thousands
#
# log1p keeps the information while reducing the extreme
# scale difference.

gdf[
    "flow_accumulation_log"
] = np.log1p(
    gdf["flow_accumulation"]
)


# ============================================================
# SELECT OUTPUT FEATURES
# ============================================================

hydrology_columns = [
    "grid_id",

    "flow_accumulation",

    "flow_accumulation_area_km2",

    "flow_accumulation_log",

    "elevation_centroid",
]


hydrology_df = gdf[
    hydrology_columns
].copy()


# ============================================================
# FINAL CLEANING
# ============================================================

print("\nCleaning hydrology dataset...")


# Convert impossible values to NaN

hydrology_df[
    "flow_accumulation"
] = hydrology_df[
    "flow_accumulation"
].replace(
    [np.inf, -np.inf],
    np.nan
)

hydrology_df[
    "flow_accumulation_area_km2"
] = hydrology_df[
    "flow_accumulation_area_km2"
].replace(
    [np.inf, -np.inf],
    np.nan
)

hydrology_df[
    "flow_accumulation_log"
] = hydrology_df[
    "flow_accumulation_log"
].replace(
    [np.inf, -np.inf],
    np.nan
)

hydrology_df[
    "elevation_centroid"
] = hydrology_df[
    "elevation_centroid"
].replace(
    [np.inf, -np.inf],
    np.nan
)


# ============================================================
# SAVE HYDROLOGY CSV
# ============================================================

hydrology_df.to_csv(
    HYDROLOGY_CSV,
    index=False
)


# ============================================================
# FINAL REPORT
# ============================================================

print("\n==============================================")
print(" HYDROLOGY PROCESSING COMPLETE")
print("==============================================")


print("\nOutput raster:")
print(
    FLOW_ACC_RASTER
)


print("\nOutput CSV:")
print(
    HYDROLOGY_CSV
)


print("\nHydrology statistics:")

print(
    hydrology_df[
        [
            "flow_accumulation",
            "flow_accumulation_area_km2",
            "flow_accumulation_log",
            "elevation_centroid",
        ]
    ].describe()
)


print("\nMissing values:")

print(
    hydrology_df.isna().sum()
)


print("\nInvalid -9999 values:")

for column in hydrology_df.columns:

    count = (
        hydrology_df[column] == -9999
    ).sum()

    if count > 0:

        print(
            f"{column}: {count}"
        )


print("\nFinal rows:")
print(
    len(hydrology_df)
)

print("\nDone.")