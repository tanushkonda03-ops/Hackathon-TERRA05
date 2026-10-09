# Development-Only Static Flood Model Improvement

This experiment uses only existing historical mapped-flood susceptibility labels (`flood_label`) on static 100 m cells. It is not future-event forecasting, calibration, or validation. The previous evaluation's inspected fold 4 was not read, trained on, compared, or used for threshold selection here.

## Leakage and Split Controls

- Used only saved assignment folds 0–3 and their existing 500 m exclusion flags. The assignment CSV was read-only and its SHA-256 is saved in `dataset_version.json`.
- The dataset loader retained only development-fold rows. Flood fraction, labels/duplicates, ward, IDs/split fields, event/rainfall/tide/scenario fields, and known-flood-location proxies are prohibited and runtime-checked against feature lists.
- Geographic feature count: 13; geographic + available drainage/hydrology proxy feature count: 26. The latter tests static proxies only; mapped spatial SWMM output features are absent and their value is not tested.
- Median imputation, scaling, categorical imputation, and encoding were fit inside each training fold.
- OOF predictions cover development validation folds 0–3. No evaluation was performed on fold 4.

## Experiment

Models: Logistic Regression with `C` in [0.1, 1.0, 10.0] (including the existing `C=1` baseline), the prior shallow regularized tree, a class-weighted Random Forest, and class-weighted Extra Trees. Ensemble limits: {'n_estimators': 200, 'max_depth': 12, 'min_samples_leaf': 20, 'max_features': 'sqrt'}. The prevalence baseline is included. Seed: `20261009`; scikit-learn `1.9.1`.

Model selection used the one-standard-error rule on development macro PR-AUC: first find the highest mean; consider candidates within one standard error; then choose the smallest feature set, lowest predeclared model-complexity rank, lowest fold PR-AUC SD, and finally higher mean PR-AUC. Selected: **logistic_regression_C_0.1** with **static_geographic**; macro PR-AUC 0.1224, fold SD 0.0333. No fold-4 data informed this choice.

### Mean development metrics (threshold 0.5; PR-AUC/ROC-AUC/precision/recall)

| Model/config | Feature set | Train PR-AUC | Validation PR-AUC ± SD | ROC-AUC | Precision | Recall | Summed TN / FP / FN / TP | PR train-validation gap |
|---|---|---:|---:|---:|---:|---:|---|---:|
| prevalence_baseline | static_geographic | 0.0436 | 0.0446 ± 0.0105 | 0.5000 | 0.0000 | 0.0000 | 24268/0/1096/0 | -0.0010 |
| prevalence_baseline | static_geographic_plus_physics_proxies | 0.0436 | 0.0446 ± 0.0105 | 0.5000 | 0.0000 | 0.0000 | 24268/0/1096/0 | -0.0010 |
| logistic_regression_C_0.1 | static_geographic | 0.1439 | 0.1224 ± 0.0333 | 0.7786 | 0.0887 | 0.7981 | 15179/9089/236/860 | 0.0215 |
| logistic_regression_C_0.1 | static_geographic_plus_physics_proxies | 0.1589 | 0.1150 ± 0.0319 | 0.7761 | 0.0856 | 0.8168 | 14900/9368/226/870 | 0.0439 |
| logistic_regression_C_1 | static_geographic | 0.1437 | 0.1225 ± 0.0336 | 0.7777 | 0.0882 | 0.7975 | 15121/9147/235/861 | 0.0212 |
| logistic_regression_C_1 | static_geographic_plus_physics_proxies | 0.1589 | 0.1139 ± 0.0322 | 0.7725 | 0.0864 | 0.8265 | 14873/9395/219/877 | 0.0450 |
| logistic_regression_C_10 | static_geographic | 0.1437 | 0.1226 ± 0.0337 | 0.7775 | 0.0881 | 0.7975 | 15112/9156/235/861 | 0.0211 |
| logistic_regression_C_10 | static_geographic_plus_physics_proxies | 0.1591 | 0.1141 ± 0.0327 | 0.7722 | 0.0869 | 0.8264 | 14902/9366/218/878 | 0.0450 |
| shallow_regularized_tree | static_geographic | 0.1039 | 0.0727 ± 0.0347 | 0.6107 | 0.0824 | 0.6036 | 16882/7386/377/719 | 0.0312 |
| shallow_regularized_tree | static_geographic_plus_physics_proxies | 0.0977 | 0.0794 ± 0.0387 | 0.6552 | 0.0740 | 0.6599 | 15320/8948/294/802 | 0.0183 |
| random_forest_conservative | static_geographic | 0.5111 | 0.1029 ± 0.0481 | 0.7024 | 0.0959 | 0.4615 | 19599/4669/517/579 | 0.4082 |
| random_forest_conservative | static_geographic_plus_physics_proxies | 0.5618 | 0.1069 ± 0.0538 | 0.7221 | 0.0968 | 0.4746 | 19537/4731/517/579 | 0.4549 |
| extra_trees_conservative | static_geographic | 0.2892 | 0.1203 ± 0.0517 | 0.7490 | 0.0819 | 0.6338 | 16842/7426/337/759 | 0.1689 |
| extra_trees_conservative | static_geographic_plus_physics_proxies | 0.3256 | 0.1255 ± 0.0599 | 0.7547 | 0.0813 | 0.6338 | 16612/7656/339/757 | 0.2001 |

Prevalence baseline macro PR-AUC is 0.0446, equal to the mean fold prevalence. Per-fold metrics and training-versus-validation results are in `fold_metrics.csv`; individual confusion matrices are represented by TN/FP/FN/TP for each fold.

## OOF Threshold

For the selected configuration, an operating threshold was chosen from pooled OOF predictions by maximizing **F2** (`beta=2`, weighting recall more than precision); ties prefer higher precision, then higher threshold. Threshold: **0.668359**. OOF precision 0.1165, recall 0.5648, F2 0.3191; confusion TN/FP/FN/TP 19572/4696/477/619.

These threshold metrics use the same OOF labels used to choose the threshold and are therefore an operating-point estimate, not an unbiased performance estimate. Full PR curve is saved in `selected_precision_recall_curve.csv`. No accuracy-only objective was used.

## Interpretation and Limits

There is a moderate train-validation PR-AUC gap; fold variation and rare labels remain important uncertainty sources.

The tree ensembles show substantially larger training than validation PR-AUC gaps (0.169 to 0.455), consistent with overfitting despite the conservative limits. The depth-3 tree has low training and validation PR-AUC relative to the selected Logistic Regression, consistent with limited fit/possible underfitting. 

Unlabelled cells are not confirmed negatives. The label reflects mapped historical flood polygons only; performance is sensitive to incomplete location reporting and fold geography. Static drainage/hydrology proxies are not spatially mapped SWMM output and this experiment does not measure SWMM feature value. Probabilities are not calibrated. No model is claimed to forecast future events or generalize to unseen storms.

The earlier fold-4 result has already been inspected outside this experiment. Do not treat it as an untouched final test. Any future independent final evaluation requires a new untouched spatial holdout or suitable nested spatial evaluation.

Reproduce with `python .venv/Scripts/python.exe scripts/tune_static_flood_models.py`. Artifacts: `fold_metrics.csv`, `development_oof_predictions.csv.gz`, `selected_precision_recall_curve.csv`, `selected_configuration.json`, `feature_lists.json`, and `dataset_version.json`.
