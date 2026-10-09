# TERRA05 Phase 3 model card

## Model
XGBoost binary classifier, `terra05-xgb-v1.0.0`. The primary artifact uses SWMM features for covered cells; a separate GIS-only model is used for uncovered cells.

## Target
`flood_label`, interpreted per Phase 3 specification as historical July-2005 waterlogging. Existing label source metadata does not independently prove the event match; evaluation is against supplied labels. `flood_fraction` is target-only and not a regressor in this phase.

## Inputs
Terrain, drainage, land cover/built environment, E001 rainfall summary, and SWMM-derived hydraulic features where covered. `built_up_fraction` is a land-cover proxy, not measured imperviousness. Nearest node depth is a hydraulic proxy, not street water depth.

## Training domain
Physics-supported: 1,516 of 47,758 cells, all in the Ward L pilot. The citywide GIS-only model uses all cells but has no SWMM physics outside the 1,516 covered cells.

## Validation
Primary benchmark uses disjoint 2 km spatial blocks within the pilot; groups are recorded in metadata. Citywide GIS uses existing five-region folds; fold 4 selects the threshold and fold 2 tests. One E001 record per cell is used; no duplicated rainfall scenarios.

## Metrics
PR-AUC, ROC-AUC, precision, recall, F1, balanced accuracy, and confusion matrices are in `experiment_comparison.csv`. Scores are not probability-calibrated.

## Limitations
Historical target event/date provenance needs confirmation; 15-minute rainfall is reconstructed from IMD three-hour totals; SWMM is executable but hydraulically unvalidated; nearest-node depth is not street depth; only 1,516 cells have SWMM features; no future-event labels support scenario forecasting. Risk levels are validation-score quantiles, not BMC warning levels.
