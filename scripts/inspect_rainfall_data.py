from pathlib import Path
import pandas as pd

root = Path("data")

files = [
    "processed/rainfall_observations_v1.csv",
    "processed/rainfall_features_v1.csv",
    "processed/mumbai_flood_events_v1.csv",
    "processed/tide_scenarios_v1.csv",
    "swmm_ready/swmm_rainfall_catalog.csv",
    "swmm_ready/swmm_subcatchments_citywide.csv",
]

for relative in files:
    path = root / relative
    print("\n" + "=" * 80)
    print(f"FILE: {relative}")

    if not path.exists():
        print("NOT FOUND")
        continue

    try:
        df = pd.read_csv(path)
        print("Rows:", len(df), "| Columns:", len(df.columns))
        print("Column names:", df.columns.tolist())
        print("\nSample:")
        print(df.head(4).to_string(index=False))
    except Exception as exc:
        print("Could not read CSV:", exc)
