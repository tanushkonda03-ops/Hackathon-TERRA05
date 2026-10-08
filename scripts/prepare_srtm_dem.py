from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.fill import fillnodata


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_DEM = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "external"
    / "dem_mumbai.tif"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "external"
)

OUTPUT_DEM = OUTPUT_DIR / "dem_mumbai_utm43.tif"
OUTPUT_SLOPE = OUTPUT_DIR / "slope_mumbai_utm43.tif"

TARGET_CRS = "EPSG:32643"
NODATA = -9999.0


print("=" * 70)
print("SRTM DEM PROCESSING")
print("=" * 70)


# ============================================================
# 1. CHECK INPUT
# ============================================================

if not INPUT_DEM.exists():
    raise FileNotFoundError(
        f"SRTM DEM not found:\n{INPUT_DEM}"
    )


# ============================================================
# 2. INSPECT INPUT
# ============================================================

print("\n[INPUT] SRTM DEM")

with rasterio.open(INPUT_DEM) as src:

    print(f"  CRS:        {src.crs}")
    print(f"  Resolution: {src.res}")
    print(f"  Width:      {src.width}")
    print(f"  Height:     {src.height}")
    print(f"  Bounds:     {src.bounds}")
    print(f"  NoData:     {src.nodata}")


# ============================================================
# 3. REPROJECT TO UTM 43N
# ============================================================

print("\n[REPROJECT] SRTM DEM -> EPSG:32643")

with rasterio.open(INPUT_DEM) as src:

    transform, width, height = calculate_default_transform(
        src.crs,
        TARGET_CRS,
        src.width,
        src.height,
        *src.bounds
    )

    profile = src.profile.copy()

    profile.update(
        driver="GTiff",
        crs=TARGET_CRS,
        transform=transform,
        width=width,
        height=height,
        dtype="float32",
        nodata=NODATA,
        compress="deflate"
    )

    with rasterio.open(OUTPUT_DEM, "w", **profile) as dst:

        reproject(
            source=rasterio.band(src, 1),
            destination=rasterio.band(dst, 1),

            src_transform=src.transform,
            src_crs=src.crs,

            dst_transform=transform,
            dst_crs=TARGET_CRS,

            src_nodata=src.nodata,
            dst_nodata=NODATA,

            resampling=Resampling.bilinear
        )

print(f"[SAVED] {OUTPUT_DEM}")


# ============================================================
# 4. CALCULATE SLOPE
# ============================================================

print("\n[SLOPE] Calculating slope...")

with rasterio.open(OUTPUT_DEM) as src:

    dem = src.read(1).astype("float32")

    pixel_x = abs(src.transform.a)
    pixel_y = abs(src.transform.e)

    valid = (
        np.isfinite(dem)
        & (dem != NODATA)
    )

    print(f"  Valid pixels:  {valid.sum():,}")
    print(f"  NoData pixels: {(~valid).sum():,}")

    # Temporarily fill NoData areas so they don't
    # create artificial slopes.
    work = dem.copy()
    work[~valid] = np.nan

    filled = fillnodata(
        work,
        mask=np.isfinite(work),
        max_search_distance=100
    )

    # Fallback for any remaining NaN
    remaining = ~np.isfinite(filled)

    if remaining.any():
        filled[remaining] = np.nanmean(filled)

    # Calculate terrain gradient
    dz_dy, dz_dx = np.gradient(
        filled,
        pixel_y,
        pixel_x
    )

    # Convert gradient to slope in degrees
    slope = np.degrees(
        np.arctan(
            np.sqrt(
                dz_dx ** 2 +
                dz_dy ** 2
            )
        )
    )

    slope[~valid] = NODATA

    profile = src.profile.copy()

    profile.update(
        dtype="float32",
        nodata=NODATA,
        count=1,
        compress="deflate"
    )

    with rasterio.open(OUTPUT_SLOPE, "w", **profile) as dst:
        dst.write(slope.astype("float32"), 1)


print(f"[SAVED] {OUTPUT_SLOPE}")


# ============================================================
# 5. VALIDATE DEM
# ============================================================

print("\n[VALIDATE] DEM")

with rasterio.open(OUTPUT_DEM) as src:

    data = src.read(1).astype("float32")

    valid_data = data[
        np.isfinite(data)
        & (data != NODATA)
    ]

    print(f"  CRS:        {src.crs}")
    print(
        f"  Resolution: "
        f"{src.res[0]:.3f} x {src.res[1]:.3f} m"
    )
    print(f"  Width:      {src.width}")
    print(f"  Height:     {src.height}")
    print(f"  Valid:      {len(valid_data):,}")
    print(f"  Min:        {np.min(valid_data):.2f} m")
    print(f"  Max:        {np.max(valid_data):.2f} m")
    print(f"  Mean:       {np.mean(valid_data):.2f} m")
    print(f"  Median:     {np.median(valid_data):.2f} m")


# ============================================================
# 6. VALIDATE SLOPE
# ============================================================

print("\n[VALIDATE] SLOPE")

with rasterio.open(OUTPUT_SLOPE) as src:

    data = src.read(1).astype("float32")

    valid_data = data[
        np.isfinite(data)
        & (data != NODATA)
    ]

    print(f"  Min:        {np.min(valid_data):.2f}°")
    print(f"  Max:        {np.max(valid_data):.2f}°")
    print(f"  Mean:       {np.mean(valid_data):.2f}°")
    print(f"  Median:     {np.median(valid_data):.2f}°")


print("\n" + "=" * 70)
print("SRTM DEM PROCESSING COMPLETE")
print("=" * 70)

print("\nCreated:")
print(f"  {OUTPUT_DEM}")
print(f"  {OUTPUT_SLOPE}")

print("\nNext:")
print("  Build the 100m Mumbai grid.")