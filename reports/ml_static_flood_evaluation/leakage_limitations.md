# Static Flood-Label ML Evaluation

## Dataset and Target

Dataset: `data/ml_ready/ml_master_spatial_features.csv` (47,758 cells, 31 columns; SHA-256 `d80af47d84f2f34a146d03a8772bbd3fb7ab522a3cd776aa74ac5ff0c141b8a6`). Target: `flood_label`. The source grid creates this target from historical BMC flood polygons using `flood_fraction > 0.05`; it is a static spatial occurrence/susceptibility label, not an event-specific flood forecast target. The label-building rule is in `scripts/build_flood_grid.py` under “HISTORICAL FLOOD LABEL”. Unlabelled cells are not confirmed non-flood observations.

The 2005 validation and warning-scenario tables duplicate the static label alongside event/scenario inputs. They were not used. No spatially mapped SWMM result features are present; the “physics proxy” comparison below uses only existing static flow-accumulation, drainage, soil, infiltration, wetness, capacity/stress features. It cannot establish incremental value from SWMM outputs.

## Leakage Controls

- Preassigned five regional/ward-group folds are used, with fold 4 reserved as the final spatial test before evaluation. Folds 0, 1, 2, 3 provide four development validation runs; model settings are fixed and no hyperparameter search or feature selection is performed.
- Flood grid polygons and the 332 local flood-label polygons are intersected. Cells associated with the same connected source-polygon component are assigned to one fold (180 components with positive cells); 17 positive cells were reassigned to keep groups together. 2 positive cells lacked a source-polygon association and retain their preassigned fold.
- For each held-out fold, candidate training cells within 500 m of any held-out cell centroid are excluded. Grid geometry is in urn:ogc:def:crs:EPSG::32643; fold and per-fold buffer flags are saved in `spatial_fold_assignments.csv`.
- `ward`, `grid_id`, split fields, `flood_fraction`, duplicated labels, event/rainfall/tide/scenario fields, and label-location-derived proxies are excluded. Exact feature lists and exclusion rationale are in `feature_lists.json`.
- Numeric imputation, scaling, and categorical imputation/one-hot encoding are inside each training-fold pipeline. The final spatial test is not used in fitting, preprocessing, or development comparisons.
- No synthetic SWMM output is treated as ground truth. The available feature files contain no spatially joined SWMM outputs, so physics-proxy ablation is not a SWMM-feature experiment.

## Evaluation Design and Results

Seed: `20261009`. Simple prevalence baseline, class-weighted Logistic Regression, and a regularized depth-3 decision tree were evaluated. Numeric imputation/scaling and categorical imputation/encoding were fit inside each training fold. Primary metric is average precision (reported as PR-AUC); ROC-AUC, precision, recall, and confusion counts are supporting measures. No hyperparameter tuning was performed.

| Fold | Rows | Positive | Negative | Training cells excluded by 500 m buffer |
|---:|---:|---:|---:|---:|
| 0 | 3215 | 133 | 3082 | 305 |
| 1 | 4044 | 185 | 3859 | 610 |
| 2 | 7096 | 414 | 6682 | 1462 |
| 3 | 11009 | 364 | 10645 | 923 |
| 4 (final test) | 22394 | 857 | 21537 | 1217 |

### Development folds 0–3 (macro mean, confusion counts summed)

| Feature set | Model | Macro PR-AUC | Macro ROC-AUC | Macro precision | Macro recall | Summed TN / FP / FN / TP |
|---|---|---:|---:|---:|---:|---|
| static_geographic | prevalence_baseline | 0.0446 | 0.5000 | 0.0000 | 0.0000 | 24268 / 0 / 1096 / 0 |
| static_geographic | logistic_regression | 0.1225 | 0.7777 | 0.0882 | 0.7975 | 15121 / 9147 / 235 / 861 |
| static_geographic | shallow_regularized_tree | 0.0727 | 0.6107 | 0.0824 | 0.6036 | 16882 / 7386 / 377 / 719 |
| static_geographic_plus_physics_proxies | prevalence_baseline | 0.0446 | 0.5000 | 0.0000 | 0.0000 | 24268 / 0 / 1096 / 0 |
| static_geographic_plus_physics_proxies | logistic_regression | 0.1139 | 0.7725 | 0.0864 | 0.8265 | 14873 / 9395 / 219 / 877 |
| static_geographic_plus_physics_proxies | shallow_regularized_tree | 0.0794 | 0.6552 | 0.0740 | 0.6599 | 15320 / 8948 / 294 / 802 |

Approach selected only from development folds by highest macro PR-AUC: **logistic_regression** with **static_geographic** (macro PR-AUC 0.1225). The prevalence baseline is a benchmark, not a tuning target.

### Reserved final spatial test fold 4 (evaluated once)

| Model | Feature set | PR-AUC | ROC-AUC | Precision | Recall | TN / FP / FN / TP |
|---|---|---:|---:|---:|---:|---|
| prevalence_baseline | static_geographic | 0.0383 | 0.5000 | 0.0000 | 0.0000 | 21537 / 0 / 857 / 0 |
| logistic_regression | static_geographic | 0.0791 | 0.7562 | 0.0735 | 0.8355 | 12505 / 9032 / 141 / 716 |

Fold 4 was excluded from model/feature selection and preprocessing. Only the selected development approach and its prevalence-baseline comparator were evaluated on fold 4. Full per-fold/aggregate metrics, final-test metrics, and reproducible prediction files are saved separately.

## Limitations

- Flood labels are mapped polygon observations. Negative labels mean “not covered by the mapped polygons under the 5% rule,” not verified no-flood outcomes; class imbalance and incomplete reporting can bias metrics.
- The local dataset has no event-linked flood outcomes and no spatial SWMM outputs. Results cannot validate forecasting, unseen-storm performance, hydraulic validity, or model calibration.
- The static + physics-proxy comparison uses available drainage/hydrology-derived spatial predictors, not mapped SWMM node/link outputs; it does not test the incremental value of spatially mapped SWMM results.
- Existing folds aggregate administrative wards into five regions; the 500 m buffer reduces adjacent-cell leakage but does not remove all spatial dependence. Polygon IDs were reconstructed from local geometries; 2 positive cells could not be linked.
- Only one held-out region is reserved as final test; performance uncertainty/generalization across alternative regions or storms remains unmeasured.
- No model score should be interpreted when a row is marked blocked or when either held-out class is absent.

Predicted scores are ranking outputs, **not calibrated flood probabilities**. The target is historical mapped-flood susceptibility, not future-event forecasting.

Reproduce with `python scripts/evaluate_static_flood_labels.py` using the repository `.venv`. Dataset hashes, row counts, feature lists, seed, selected approach, and fold settings are in `dataset_version.json`; saved fold assignments are reused without modification. `fold_metrics.csv` contains per-fold and aggregate development scores; `final_test_metrics.csv` contains only the selected approach and prevalence baseline for fold 4. Predictions are in compressed CSV files.
