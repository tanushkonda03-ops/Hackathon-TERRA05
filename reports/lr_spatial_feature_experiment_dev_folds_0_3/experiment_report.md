# Logistic Regression Spatial Feature Experiment

Target: historical mapped-flood susceptibility from static 100 m grid labels, not future-event forecasting. Unlabelled cells are not confirmed non-flood observations. Fold-4 assignments are skipped when filtering the saved split; no fold-4 labels, metrics, predictions, or outcomes are used or opened by this experiment.

## Leakage Controls

- Reused saved development folds 0–3 and their existing 500 m exclusion flags unchanged (assignment SHA-256 `b922175914c876cb1078b0a62072273d7bafa1ae2dccda29f1411264e274e039`).
- Every outer fold uses identical eligible train/validation rows across feature variants. Each outer-fold threshold is chosen by nested inner OOF F2 using only that outer fold's training rows.
- Imputation, scaling, and categorical encoding are fit in each inner/outer training pipeline. Added transforms are deterministic row-wise log1p or product terms, with no full-dataset fit.
- Ward, IDs, fold fields, flood fractions/labels, event/rainfall/tide/scenario values, label-location proxies, and SWMM outputs are prohibited or absent.

## Baseline Error Analysis

Fold 0 has the lowest saved Logistic Regression PR-AUC; fold 1's low precision is dominated by false positives; fold 3 has the largest false-negative count and lower recall. The baseline proxy ablation below shows whether adding the available static drainage/hydrology group helps within each fold.

| Fold | PR-AUC | ROC-AUC | Precision@0.5 | Recall@0.5 | FP | FN | Δ PR-AUC adding static proxies |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0.0872 | 0.7388 | 0.0879 | 0.7293 | 1007 | 36 | -0.0159 |
| 1 | 0.1073 | 0.7498 | 0.0559 | 0.9892 | 3089 | 2 | +0.0046 |
| 2 | 0.1303 | 0.7620 | 0.1005 | 0.8696 | 3222 | 54 | +0.0120 |
| 3 | 0.1646 | 0.8636 | 0.1105 | 0.6044 | 1771 | 144 | -0.0303 |

## Feature Variants

All comparisons use Logistic Regression C=0.1, class_weight=balanced, and the same four outer folds. The log1p and interaction terms are calculated per row from existing source fields; no target information is used.

| Variant | Features | Train PR-AUC | Outer PR-AUC ± SD | ROC-AUC | Precision@0.5 | Recall@0.5 | Train-validation PR gap | Nested threshold precision | Nested threshold recall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| geographic_baseline | 13 | 0.1439 | 0.1224 ± 0.0333 | 0.7786 | 0.0887 | 0.7981 | 0.0215 | 0.0847 | 0.6570 |
| geographic_hydrology_log1p_interactions | 36 | 0.1882 | 0.1187 ± 0.0456 | 0.7493 | 0.0813 | 0.6606 | 0.0695 | 0.0590 | 0.7707 |
| geographic_hydrology_log1p | 33 | 0.1882 | 0.1179 ± 0.0453 | 0.7489 | 0.0819 | 0.6661 | 0.0703 | 0.0582 | 0.7708 |
| geographic_plus_hydrology | 26 | 0.1589 | 0.1150 ± 0.0319 | 0.7761 | 0.0856 | 0.8168 | 0.0439 | 0.0607 | 0.7565 |

### Per outer fold

