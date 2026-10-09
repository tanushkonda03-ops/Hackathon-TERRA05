from pathlib import Path
import json
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.metrics import (
    roc_auc_score, average_precision_score,
    precision_score, recall_score, f1_score,
    balanced_accuracy_score, confusion_matrix,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/ml_ready/ml_master_spatial_features.csv"
OUT = ROOT / "outputs/reports/model_comparison"
OUT.mkdir(parents=True, exist_ok=True)

TARGET = "flood_label"
FOLD = "spatial_cv_fold"
EXCLUDED = {"grid_id", "ward", TARGET, "flood_fraction", FOLD}
SOIL_FEATURES = {
    "clay_percent", "sand_percent", "silt_percent",
    "infiltration_proxy",
}

df = pd.read_csv(DATA)
y = df[TARGET].astype(int)
folds = df[FOLD].astype(int)

all_features = [
    c for c in df.columns
    if c not in EXCLUDED and pd.api.types.is_numeric_dtype(df[c])
]
variants = {
    "with_soil": all_features,
    "without_soil": [c for c in all_features if c not in SOIL_FEATURES],
}

train = ~folds.isin([2, 4])
val = folds == 4
final_train = folds != 2
test = folds == 2

rows = []
for variant, features in variants.items():
    X = df[features].replace([np.inf, -np.inf], np.nan)
    print(f"\n=== {variant} ({len(features)} features) ===")

    selector = make_pipeline(
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
    start = time.time()
    selector.fit(X.loc[train], y.loc[train])
    val_prob = selector.predict_proba(X.loc[val])[:, 1]
    y_val = y.loc[val]

    thresholds = np.arange(0.05, 0.951, 0.025)
    val_f1 = [
        f1_score(y_val, val_prob >= t, zero_division=0)
        for t in thresholds
    ]
    threshold = float(thresholds[int(np.argmax(val_f1))])

    final_model = make_pipeline(
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
    final_model.fit(X.loc[final_train], y.loc[final_train])
    prob = final_model.predict_proba(X.loc[test])[:, 1]
    pred = (prob >= threshold).astype(int)
    yt = y.loc[test]

    metrics = {
        "variant": variant,
        "features": features,
        "threshold_selected_on_fold_4": threshold,
        "validation_f1": float(max(val_f1)),
        "test_fold": 2,
        "test_roc_auc": float(roc_auc_score(yt, prob)),
        "test_average_precision": float(average_precision_score(yt, prob)),
        "test_precision": float(precision_score(yt, pred, zero_division=0)),
        "test_recall": float(recall_score(yt, pred, zero_division=0)),
        "test_f1": float(f1_score(yt, pred, zero_division=0)),
        "test_balanced_accuracy": float(balanced_accuracy_score(yt, pred)),
        "test_confusion_matrix": confusion_matrix(yt, pred, labels=[0, 1]).tolist(),
        "seconds": round(time.time() - start, 2),
        "warning": "Historical flood-spot susceptibility labels; not event-specific flood forecasting.",
    }
    rows.append(metrics)
    (OUT / f"hgb_{variant}_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    print(json.dumps({
        k: v for k, v in metrics.items()
        if k not in {"features", "warning"}
    }, indent=2))

summary = pd.DataFrame(rows)[[
    "variant", "threshold_selected_on_fold_4", "validation_f1",
    "test_roc_auc", "test_average_precision", "test_precision",
    "test_recall", "test_f1", "test_balanced_accuracy", "seconds"
]]
summary.to_csv(OUT / "soil_ablation_summary.csv", index=False)
print("\n=== SOIL ABLATION SUMMARY ===")
print(summary.to_string(index=False))
print("\nSaved to:", OUT / "soil_ablation_summary.csv")
