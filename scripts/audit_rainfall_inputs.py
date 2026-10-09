from pathlib import Path
import pandas as pd

root = Path("data")

files = [
    "processed/rainfall_observations_v1.csv",
    "processed/rainfall_features_v1.csv",
    "processed/mumbai_flood_events_v1.csv",
    "swmm_ready/swmm_rainfall_catalog.csv",
]

for rel in files:
    path = root / rel
    df = pd.read_csv(path)

    print("\n" + "=" * 70)
    print(rel)
    print("Shape:", df.shape)
    print("Dtypes:")
    print(df.dtypes.to_string())
    print("Missing values:")
    print(df.isna().sum().to_string())

    for col in df.columns:
        if any(k in col.lower() for k in
               ["rainfall", "timestamp", "datetime", "date", "time"]):
            if pd.api.types.is_numeric_dtype(df[col]):
                print(
                    f"{col}: min={df[col].min()}, "
                    f"max={df[col].max()}, "
                    f"negative={(df[col] < 0).sum()}"
                )

    if "event_id" in df.columns:
        print("Rows per event:")
        print(df.groupby("event_id").size().to_string())

    if "timeseries_id" in df.columns:
        print("Rows per time series:")
        print(df.groupby("timeseries_id").size().to_string())
        print("Rainfall totals by series (mm):")
        print(df.groupby("timeseries_id")["rainfall_15min_mm"].sum().to_string())
