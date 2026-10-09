import json
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "ml_ready" / "ml_master_spatial_features.csv"
OUT = ROOT / "outputs"
MODEL_DIR = OUT / "models"
REPORT_DIR = OUT / "reports"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

print("Loading citywide dataset...")
df = pd.read_csv(DATA)

target = "flood_label"
fold_col = "spatial_cv_fold"
test_fold = 2

# Exclude identifiers, the target, fold metadata, and flood_fraction.
# flood_fraction is excluded because it is strongly associated with
# the target and may have been constructed from the same flood-spot data.
excluded = {
    "grid_id",
    "ward",
    "flood_label",
    "flood_fraction",
    "spatial_cv_fold",
}

required = {target, fold_col}
if not required.issubset(df.columns):
    raise ValueError(f"Missing required columns: {required - set(df.columns)}")

if df[target].isna().any() or df[fold_col].isna().any():
    raise ValueError("Target or spatial-fold column contains missing values.")

if set(df[target].unique()) - {0, 1}:
    raise ValueError("Expected binary flood_label values 0 and 1.")

train_df = df[df[fold_col] != test_fold].copy()
test_df = df[df[fold_col] == test_fold].copy()

if train_df.empty or test_df.empty:
    raise ValueError("Train or holdout set is empty.")

if train_df[target].nunique() < 2 or test_df[target].nunique() < 2:
    raise ValueError("Train and holdout must each contain both classes.")

feature_cols = [c for c in df.columns if c not in excluded]
X_train = train_df[feature_cols]
y_train = train_df[target].astype(int)
X_test = test_df[feature_cols]
y_test = test_df[target].astype(int)

categorical = X_train.select_dtypes(
    include=["object", "category"]
).columns.tolist()
numeric = [c for c in feature_cols if c not in categorical]

preprocess = ColumnTransformer(
    transformers=[
        (
            "numeric",
            SimpleImputer(strategy="median", keep_empty_features=True),
            numeric,
        ),
        (
            "categorical",
            Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("onehot", OneHotEncoder(handle_unknown="ignore")),
            ]),
            categorical,
        ),
    ],
    remainder="drop",
)

model = Pipeline([
    ("preprocess", preprocess),
    ("classifier", RandomForestClassifier(
        n_estimators=400,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )),
])

print(f"Scikit-learn version: {sklearn.__version__}")
print(f"Training cells: {len(train_df):,}")
print(f"Holdout cells (fold {test_fold}): {len(test_df):,}")
print(f"Features: {len(feature_cols)}")
print(f"Training positives: {int(y_train.sum()):,}")
print(f"Holdout positives: {int(y_test.sum()):,}")
print("Fitting Random Forest...")

model.fit(X_train, y_train)

prob = model.predict_proba(X_test)[:, 1]
pred = (prob >= 0.5).astype(int)

metrics = {
    "model": "RandomForestClassifier",
    "purpose": "Provisional historical flood-susceptibility baseline",
    "test_fold": test_fold,
    "random_state": 42,
    "threshold": 0.5,
    "train_rows": int(len(train_df)),
    "test_rows": int(len(test_df)),
    "train_positive_count": int(y_train.sum()),
    "test_positive_count": int(y_test.sum()),
    "feature_columns": feature_cols,
    "excluded_columns": sorted(excluded),
    "roc_auc": float(roc_auc_score(y_test, prob)),
    "average_precision": float(average_precision_score(y_test, prob)),
    "balanced_accuracy": float(balanced_accuracy_score(y_test, pred)),
    "confusion_matrix_labels_0_1": confusion_matrix(
        y_test, pred, labels=[0, 1]
    ).tolist(),
    "classification_report": classification_report(
        y_test, pred, labels=[0, 1], output_dict=True, zero_division=0
    ),
    "warning": (
        "Preliminary evaluation only. Verify flood-label construction and "
        "feature provenance before interpreting these metrics as real-world "
        "predictive performance."
    ),
}

model_path = MODEL_DIR / "ward_flood_susceptibility_rf.joblib"
metrics_path = REPORT_DIR / "ward_flood_susceptibility_metrics.json"
pred_path = REPORT_DIR / "ward_flood_susceptibility_holdout.csv"

joblib.dump(model, model_path)
metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

pd.DataFrame({
    "grid_id": test_df["grid_id"].values,
    "ward": test_df["ward"].values,
    "actual_label": y_test.values,
    "predicted_probability": prob,
    "predicted_label": pred,
}).to_csv(pred_path, index=False)

print("\n=== HOLDOUT RESULTS ===")
print(f"ROC-AUC:          {metrics['roc_auc']:.4f}")
print(f"Average precision:{metrics['average_precision']:.4f}")
print(f"Balanced accuracy:{metrics['balanced_accuracy']:.4f}")
print("Confusion matrix (rows=actual, columns=predicted; labels 0,1):")
print(metrics["confusion_matrix_labels_0_1"])
print("\nClassification report:")
print(classification_report(y_test, pred, zero_division=0))
print("\nSaved model:", model_path)
print("Saved metrics:", metrics_path)
print("Saved holdout predictions:", pred_path)
print("\nIMPORTANT: This is a provisional susceptibility baseline, not a")
print("storm-specific flood forecast or yet a fully validated result.")
