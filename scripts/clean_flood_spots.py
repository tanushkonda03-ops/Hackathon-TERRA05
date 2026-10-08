from pathlib import Path
import geopandas as gpd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT = PROJECT_ROOT / "data" / "raw" / "flooding_spots.geojson"
OUTPUT = PROJECT_ROOT / "data" / "raw" / "flooding_spots_clean.geojson"


print("=" * 70)
print("CLEANING BMC FLOOD SPOTS")
print("=" * 70)

gdf = gpd.read_file(INPUT)

print(f"\nOriginal features: {len(gdf)}")


# ------------------------------------------------------------
# 1. Remove records marked Delete
# ------------------------------------------------------------

text_columns = [
    "NAME",
    "REMARKS",
    "LOCATION",
    "STRETCH"
]

delete_mask = gdf[text_columns].fillna("").astype(str).apply(
    lambda col: col.str.contains(
        "delete",
        case=False,
        na=False
    )
).any(axis=1)

deleted_count = delete_mask.sum()

gdf = gdf[~delete_mask].copy()

print(f"Removed Delete records: {deleted_count}")


# ------------------------------------------------------------
# 2. Remove duplicate FEATUREIDs
# ------------------------------------------------------------

before_duplicates = len(gdf)

gdf = gdf.drop_duplicates(
    subset="FEATUREID",
    keep="first"
).copy()

duplicate_count = before_duplicates - len(gdf)

print(f"Removed duplicate FEATUREIDs: {duplicate_count}")


# ------------------------------------------------------------
# 3. Fix geometry
# ------------------------------------------------------------

gdf = gdf[gdf.geometry.notna()].copy()

gdf = gdf[gdf.geometry.is_valid].copy()


# ------------------------------------------------------------
# 4. Save
# ------------------------------------------------------------

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

gdf.to_file(
    OUTPUT,
    driver="GeoJSON"
)


# ------------------------------------------------------------
# 5. Final summary
# ------------------------------------------------------------

print("\nFinal flood dataset:")
print(f"  Features: {len(gdf)}")
print(f"  Unique FEATUREID: {gdf['FEATUREID'].nunique()}")
print(f"  CRS: {gdf.crs}")

print("\nTYPE distribution:")
print(
    gdf["TYPE"]
    .value_counts(dropna=False)
    .to_string()
)

print(f"\n[SAVED] {OUTPUT}")

print("\n" + "=" * 70)
print("FLOOD DATA CLEANING COMPLETE")
print("=" * 70)
