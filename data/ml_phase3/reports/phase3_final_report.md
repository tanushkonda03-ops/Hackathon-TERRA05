# TERRA05 Phase 3 ML Report

## 1. Objective
Train a reproducible XGBoost waterlogging-label classifier and test the added value of Phase 2B SWMM features.

## 2. Target Definition
`flood_label` and `flood_fraction` are target-only, interpreted per Phase 3 specification as July-2005 waterlogging. Source label event/date linkage still needs confirmation; metrics are label agreement, not independently established event forecasting.

## 3. Dataset
Citywide 47,758; physics-supported 1,516; 280 supported positives. See dataset_report.md.

## 4. Feature Engineering
GIS 25, event rainfall 8, nonempty SWMM 6. Inputs are whitelisted; target columns are excluded.

## 5. SWMM Physics Integration
Joined by authoritative `grid_id`; 1,516/47,758 mapped cells. Nearest node depth is named a proxy, never street depth. The model is hydraulically unvalidated.

## 6. Leakage Audit
See leakage_audit.md. Only E001 once per cell is used; no duplicated scenario rows.

## 7. Validation Strategy
Fixed three-way 2 km EPSG:32643 spatial block split, no shared blocks. Groups: {"train": ["137_1054", "138_1053", "138_1057", "139_1054", "139_1055", "139_1057", "139_1058"], "validation": ["137_1053", "138_1054", "138_1055"], "test": ["138_1056", "138_1058", "139_1056"]}.

## 8. Model Configuration
Version terra05-xgb-v1.0.0; seed 42; threshold 0.0013 selected on validation (max F1 with precision >= 0.10). Score is uncalibrated.

## 9. Experiment A — GIS
Validation: {'pr_auc': 0.3478583907176358, 'roc_auc': 0.5194487553541498, 'precision': 0.28874388254486133, 'recall': 0.9779005524861878, 'f1': 0.44584382871536526, 'balanced_accuracy': 0.4990626357936557, 'confusion_matrix_tn_fp_fn_tp': [[9, 436], [4, 177]], 'threshold': 0.004684207029640675}
Test: {'pr_auc': 0.18529166123471785, 'roc_auc': 0.5670349094122846, 'precision': 0.1477832512315271, 'recall': 0.967741935483871, 'f1': 0.2564102564102564, 'balanced_accuracy': 0.5098983650022094, 'confusion_matrix_tn_fp_fn_tp': [[19, 346], [2, 60]], 'threshold': 0.004684207029640675}

## 10. Experiment B — GIS + Rainfall
Validation: {'pr_auc': 0.33609059687294823, 'roc_auc': 0.5187783226767646, 'precision': 0.2917369308600337, 'recall': 0.9558011049723757, 'f1': 0.4470284237726098, 'balanced_accuracy': 0.5059904401266373, 'confusion_matrix_tn_fp_fn_tp': [[25, 420], [8, 173]], 'threshold': 0.01}
Test: {'pr_auc': 0.19264172175036098, 'roc_auc': 0.5807335395492709, 'precision': 0.15263157894736842, 'recall': 0.9354838709677419, 'f1': 0.26244343891402716, 'balanced_accuracy': 0.526646045072912, 'confusion_matrix_tn_fp_fn_tp': [[43, 322], [4, 58]], 'threshold': 0.01}

## 11. Experiment C — GIS + Rainfall + SWMM
Validation: {'pr_auc': 0.3467880606831918, 'roc_auc': 0.5452728288534359, 'precision': 0.29526916802610115, 'recall': 1.0, 'f1': 0.45591939546599497, 'balanced_accuracy': 0.5146067415730337, 'confusion_matrix_tn_fp_fn_tp': [[13, 432], [0, 181]], 'threshold': 0.0012947609648108482}
Test: {'pr_auc': 0.24080915163595829, 'roc_auc': 0.6204153778170571, 'precision': 0.14454976303317535, 'recall': 0.9838709677419355, 'f1': 0.25206611570247933, 'balanced_accuracy': 0.49741493592576225, 'confusion_matrix_tn_fp_fn_tp': [[4, 361], [1, 61]], 'threshold': 0.0012947609648108482}

## 12. Random Forest Baseline
Validation: {'pr_auc': 0.3266955205818367, 'roc_auc': 0.5348252529641815, 'precision': 0.296875, 'recall': 0.9447513812154696, 'f1': 0.45178335535006603, 'balanced_accuracy': 0.517319510832454, 'confusion_matrix_tn_fp_fn_tp': [[40, 405], [10, 171]], 'threshold': 0.0702141878350862}
Test: {'pr_auc': 0.24893711861330386, 'roc_auc': 0.6489173663278834, 'precision': 0.17058823529411765, 'recall': 0.9354838709677419, 'f1': 0.2885572139303483, 'balanced_accuracy': 0.5814405656208572, 'confusion_matrix_tn_fp_fn_tp': [[83, 282], [4, 58]], 'threshold': 0.0702141878350862}

## 13. Model Comparison
See experiment_comparison.csv; all supported-domain models use identical spatial partitions. Citywide GIS-only held-out test PR-AUC is 0.163 and ROC-AUC 0.784; its validation threshold produced zero test detections, so citywide outputs are risk scores only and have no binary predicted label.

## 14. Feature Importance
Gain and validation permutation importance are in feature_importance.csv. Top validation permutation features: distance_to_water (GIS), swmm_peak_conduit_velocity_m_s (SWMM), swmm_peak_conduit_flow_m3s (SWMM), swmm_nearest_node_depth_proxy_m (SWMM), distance_to_drain (GIS). Importance is associational, not causal.

## 15. Physics Contribution
PR-AUC delta (GIS+rainfall+SWMM minus GIS+rainfall): +0.0482 absolute (+25.0% relative). Random Forest test PR-AUC is 0.2489, slightly above the XGBoost physics model. At the validation-selected XGBoost threshold, test precision is 0.145 and recall 0.984, with 361 false positives; this threshold favors detection and is not a low-false-alarm operating point.

## 16. Prediction Examples
See test_predictions.csv and citywide_predictions.csv. Scores are ranking scores, not calibrated probabilities. Citywide full-fit rows are training-domain scores; generalization is estimated from the separate spatial folds, not those in-sample rows.

## 17. Limitations
Historical label provenance and July 2005 event match remain unverified; rainfall 15-minute profile reconstructed; SWMM is uncalibrated/ hydraulically unvalidated; nearest node depth is a proxy; citywide GIS model extrapolation is not physics-supported; no causal or real-time forecast claim.

## 18. Reproducibility
Run `python scripts/train_xgboost_phase3.py`; fixed seed 42 and saved dataset/schema hashes in manifests.

## 19. Final Verdict
PHASE_3_COMPLETE_WITH_LIMITATIONS; models, spatial comparison, serialized artifacts, predictions, leakage audit and API are present, with source-label and hydraulic validation limitations stated.
