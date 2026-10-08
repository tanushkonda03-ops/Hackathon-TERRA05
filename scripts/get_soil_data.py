from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import geopandas as gpd


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

SOIL_DIR = (
    ROOT
    / "data"
    / "raw"
    / "external"
    / "soil"
)

PROCESSED_DIR = (
    ROOT
    / "data"
    / "processed"
)

GRID_GEOJSON = (
    PROCESSED_DIR
    / "flood_grid_100m.geojson"
)

OUTPUT_CSV = (
    PROCESSED_DIR
    / "soil_100m.csv"
)


# ============================================================
# SETTINGS
# ============================================================

MODEL_CRS = "EPSG:32643"

SOIL_PROPERTIES = [
    "clay",
    "sand",
    "silt",
]

DEPTH = "0-5cm"


# ============================================================
# DIRECTORIES
# ============================================================

SOIL_DIR.mkdir(
    parents=True,
    exist_ok=True
)

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# HEADER
# ============================================================

print("\n==============================================")
print(" MUMBAI SOIL DATA PROCESSING")
print("==============================================")


# ============================================================
# STEP 1 — LOAD GRID
# ============================================================

print("\n[1/6] Loading Mumbai grid...")

if not GRID_GEOJSON.exists():
    raise FileNotFoundError(
        f"Grid not found:\n{GRID_GEOJSON}"
    )

grid = gpd.read_file(
    GRID_GEOJSON
)

print(
    f"Grid cells: {len(grid):,}"
)

print(
    f"Original CRS: {grid.crs}"
)


# Make absolutely sure our modelling grid is projected.

grid = grid.to_crs(
    MODEL_CRS
)

print(
    f"Model CRS: {grid.crs}"
)


# ============================================================
# STEP 2 — FIND SOIL RASTERS
# ============================================================

print("\n[2/6] Locating SoilGrids rasters...")


soil_rasters = {}

for property_name in SOIL_PROPERTIES:

    raster_file = (
        SOIL_DIR
        / f"{property_name}_{DEPTH}_mumbai.tif"
    )

    if not raster_file.exists():

        raise FileNotFoundError(
            f"Missing SoilGrids raster:\n"
            f"{raster_file}"
        )

    soil_rasters[
        property_name
    ] = raster_file

    print(
        f"{property_name}: "
        f"{raster_file.name}"
    )


# ============================================================
# STEP 3 — SAMPLE EACH SOIL PROPERTY
# ============================================================

print(
    "\n[3/6] Sampling SoilGrids at 100m grid centroids..."
)


# ------------------------------------------------------------
# IMPORTANT
# ------------------------------------------------------------
#
# SoilGrids is approximately 250m resolution.
#
# Our model grid is 100m.
#
# We therefore SAMPLE the SoilGrids surface onto our 100m
# modelling grid.
#
# This does NOT increase the true resolution of the soil data.
# ------------------------------------------------------------


centroids = grid.geometry.centroid

soil_data = {
    "grid_id":
        grid["grid_id"].to_numpy()
}


for property_name, raster_file in soil_rasters.items():

    print(
        f"\nProcessing {property_name}..."
    )

    with rasterio.open(
        raster_file
    ) as src:

        # ----------------------------------------------------
        # Transform grid centroids into raster CRS
        # ----------------------------------------------------

        centroid_points = (
            gpd.GeoSeries(
                centroids,
                crs=MODEL_CRS
            )
            .to_crs(src.crs)
        )

        xs = (
            centroid_points.x.to_numpy()
        )

        ys = (
            centroid_points.y.to_numpy()
        )

        # ----------------------------------------------------
        # Convert coordinates to raster cells
        # ----------------------------------------------------

        rows, cols = (
            rasterio.transform.rowcol(
                src.transform,
                xs,
                ys
            )
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
            &
            (rows < src.height)
            &
            (cols >= 0)
            &
            (cols < src.width)
        )

        values = np.full(
            len(grid),
            np.nan,
            dtype="float64"
        )

        raster_data = (
            src.read(1)
            .astype("float64")
        )

        # ----------------------------------------------------
        # Sample raster
        # ----------------------------------------------------

        values[
            valid_points
        ] = raster_data[
            rows[valid_points],
            cols[valid_points]
        ]

        # ----------------------------------------------------
        # Handle explicit NoData
        # ----------------------------------------------------

        if src.nodata is not None:

            values[
                values == src.nodata
            ] = np.nan

        soil_data[
            f"{property_name}_raw"
        ] = values

        print(
            f"Valid samples: "
            f"{np.isfinite(values).sum():,}"
            f" / {len(values):,}"
        )


# ============================================================
# STEP 4 — CONVERT SOILGRIDS UNITS
# ============================================================

print(
    "\n[4/6] Converting SoilGrids units..."
)


soil_df = pd.DataFrame(
    soil_data
)


# SoilGrids texture values are represented as g/kg.
#
# Conversion:
#
# 100 g/kg = 10%
#
# therefore:
#
# percentage = g/kg / 10


soil_df[
    "clay_percent"
] = (
    soil_df[
        "clay_raw"
    ] / 10.0
)

