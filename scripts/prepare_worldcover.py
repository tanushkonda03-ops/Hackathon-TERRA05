from pathlib import Path

import numpy as np
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

EXTERNAL = PROJECT_ROOT / "data" / "raw" / "external"
BMC = PROJECT_ROOT / "data" / "raw" / "bmc"

WORLD_COVER = EXTERNAL / "worldcover_N18E072.tif"
WARD_FILE = BMC / "wards.geojson"

CLIPPED = EXTERNAL / "worldcover_mumbai.tif"
UTM_OUTPUT = EXTERNAL / "worldcover_mumbai_utm43.tif"


# ============================================================
# SETTINGS
# ============================================================

TARGET_CRS = "EPSG:32643"


# WorldCover classes
BUILT_UP = 50

VEGETATION = {
    10,  # Tree cover
    20,  # Shrubland
    30,  # Grassland
    40,  # Cropland
}

WATER = {
    80,  # Permanent water
    90,  # Herbaceous wetland
}


# ============================================================
# VALIDATE INPUTS
# ============================================================

if not WORLD_COVER.exists():
    raise FileNotFoundError(
        f"WorldCover not found:\n{WORLD_COVER}"
    )

if not WARD_FILE.exists():
    raise FileNotFoundError(
        f"Wards file not found:\n{WARD_FILE}"
    )


# ============================================================
# LOAD WORLD COVER
# ============================================================

print()
print("=" * 70)
print("WORLD COVER PROCESSING")
print("=" * 70)

print()
print("[OPEN] WorldCover")

with rasterio.open(WORLD_COVER) as src:

    print(f"CRS:        {src.crs}")
    print(f"Resolution: {src.res}")
    print(f"Width:      {src.width}")
    print(f"Height:     {src.height}")
    print(f"Bounds:     {src.bounds}")

    worldcover_crs = src.crs

    # --------------------------------------------------------
    # Load Mumbai wards
    # --------------------------------------------------------

    print()
    print("[BOUNDARY] Loading BMC wards")

    wards = gpd.read_file(WARD_FILE)

    if wards.empty:
        raise RuntimeError("BMC wards file is empty.")

    print(f"[BOUNDARY] {len(wards)} wards")

    # Match WorldCover CRS
    wards = wards.to_crs(src.crs)

    # Dissolve all wards into one Mumbai boundary
    mumbai = wards.dissolve()

    geometries = mumbai.geometry.values

    # --------------------------------------------------------
    # Clip WorldCover
    # --------------------------------------------------------

    print()
    print("[CLIP] Clipping WorldCover to Mumbai")

    clipped, clipped_transform = mask(
        src,
        geometries,
        crop=True,
        nodata=0
    )

    clipped_profile = src.profile.copy()

    clipped_profile.update(
        driver="GTiff",
        height=clipped.shape[1],
        width=clipped.shape[2],
        transform=clipped_transform,
        nodata=0,
        compress="deflate",
        predictor=2,
        tiled=False
    )

    with rasterio.open(CLIPPED, "w", **clipped_profile) as dst:
        dst.write(clipped)

print(f"[SAVED] {CLIPPED}")


# ============================================================
# REPROJECT TO UTM 43N
# ============================================================

print()
print("[REPROJECT] WorldCover → EPSG:32643")

with rasterio.open(CLIPPED) as src:

    transform, width, height = calculate_default_transform(
        src.crs,
        TARGET_CRS,
        src.width,
        src.height,
        *src.bounds
    )

    profile = src.profile.copy()

    profile.update(
        crs=TARGET_CRS,
        transform=transform,
        width=width,
        height=height,
        compress="deflate",
        predictor=2,
        tiled=False,
        nodata=0
    )

    with rasterio.open(UTM_OUTPUT, "w", **profile) as dst:

        reproject(
            source=rasterio.band(src, 1),
            destination=rasterio.band(dst, 1),

            src_transform=src.transform,
            src_crs=src.crs,

            dst_transform=transform,
            dst_crs=TARGET_CRS,

            resampling=Resampling.nearest,

            src_nodata=0,
            dst_nodata=0
        )


print(f"[SAVED] {UTM_OUTPUT}")


# ============================================================
# VALIDATE CLASSES
# ============================================================

print()
print("[VALIDATE] Checking WorldCover classes")

with rasterio.open(UTM_OUTPUT) as src:

    data = src.read(1)

    valid = data[data != 0]

    unique, counts = np.unique(
        valid,
        return_counts=True
    )

    print()
    print("WorldCover classes found:")

    for cls, count in zip(unique, counts):

        percentage = (
            count / len(valid) * 100
        )

        print(
            f"  Class {int(cls):>3}: "
            f"{count:,} pixels "
            f"({percentage:.2f}%)"
        )

    # --------------------------------------------------------
    # Calculate basic fractions
    # --------------------------------------------------------

    built_up_pixels = np.isin(
        valid,
        [BUILT_UP]
    ).sum()

    vegetation_pixels = np.isin(
        valid,
        list(VEGETATION)
    ).sum()

    water_pixels = np.isin(
        valid,
        list(WATER)
    ).sum()

    total = len(valid)

    print()
    print("Overall Mumbai land-cover fractions:")
    print(
        f"  Built-up:   {built_up_pixels / total * 100:.2f}%"
    )
    print(
        f"  Vegetation: {vegetation_pixels / total * 100:.2f}%"
    )
    print(
        f"  Water:      {water_pixels / total * 100:.2f}%"
    )

    print()
    print(f"CRS:        {src.crs}")
    print(f"Resolution: {src.res}")
    print(f"Width:      {src.width}")
    print(f"Height:     {src.height}")
    print(f"Bounds:     {src.bounds}")


print()
print("=" * 70)
print("WORLD COVER PROCESSING COMPLETE")
print("=" * 70)

print()
print("Created:")
print(f"  {CLIPPED}")
print(f"  {UTM_OUTPUT}")

print()
print("Next:")
print("  Build 100m grid features from WorldCover + DEM.")