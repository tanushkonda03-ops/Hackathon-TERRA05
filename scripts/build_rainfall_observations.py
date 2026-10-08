from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "rainfall_observations_v1.csv"


# ============================================================
# E001 — Mumbai extreme rainfall event
# 26–27 July 2005
#
# Source:
# IMD MAUSAM Diamond Jubilee Volume, Table 7
#
# The published values are accumulated rainfall at 3-hour
# timestamps. We derive interval rainfall by differencing
# consecutive accumulated observations.
# ============================================================

e001_cumulative = [
    ("2005-07-26", "03:00", 0.09),
    ("2005-07-26", "06:00", 0.09),
    ("2005-07-26", "09:00", 1.84),
    ("2005-07-26", "12:00", 45.01),
    ("2005-07-26", "15:00", 66.77),
    ("2005-07-26", "18:00", 76.89),
    ("2005-07-26", "21:00", 88.50),
    ("2005-07-27", "00:00", 89.60),
    ("2005-07-27", "03:00", 94.42),
]


rows = []

previous_cumulative_mm = 0.0

for date, time, cumulative_cm in e001_cumulative:

    cumulative_mm = cumulative_cm * 10.0

    interval_mm = cumulative_mm - previous_cumulative_mm

    rows.append({
        "event_id": "E001",
        "station": "Santacruz",
        "observation_date": date,
        "observation_time_utc": time,
        "rainfall_mm": round(interval_mm, 2),
        "cumulative_rainfall_mm": round(cumulative_mm, 2),
        "accumulation_period_hours": 3,
        "observation_type": "3h_interval_derived_from_IMD_cumulative",
        "source": "IMD MAUSAM Diamond Jubilee Volume, Table 7",
        "source_quality": "verified",
    })

    previous_cumulative_mm = cumulative_mm


# ============================================================
# E002
# ============================================================

rows.extend([
    {
        "event_id": "E002",
        "station": "Santacruz",
        "observation_date": "2020-07-15",
        "observation_time_utc": None,
        "rainfall_mm": 106.0,
        "cumulative_rainfall_mm": None,
        "accumulation_period_hours": 24,
        "observation_type": "24h_accumulated",
        "source": "IMD Special Bulletin - 15 July 2020",
        "source_quality": "verified",
    },
    {
        "event_id": "E002",
        "station": "Santacruz",
        "observation_date": "2020-07-15",
        "observation_time_utc": None,
        "rainfall_mm": 63.0,
        "cumulative_rainfall_mm": None,
        "accumulation_period_hours": 3,
        "observation_type": "3h_accumulated",
        "source": "IMD Special Bulletin - 15 July 2020",
        "source_quality": "verified",
    },
])


df = pd.DataFrame(rows)

OUT.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT, index=False)

print("=" * 70)
print(" MUMBAI RAINFALL OBSERVATIONS v1")
print("=" * 70)

print(f"Rows   : {len(df)}")
print(f"Events : {df.event_id.nunique()}")
print(f"Output : {OUT}")

print("\nE001 DERIVED 3-HOUR RAINFALL:")
print(
    df[df["event_id"] == "E001"][
        [
            "observation_date",
            "observation_time_utc",
            "rainfall_mm",
            "cumulative_rainfall_mm",
        ]
    ].to_string(index=False)
)

print("\nE001 TOTAL:")
print(
    df[df["event_id"] == "E001"]["rainfall_mm"].sum(),
    "mm"
)