| Variant | Fold | Train PR-AUC | Validation PR-AUC | ROC-AUC | Train-validation gap | Precision / recall @0.5 | Nested threshold | Precision / recall at nested threshold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geographic_baseline | 0 | 0.1507 | 0.0872 | 0.7388 | 0.0636 | 0.0879 / 0.7293 | 0.6788 | 0.0809 / 0.0827 |
| geographic_baseline | 1 | 0.1461 | 0.1073 | 0.7498 | 0.0388 | 0.0559 / 0.9892 | 0.6216 | 0.0701 / 0.9189 |
| geographic_baseline | 2 | 0.1478 | 0.1303 | 0.7620 | 0.0174 | 0.1005 / 0.8696 | 0.2624 | 0.0776 / 0.9203 |
| geographic_baseline | 3 | 0.1309 | 0.1646 | 0.8636 | -0.0337 | 0.1105 / 0.6044 | 0.4122 | 0.1102 / 0.7060 |
| geographic_hydrology_log1p | 0 | 0.2109 | 0.0600 | 0.6766 | 0.1509 | 0.0301 / 0.1429 | 0.5257 | 0.0331 / 0.1278 |
| geographic_hydrology_log1p | 1 | 0.2220 | 0.1040 | 0.6477 | 0.1180 | 0.0576 / 0.9459 | 0.3966 | 0.0555 / 0.9676 |
| geographic_hydrology_log1p | 2 | 0.1469 | 0.1580 | 0.8011 | -0.0111 | 0.1166 / 0.8889 | 0.0279 | 0.0751 / 0.9879 |
| geographic_hydrology_log1p | 3 | 0.1729 | 0.1496 | 0.8703 | 0.0234 | 0.1232 / 0.6868 | 0.0130 | 0.0689 / 1.0000 |
| geographic_hydrology_log1p_interactions | 0 | 0.2097 | 0.0604 | 0.6770 | 0.1492 | 0.0316 / 0.1504 | 0.5208 | 0.0332 / 0.1353 |
| geographic_hydrology_log1p_interactions | 1 | 0.2217 | 0.1044 | 0.6495 | 0.1173 | 0.0573 / 0.9405 | 0.4204 | 0.0558 / 0.9622 |
| geographic_hydrology_log1p_interactions | 2 | 0.1463 | 0.1573 | 0.8008 | -0.0111 | 0.1152 / 0.8841 | 0.0306 | 0.0758 / 0.9879 |
| geographic_hydrology_log1p_interactions | 3 | 0.1749 | 0.1524 | 0.8701 | 0.0225 | 0.1211 / 0.6676 | 0.0174 | 0.0712 / 0.9973 |
| geographic_plus_hydrology | 0 | 0.1697 | 0.0713 | 0.7046 | 0.0984 | 0.0662 / 0.7970 | 0.6867 | 0.0442 / 0.0602 |
| geographic_plus_hydrology | 1 | 0.1714 | 0.1119 | 0.7526 | 0.0595 | 0.0541 / 1.0000 | 0.5893 | 0.0576 / 0.9784 |
| geographic_plus_hydrology | 2 | 0.1463 | 0.1424 | 0.7846 | 0.0039 | 0.1108 / 0.8768 | 0.0142 | 0.0710 / 0.9903 |
| geographic_plus_hydrology | 3 | 0.1481 | 0.1343 | 0.8624 | 0.0138 | 0.1112 / 0.5934 | 0.0189 | 0.0702 / 0.9973 |

Per-fold values and confusion matrices at 0.5 and nested thresholds are in `feature_variant_fold_metrics.csv`; fold-specific thresholds are recorded there and in OOF predictions.

## Threshold and Limitations

Thresholds are selected separately for each outer fold by F2 on inner OOF predictions from that outer fold's eligible training data, then applied once to that outer validation fold. Thus threshold-selection rows do not score their own calibration predictions. Fold-to-fold threshold variability remains a limitation.

No mapped spatial SWMM result features exist in this ML dataset. These variants test existing drainage/hydrology proxies and derived row-wise terms, not the value of SWMM outputs. These are susceptibility rankings, not calibrated probabilities, validated forecasts, or evidence of generalization to unseen storms.

Fold 4 was not read or used here, but its earlier inspection means it is not an untouched final test. A future independent evaluation requires a new untouched spatial holdout or suitable nested spatial evaluation.

### Next step

Keep the 13-feature geographic Logistic Regression baseline; none of the tested additions improved mean outer-fold PR-AUC. The next concrete action is to review the mapped-label coverage and the saved fold-0/fold-3 false-positive/false-negative locations, then designate a new untouched spatial holdout before another model comparison. Do not reuse the previously inspected fold 4 as a final test.

Reproduce with `.venv/Scripts/python.exe scripts/experiment_lr_spatial_features.py`.
