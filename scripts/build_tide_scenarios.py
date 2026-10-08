from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

OUT = ROOT / "data" / "processed" / "tide_scenarios_v1.csv"

scenarios = [
    {
        "tide_scenario": "LOW",
        "tide_factor": 0.25,
        "description": "Low coastal water level; relatively favorable drainage outfall",
    },
    {
        "tide_scenario": "NORMAL",
        "tide_factor": 0.50,
        "description": "Normal coastal water level",
    },
    {
        "tide_scenario": "HIGH",
        "tide_factor": 0.75,
        "description": "High coastal water level; reduced drainage outfall efficiency",
    },
    {
        "tide_scenario": "VERY_HIGH",
        "tide_factor": 1.00,
        "description": "Very high coastal water level; strongly restricted drainage outfall",
    },
]

df = pd.DataFrame(scenarios)

OUT.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT, index=False)

print("=" * 60)
print(" SYNTHETIC TIDE SCENARIOS v1")
print("=" * 60)
print(f"Rows   : {len(df)}")
print(f"Output : {OUT}")
print()
print(df.to_string(index=False))