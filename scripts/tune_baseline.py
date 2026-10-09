from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.metrics import (
    average_precision_score, roc_auc_score,
    precision_score, recall_score, f1_score,
    balanced_accuracy_score, confusion_matrix,
)

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_csv(ROOT / "data/ml_ready/ml_master_spatial_features.csv")
OUT = ROOT / "outputs"
(OUT / "models").mkdir(parents=True, exist_ok=True)
(OUT / "reports").mkdir(parents=True, exist_ok=True)

target = "flood_label"
fold = "spatial_cv_fold"
excluded = {
    "grid_id", "ward", target, "flood_fraction", fold
}
features = [c for c in df.columns if c not in excluded]

# Use only numeric features in this experiment.
# soil_class is excluded here; categorical handling can be added separately.
X = df[features].select_dtypes(include="number")
if X.shape[1] == 0:
    raise ValueError("No numeric predictors available.")

y = df[target].astype(int)
folds = df[fold].astype(int)

# Fold 2 remains the final geographic test set.
# Fold 4 is used only to select the threshold.
train_mask = ~folds.isin([2, 4])
val_mask = folds == 4
test_mask = folds == 2

def new_model():
    return make_pipeline(
        SimpleImputer(strategy="median", keep_empty_features=True),
        RandomForestClassifier(
            n_estimators=400,
            min_samples_leaf=2,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=1,
        ),
    )

X_train, y_train = X.loc[train_mask], y.loc[train_mask]
X_val, y_val = X.loc[val_mask], y.loc[val_mask]
X_final, y_final = X.loc[~test_mask], y.loc[~test_mask]
X_test, y_test = X.loc[test_mask], y.loc[test_mask]

if y_val.nunique() < 2 or y_test.nunique() < 2:
    raise ValueError("Validation and test folds must each contain both classes.")

print("Training threshold-selection model...")
selector = new_model()
selector.fit(X_train, y_train)
val_prob = selector.predict_proba(X_val)[:, 1]

# Select threshold maximizing F1 on fold 4 only.
thresholds = np.arange(0.01, 0.501, 0.005)
scores = [
    f1_score(y_val, (val_prob >= t).astype(int), zero_division=0)
    for t in thresholds
]
best_idx = int(np.argmax(scores))
threshold = float(thresholds[best_idx])

print(f"Threshold selected on fold 4: {threshold:.3f}")
print(f"Validation F1: {scores[best_idx]:.4f}")

# Refit using all data except the untouched fold-2 test region.
print("Refitting final model on all non-test folds...")
final_model = new_model()
final_model.fit(X_final, y_final)
test_prob = final_model.predict_proba(X_test)[:, 1]
test_pred = (test_prob >= threshold).astype(int)

metrics = {
    "model": "RandomForestClassifier",
    "numeric_features": X.columns.tolist(),
    "excluded_columns": sorted(excluded),
    "threshold_selection_fold": 4,
    "test_fold": 2,
    "selected_threshold": threshold,
    "validation_f1": float(scores[best_idx]),
    "test_roc_auc": float(roc_auc_score(y_test, test_prob)),
    "test_average_precision": float(average_precision_score(y_test, test_prob)),
    "test_precision": float(precision_score(y_test, test_pred, zero_division=0)),
    "test_recall": float(recall_score(y_test, test_pred, zero_division=0)),
    "test_f1": float(f1_score(y_test, test_pred, zero_division=0)),
    "test_balanced_accuracy": float(balanced_accuracy_score(y_test, test_pred)),
    "test_confusion_matrix": confusion_matrix(
        y_test, test_pred, labels=[0, 1]
    ).tolist(),
    "warning": "Provisional susceptibility model; label provenance still needs verification."
}

joblib.dump(final_model, OUT / "models/ward_flood_susceptibility_rf_tuned.joblib")
(OUT / "reports/ward_flood_susceptibility_tuned_metrics.json").write_text(
    json.dumps(metrics, indent=2), encoding="utf-8"
)
pd.DataFrame({
    "grid_id": df.loc[test_mask, "grid_id"].values,
    "ward": df.loc[test_mask, "ward"].values,
    "actual_label": y_test.values,
    "predicted_probability": test_prob,
    "predicted_label": test_pred,
}).to_csv(OUT / "reports/ward_flood_susceptibility_tuned_holdout.csv", index=False)

print("\n=== FINAL FOLD-2 RESULTS ===")
for key in [
    "test_roc_auc", "test_average_precision", "test_precision",
    "test_recall", "test_f1", "test_balanced_accuracy"
]:
    print(f"{key}: {metrics[key]:.4f}")
print("Confusion matrix (actual rows, predicted columns; labels 0,1):")
print(metrics["test_confusion_matrix"])
print("\nSaved tuned model and reports in outputs/.")
