from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "mumbai_flood_events_v1.csv"

events = [
    {
        "event_id": "E001",
        "event_name": "Mumbai Extreme Rainfall and Flood Event - July 2005",
        "event_start": "2005-07-26 00:00",
        "event_end": "2005-07-27 03:00",
        "primary_station": "Santacruz",
        "secondary_station": "Colaba",
        "rainfall_24h_mm": 944.2,
        "rainfall_1h_mm": None,
        "rainfall_3h_mm": None,
        "rainfall_6h_mm": None,
        "rainfall_12h_mm": None,
        "rainfall_48h_mm": None,
        "rainfall_source": "IMD MAUSAM",
        "source_quality": "verified",
        "event_role": "primary_validation",
        "notes": (
            "IMD reports 944.2 mm at Santacruz for the 24 hours "
            "ending 0300 UTC on 27 July 2005. "
            "Detailed 3-hour observation table is available in IMD publication."
        ),
    },

    {
        "event_id": "E002",
        "event_name": "Mumbai Heavy Rainfall Event - July 2020",
        "event_start": "2020-07-14 08:30",
        "event_end": "2020-07-15 11:30",
        "primary_station": "Santacruz",
        "secondary_station": "Colaba",
        "rainfall_24h_mm": 106.0,
        "rainfall_1h_mm": None,
        "rainfall_3h_mm": 63.0,
        "rainfall_6h_mm": None,
        "rainfall_12h_mm": None,
        "rainfall_48h_mm": None,
        "rainfall_source": "IMD Special Bulletin - 15 July 2020",
        "source_quality": "verified_partial",
        "event_role": "training_validation",
        "notes": (
            "Santacruz recorded 106 mm from 0830 IST 14 July "
            "to 0830 IST 15 July, followed by 63 mm from 0830 "
            "to 1130 IST on 15 July."
        ),
    },

    {
        "event_id": "E003",
        "event_name": "Mumbai Heavy Rainfall Spell - August 2020",
        "event_start": "2020-08-03 00:00",
        "event_end": "2020-08-08 00:00",
        "primary_station": "Santacruz",
        "secondary_station": "Colaba",
        "rainfall_24h_mm": None,
        "rainfall_1h_mm": None,
        "rainfall_3h_mm": None,
        "rainfall_6h_mm": None,
        "rainfall_12h_mm": None,
        "rainfall_48h_mm": None,
        "rainfall_source": "IMD",
        "source_quality": "event_verified_values_pending",
        "event_role": "training_validation",
        "notes": (
            "Major multi-day Mumbai rainfall spell. "
            "Individual station/day values will be populated "
            "from the corresponding IMD observations."
        ),
    },

    {
        "event_id": "E004",
        "event_name": "Mumbai Heavy Rainfall Spell - July 2021",
        "event_start": "2021-07-15 00:00",
        "event_end": "2021-07-21 23:59",
        "primary_station": "Santacruz",
        "secondary_station": "Colaba",
        "rainfall_24h_mm": None,
        "rainfall_1h_mm": None,
        "rainfall_3h_mm": None,
        "rainfall_6h_mm": None,
        "rainfall_12h_mm": None,
        "rainfall_48h_mm": None,
        "rainfall_source": "IMD",
        "source_quality": "event_verified_values_pending",
        "event_role": "training_validation",
        "notes": (
            "Major prolonged west-coast rainfall spell affecting Mumbai. "
            "Exact event rainfall windows will be populated from IMD records."
        ),
    },

    {
        "event_id": "E005",
        "event_name": "Mumbai Major Rainfall Event - 2019",
        "event_start": None,
        "event_end": None,
        "primary_station": "Santacruz",
        "secondary_station": "Colaba",
        "rainfall_24h_mm": None,
        "rainfall_1h_mm": None,
        "rainfall_3h_mm": None,
        "rainfall_6h_mm": None,
        "rainfall_12h_mm": None,
        "rainfall_48h_mm": None,
        "rainfall_source": "IMD",
        "source_quality": "candidate",
        "event_role": "candidate_event",
        "notes": (
            "Candidate event retained only until a specific IMD "
            "rainfall period and matching BMC flood observation are verified."
        ),
    },
]

df = pd.DataFrame(events)

OUT.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT, index=False)

print("=" * 60)
print(" MUMBAI FLOOD EVENT CATALOGUE")
print("=" * 60)
print(f"Events: {len(df)}")
print(f"Output: {OUT}")
print()
print(df[
    [
        "event_id",
        "event_name",
        "primary_station",
        "rainfall_24h_mm",
        "source_quality",
        "event_role",
    ]
].to_string(index=False))