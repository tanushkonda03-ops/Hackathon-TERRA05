import pandas as pd

path = "data/ml_ready/ml_pilot_ward_L.csv"
df = pd.read_csv(path)

print("\n=== DATASET ===")
print("Shape:", df.shape)
print("Duplicate grid IDs:", df["grid_id"].duplicated().sum())
print("\n=== TARGET DISTRIBUTION ===")
print(df["flood_label"].value_counts(dropna=False))
print("\nTarget rate:", df["flood_label"].mean())
print("\n=== FLOOD FRACTION BY LABEL ===")
print(df.groupby("flood_label")["flood_fraction"].describe())
print("\n=== SPATIAL FOLD DISTRIBUTION ===")
print(pd.crosstab(df["spatial_cv_fold"], df["flood_label"], margins=True))
print("\n=== MISSING VALUES ===")
print(df.isna().sum().sort_values(ascending=False).head(15))
print("\n=== NUMERIC CORRELATION WITH TARGET ===")
print(
    df.select_dtypes(include="number")
      .corr()["flood_label"]
      .sort_values(ascending=False)
      .to_string()
)
print("\n=== LABEL-GENERATION CODE REFERENCES ===")
