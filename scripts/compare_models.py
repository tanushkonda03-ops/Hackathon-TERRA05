from pathlib import Path
import json
import time

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
    precision_score,
    recall_score,
    f1_score,
    balanced_accuracy_score,
    confusion_matrix,
)
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/ml_ready/ml_master_spatial_features.csv"
OUT = ROOT / "outputs/reports/model_comparison"
OUT.mkdir(parents=True, exist_ok=True)

TARGET = "flood_label"
FOLD = "spatial_cv_fold"
TEST_FOLD = 2
VAL_FOLD = 4
EXCLUDED = {
    "grid_id", "ward", TARGET, "flood_fraction", FOLD
}

df = pd.read_csv(DATA)
if df[TARGET].isna().any() or df[FOLD].isna().any():
    raise ValueError("Target/fold contains missing values.")

feature_cols = [
    c for c in df.columns
    if c not in EXCLUDED
    and pd.api.types.is_numeric_dtype(df[c])
]

X = df[feature_cols].replace([np.inf, -np.inf], np.nan)
y = df[TARGET].astype(int)
folds = df[FOLD].astype(int)

train_mask = ~folds.isin([TEST_FOLD, VAL_FOLD])
val_mask = folds == VAL_FOLD
final_train_mask = folds != TEST_FOLD
test_mask = folds == TEST_FOLD

for name, mask in [
    ("train", train_mask), ("validation", val_mask),
    ("final_train", final_train_mask), ("test", test_mask)
]:
    if mask.sum() == 0 or y[mask].nunique() != 2:
        raise ValueError(f"{name} split is empty or missing a class.")

# Fold 4 selects the threshold. Fold 2 is not used until final evaluation.
models = {
    "ExtraTrees": ExtraTreesClassifier(
        n_estimators=300,
        min_samples_leaf=2,
        class_weight="balanced",
        max_features="sqrt",
        random_state=42,
        n_jobs=-1,
    ),
    "HistGradientBoosting": HistGradientBoostingClassifier(
        max_iter=200,
        learning_rate=0.08,
        max_leaf_nodes=15,
        l2_regularization=1.0,
        class_weight="balanced",
        early_stopping=False,
        random_state=42,
    ),
}

results = []
predictions = []

print(f"scikit-learn: {sklearn.__version__}")
print(f"Dataset: {len(df):,} rows; numeric features: {len(feature_cols)}")
print(f"Train: {train_mask.sum():,}; validation fold {VAL_FOLD}: "
      f"{val_mask.sum():,}; final holdout fold {TEST_FOLD}: "
      f"{test_mask.sum():,}")
print("Excluded:", sorted(EXCLUDED))
print("Features:", feature_cols)

for name, classifier in models.items():
    print(f"\n=== {name} ===")
    started = time.time()

    selector = make_pipeline(
        SimpleImputer(strategy="median", keep_empty_features=True),
        classifier,
    )
    selector.fit(X.loc[train_mask], y.loc[train_mask])
    val_prob = selector.predict_proba(X.loc[val_mask])[:, 1]

    # Choose threshold using fold 4 only.
    thresholds = np.arange(0.02, 0.501, 0.01)
    val_scores = [
        f1_score(y.loc[val_mask], val_prob >= t, zero_division=0)
        for t in thresholds
    ]
    best_idx = int(np.argmax(val_scores))
    threshold = float(thresholds[best_idx])

    # Refit on all non-test folds, then evaluate fold 2 once.
    final_model = make_pipeline(
        SimpleImputer(strategy="median", keep_empty_features=True),
        models[name],
    )
    final_model.fit(X.loc[final_train_mask], y.loc[final_train_mask])
    test_prob = final_model.predict_proba(X.loc[test_mask])[:, 1]
    test_pred = (test_prob >= threshold).astype(int)
    y_test = y.loc[test_mask]

    metrics = {
        "model": name,
        "sklearn_version": sklearn.__version__,
        "numeric_features": feature_cols,
        "threshold": threshold,
        "threshold_selection_fold": VAL_FOLD,
        "test_fold": TEST_FOLD,
        "validation_f1": float(val_scores[best_idx]),
        "test_roc_auc": float(roc_auc_score(y_test, test_prob)),
        "test_average_precision": float(
            average_precision_score(y_test, test_prob)
        ),
        "test_precision": float(
            precision_score(y_test, test_pred, zero_division=0)
        ),
        "test_recall": float(
            recall_score(y_test, test_pred, zero_division=0)
        ),
        "test_f1": float(f1_score(y_test, test_pred, zero_division=0)),
        "test_balanced_accuracy": float(
            balanced_accuracy_score(y_test, test_pred)
        ),
        "test_confusion_matrix": confusion_matrix(
            y_test, test_pred, labels=[0, 1]
        ).tolist(),
        "fit_seconds_including_validation_and_final_fit": round(
            time.time() - started, 2
        ),
        "warning": (
            "Provisional spatial susceptibility evaluation. "
            "Labels are derived from historical flood-spot overlap, "
            "not event-specific flood observations. Threshold selection "
            "uses fold 4; final metrics use fold 2."
        ),
    }
    results.append(metrics)

    pred_frame = pd.DataFrame({
        "grid_id": df.loc[test_mask, "grid_id"].values,
        "ward": df.loc[test_mask, "ward"].values,
        "actual_label": y_test.values,
        "predicted_probability": test_prob,
        "predicted_label": test_pred,
    })
    pred_frame.to_csv(OUT / f"{name.lower()}_holdout.csv", index=False)
    (OUT / f"{name.lower()}_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )

    print(f"Validation threshold: {threshold:.2f}")
    print(f"Validation F1: {metrics['validation_f1']:.4f}")
    print(f"Test ROC-AUC: {metrics['test_roc_auc']:.4f}")
    print(f"Test Average Precision: {metrics['test_average_precision']:.4f}")
    print(f"Test Precision / Recall / F1: "
          f"{metrics['test_precision']:.4f} / "
          f"{metrics['test_recall']:.4f} / {metrics['test_f1']:.4f}")
    print(f"Test balanced accuracy: {metrics['test_balanced_accuracy']:.4f}")
    print("Confusion matrix:", metrics["test_confusion_matrix"])
    print(f"Elapsed seconds: {metrics['fit_seconds_including_validation_and_final_fit']}")

summary = pd.DataFrame(results)[[
    "model", "threshold", "test_roc_auc", "test_average_precision",
    "test_precision", "test_recall", "test_f1", "test_balanced_accuracy"
]]
summary.to_csv(OUT / "comparison_summary.csv", index=False)

print("\n=== COMPARISON SUMMARY ===")
print(summary.to_string(index=False))
print("\nReports saved to:", OUT)
print("No model artifacts were overwritten or saved by this experiment.")