soil_df[
    "sand_percent"
] = (
    soil_df[
        "sand_raw"
    ] / 10.0
)

soil_df[
    "silt_percent"
] = (
    soil_df[
        "silt_raw"
    ] / 10.0
)


# ============================================================
# STEP 5 — DERIVED FEATURES
# ============================================================

print(
    "\n[5/6] Creating derived soil features..."
)


# ------------------------------------------------------------
# Texture sum
# ------------------------------------------------------------
#
# This is ONLY diagnostic.
#
# We do NOT force the values to sum to 100%.
# ------------------------------------------------------------

soil_df[
    "texture_sum_percent"
] = (
    soil_df["clay_percent"]
    + soil_df["sand_percent"]
    + soil_df["silt_percent"]
)


# ------------------------------------------------------------
# Soil texture class
# ------------------------------------------------------------
#
# This is a simplified model feature, not an official
# detailed soil-survey classification.
# ------------------------------------------------------------

def classify_texture(
    clay,
    sand,
    silt
):

    if (
        np.isnan(clay)
        or np.isnan(sand)
        or np.isnan(silt)
    ):
        return "Unknown"

    if clay >= 40:
        return "Clay_Dominant"

    if sand >= 70:
        return "Sand_Dominant"

    if silt >= 50:
        return "Silt_Dominant"

    if clay >= 27 and sand < 50:
        return "Clay_Loam"

    if sand >= 50 and clay < 27:
        return "Sandy_Loam"

    if (
        clay < 27
        and sand < 50
        and silt < 50
    ):
        return "Loam"

    return "Mixed"


soil_df[
    "soil_class"
] = [
    classify_texture(
        clay,
        sand,
        silt
    )
    for clay, sand, silt
    in zip(
        soil_df["clay_percent"],
        soil_df["sand_percent"],
        soil_df["silt_percent"]
    )
]


# ------------------------------------------------------------
# Infiltration proxy
# ------------------------------------------------------------
#
# This is NOT measured hydraulic conductivity.
#
# It is simply a normalized texture-derived indicator.
#
# Higher sand -> generally more infiltration
# Higher clay -> generally less infiltration
# ------------------------------------------------------------

sand_score = np.clip(
    soil_df["sand_percent"] / 80.0,
    0,
    1
)

clay_score = (
    1
    - np.clip(
        soil_df["clay_percent"] / 60.0,
        0,
        1
    )
)

soil_df[
    "infiltration_proxy"
] = (
    0.6 * sand_score
    + 0.4 * clay_score
)


# ============================================================
# CLEAN NUMERIC VALUES
# ============================================================

for column in [
    "clay_percent",
    "sand_percent",
    "silt_percent",
    "texture_sum_percent",
    "infiltration_proxy",
]:

    soil_df[
        column
    ] = soil_df[
        column
    ].replace(
        [np.inf, -np.inf],
        np.nan
    )


# ============================================================
# FINAL DATASET
# ============================================================

final_columns = [
    "grid_id",

    "clay_percent",
    "sand_percent",
    "silt_percent",

    "soil_class",

    "infiltration_proxy",
]


final_df = soil_df[
    final_columns
].copy()


# ============================================================
# SAVE
# ============================================================

final_df.to_csv(
    OUTPUT_CSV,
    index=False
)


# ============================================================
# VALIDATION REPORT
# ============================================================

print(
    "\n[6/6] Validating soil dataset..."
)


print("\n==============================================")
print(" SOIL PROCESSING COMPLETE")
print("==============================================")


print(
    "\nOutput:"
)

print(
    OUTPUT_CSV
)


print(
    "\nRows:"
)

print(
    len(final_df)
)


print(
    "\nNumeric statistics:"
)

print(
    final_df[
        [
            "clay_percent",
            "sand_percent",
            "silt_percent",
            "infiltration_proxy",
        ]
    ].describe()
)


print(
    "\nTexture distribution:"
)

print(
    final_df[
        "soil_class"
    ].value_counts(
        dropna=False
    )
)


print(
    "\nMissing values:"
)

print(
    final_df.isna().sum()
)


# ============================================================
# SANITY CHECKS
# ============================================================

print(
    "\nSanity checks:"
)


for column in [
    "clay_percent",
    "sand_percent",
    "silt_percent",
]:

    negative_count = (
        final_df[column] < 0
    ).sum()

    print(
        f"{column} negative values: "
        f"{negative_count}"
    )


texture_sum = (
    final_df[
        "clay_percent"
    ]
    + final_df[
        "sand_percent"
    ]
    + final_df[
        "silt_percent"
    ]
)

print(
    "\nTexture sum statistics:"
)

print(
    texture_sum.describe()
)


print(
    "\n=============================================="
)

print(
    "IMPORTANT:"
)

print(
    "SoilGrids source resolution is approximately 250m."
)

print(
    "Values were sampled onto the 100m modelling grid."
)

print(
    "infiltration_proxy is a derived texture proxy, "
    "NOT measured hydraulic conductivity."
)

print(
    "=============================================="
)

print(
    "\nDone."
)