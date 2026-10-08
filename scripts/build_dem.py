from pathlib import Path
import zipfile
import shutil

import rasterio
from rasterio.merge import merge
from rasterio.mask import mask
import geopandas as gpd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

EXTERNAL = PROJECT_ROOT / "data" / "raw" / "external"
BMC = PROJECT_ROOT / "data" / "raw" / "bmc"

OUTPUT = EXTERNAL / "dem_mumbai.tif"

WARD_FILE = BMC / "wards.geojson"


# ============================================================
# SRTM FILES
# ============================================================

TILES = [
    "N18E072",
    "N18E073",
    "N19E072",
    "N19E073",
]


# ============================================================
# 1. EXTRACT HGT FILES
# ============================================================

def extract_hgt(tile):

    zip_path = EXTERNAL / f"{tile}.hgt.zip"
    hgt_path = EXTERNAL / f"{tile}.hgt"

    if hgt_path.exists():
        print(f"[SKIP] {hgt_path.name}")
        return hgt_path

    if not zip_path.exists():
        raise FileNotFoundError(
            f"Missing SRTM tile: {zip_path}"
        )

    print(f"[EXTRACT] {zip_path.name}")

    with zipfile.ZipFile(zip_path, "r") as z:
        members = z.namelist()

        # Find the HGT file inside the ZIP
        hgt_member = next(
            (
                m for m in members
                if m.lower().endswith(".hgt")
            ),
            None
        )

        if hgt_member is None:
            raise RuntimeError(
                f"No .hgt file found inside {zip_path}"
            )

        with z.open(hgt_member) as src, open(hgt_path, "wb") as dst:
            shutil.copyfileobj(src, dst)

    print(f"[SAVED] {hgt_path}")

    return hgt_path


# ============================================================
# 2. OPEN SRTM TILES
# ============================================================

datasets = []

for tile in TILES:

    hgt = extract_hgt(tile)

    print(f"[OPEN] {hgt.name}")

    src = rasterio.open(hgt)

    datasets.append(src)

    print(
        f"       bounds={src.bounds}"
    )

    print(
        f"       resolution={src.res}"
    )

    print(
        f"       CRS={src.crs}"
    )


# ============================================================
# 3. MOSAIC
# ============================================================

print()
print("[MOSAIC] Combining SRTM tiles...")

mosaic, transform = merge(datasets)

source = datasets[0]

profile = source.profile.copy()

profile.update(
    driver="GTiff",
    height=mosaic.shape[1],
    width=mosaic.shape[2],
    transform=transform,
    crs=source.crs,
    count=1,
    dtype=mosaic.dtype,
    compress="deflate",
    predictor=2,
    tiled=False,
    BIGTIFF="IF_SAFER",
)

mosaic_path = EXTERNAL / "srtm_mosaic.tif"

with rasterio.open(mosaic_path, "w", **profile) as dst:
    dst.write(mosaic[0], 1)

print(f"[SAVED] {mosaic_path}")


# ============================================================
# 4. LOAD MUMBAI BOUNDARY
# ============================================================

print()
print("[BOUNDARY] Loading BMC wards...")

wards = gpd.read_file(WARD_FILE)

if wards.empty:
    raise RuntimeError(
        "BMC wards file is empty."
    )

print(
    f"[BOUNDARY] {len(wards)} wards loaded"
)


# ============================================================
# 5. DISSOLVE WARDS INTO ONE MUMBAI STUDY AREA
# ============================================================

print("[BOUNDARY] Creating Mumbai boundary...")

mumbai = wards.dissolve()

# Match DEM CRS
mumbai = mumbai.to_crs(profile["crs"])

geometries = mumbai.geometry.values


# ============================================================
# 6. CLIP DEM TO MUMBAI
# ============================================================

print()
print("[CLIP] Clipping DEM to Mumbai...")

with rasterio.open(mosaic_path) as src:

    clipped, clipped_transform = mask(
        src,
        geometries,
        crop=True,
        nodata=-9999
    )

    clipped_profile = src.profile.copy()

    clipped_profile.update(
        height=clipped.shape[1],
        width=clipped.shape[2],
        transform=clipped_transform,
        nodata=-9999,
        compress="deflate",
        predictor=2,
        tiled=False,
        BIGTIFF="IF_SAFER",
    )

    with rasterio.open(
        OUTPUT,
        "w",
        **clipped_profile
    ) as dst:

        dst.write(clipped)


# ============================================================
# 7. VALIDATE
# ============================================================

print()
print("=" * 70)
print("DEM CREATED")
print("=" * 70)

print(f"Output: {OUTPUT}")

with rasterio.open(OUTPUT) as src:

    data = src.read(1)

    valid = data[data != src.nodata]

    print()
    print(f"CRS:       {src.crs}")
    print(f"Width:     {src.width}")
    print(f"Height:    {src.height}")
    print(f"Resolution:{src.res}")
    print(f"Bounds:    {src.bounds}")

    if len(valid) > 0:

        print(
            f"Min elevation: {valid.min():.2f} m"
        )

        print(
            f"Max elevation: {valid.max():.2f} m"
        )

        print(
            f"Mean elevation: {valid.mean():.2f} m"
        )

    else:

        raise RuntimeError(
            "DEM contains no valid elevation pixels!"
        )


# ============================================================
# 8. CLOSE DATASETS
# ============================================================

for src in datasets:
    src.close()


print()
print("[DONE]")
print()
print(
    "Next file should be:"
)
print(
    "data/raw/external/dem_mumbai.tif"
)