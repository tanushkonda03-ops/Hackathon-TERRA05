from pathlib import Path
from datetime import timedelta
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "data" / "processed" / "rainfall_observations_v1.csv"
OUTPUT = ROOT / "data" / "processed" / "rainfall_features_v1.csv"


df = pd.read_csv(INPUT)

# ------------------------------------------------------------
# Only use observations that have a real timestamp.
# ------------------------------------------------------------

df_ts = df[
    df["observation_time_utc"].notna()
].copy()

df_ts["timestamp"] = pd.to_datetime(
    df_ts["observation_date"].astype(str)
    + " "
    + df_ts["observation_time_utc"].astype(str)
)

df_ts = df_ts.sort_values(
    ["event_id", "station", "timestamp"]
)


results = []

for (event_id, station), group in df_ts.groupby(
    ["event_id", "station"]
):

    group = group.sort_values("timestamp").reset_index(drop=True)

    rainfall = group["rainfall_mm"]

    # --------------------------------------------------------
    # These are 3-hour rainfall intervals.
    #
    # Therefore:
    #
    # 3h  = latest interval
    # 6h  = latest 2 intervals
    # 12h = latest 4 intervals
    # 24h = latest 8 intervals
    #
    # However, E001 contains 9 observations because the first
    # observation represents the initial accumulation.
    # We use the actual rainfall intervals directly.
    # --------------------------------------------------------

    rainfall_3h = rainfall.iloc[-1:].sum()
    rainfall_6h = rainfall.iloc[-2:].sum()
    rainfall_12h = rainfall.iloc[-4:].sum()

    if event_id == "E001":
        if len(group) != 9 or group.iloc[0]["timestamp"] != pd.Timestamp("2005-07-26 03:00"):
            raise ValueError("E001 expected nine 3-hour records beginning at 2005-07-26 03:00")
        rainfall_24h_intervals = group.iloc[1:]
        rainfall_24h = rainfall_24h_intervals["rainfall_mm"].sum()
        rainfall_24h_start = rainfall_24h_intervals.iloc[0]["timestamp"] - timedelta(hours=3)
        rainfall_24h_end = rainfall_24h_intervals.iloc[-1]["timestamp"]
        rainfall_27h = rainfall.sum()
        rainfall_27h_start = group.iloc[0]["timestamp"] - timedelta(hours=3)
        rainfall_27h_end = group.iloc[-1]["timestamp"]
    else:
        rainfall_24h = rainfall.sum()
        rainfall_24h_start = group.iloc[0]["timestamp"]
        rainfall_24h_end = group.iloc[-1]["timestamp"]
        rainfall_27h = None
        rainfall_27h_start = None
        rainfall_27h_end = None

    results.append({
        "event_id": event_id,
        "station": station,
        "event_end_timestamp_utc": group.iloc[-1]["timestamp"],
        "rainfall_24h_start_timestamp_utc": rainfall_24h_start,
        "rainfall_24h_end_timestamp_utc": rainfall_24h_end,

        "rainfall_3h_mm": round(float(rainfall_3h), 2),
        "rainfall_6h_mm": round(float(rainfall_6h), 2),
        "rainfall_12h_mm": round(float(rainfall_12h), 2),
        "rainfall_24h_mm": round(float(rainfall_24h), 2),
        "rainfall_27h_reconstruction_start_timestamp_utc": rainfall_27h_start,
        "rainfall_27h_reconstruction_end_timestamp_utc": rainfall_27h_end,
        "rainfall_27h_reconstruction_mm": (
            round(float(rainfall_27h), 2) if rainfall_27h is not None else None
        ),

        "source": "Derived from rainfall_observations_v1",
    })


features = pd.DataFrame(results)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
features.to_csv(OUTPUT, index=False)


print("=" * 70)
print(" MUMBAI RAINFALL FEATURES v1")
print("=" * 70)

print(f"Input : {INPUT}")
print(f"Output: {OUTPUT}")
print(f"Rows  : {len(features)}")

print("\nFEATURES:")
print(features.to_string(index=False))