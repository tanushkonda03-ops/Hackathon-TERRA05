import pandas as pd

p = "data/ml_ready/ml_master_spatial_features.csv"
df = pd.read_csv(p)

print("Shape:", df.shape)
print("\nWard counts:")
print(df["ward"].value_counts().to_string())
print("\nFold counts:")
print(df.groupby("spatial_cv_fold").agg(
    cells=("grid_id", "size"),
    positives=("flood_label", "sum"),
    wards=("ward", "nunique")
).to_string())
print("\nTarget distribution:")
print(df["flood_label"].value_counts(dropna=False).to_string())
