from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.metrics import precision_score, recall_score, f1_score

root = Path.cwd()
df = pd.read_csv(root / "data/ml_ready/ml_master_spatial_features.csv")

target = "flood_label"
fold = "spatial_cv_fold"
excluded = {"grid_id", "ward", target, "flood_fraction", fold}
features = [
    c for c in df.columns
    if c not in excluded and pd.api.types.is_numeric_dtype(df[c])
]

X = df[features].replace([np.inf, -np.inf], np.nan)
y = df[target].astype(int)
f = df[fold].astype(int)

train = ~f.isin([2, 4])
valid = f == 4

model = make_pipeline(
    SimpleImputer(strategy="median", keep_empty_features=True),
    HistGradientBoostingClassifier(
        max_iter=200,
        learning_rate=0.08,
        max_leaf_nodes=15,
        l2_regularization=1.0,
        class_weight="balanced",
        early_stopping=False,
        random_state=42,
    ),
)

print("Fitting on folds 0, 1 and 3; evaluating thresholds on fold 4...")
model.fit(X.loc[train], y.loc[train])
p = model.predict_proba(X.loc[valid])[:, 1]
yv = y.loc[valid]

thresholds = np.arange(0.05, 0.951, 0.025)
rows = []

for t in thresholds:
    pred = (p >= t).astype(int)
    rows.append({
        "threshold": round(float(t), 3),
        "precision": precision_score(yv, pred, zero_division=0),
        "recall": recall_score(yv, pred, zero_division=0),
        "f1": f1_score(yv, pred, zero_division=0),
        "predicted_positive_count": int(pred.sum()),
    })

result = pd.DataFrame(rows)
out = root / "outputs/reports/model_comparison/hgb_validation_threshold_sweep.csv"
result.to_csv(out, index=False)

print("\n=== TOP THRESHOLDS BY VALIDATION F1 ===")
print(result.sort_values("f1", ascending=False).head(10).to_string(index=False))
print("\n=== SELECTED THRESHOLD RANGE ===")
print(result[result["threshold"].between(0.40, 0.80)].to_string(index=False))
print("\nSaved:", out)
print("Fold 2 was not loaded for evaluation or used in threshold selection.")
