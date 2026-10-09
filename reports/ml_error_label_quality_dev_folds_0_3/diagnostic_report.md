# Development OOF Error and Label-Coverage Diagnostic

Only the preferred geographic Logistic Regression OOF predictions and saved spatial folds 0–3 were used. Fold-4 assignments were filtered out; no fold-4 labels, metrics, predictions, or outcomes were loaded or used. The saved assignments, predictions, and labels were not changed. False-positive/false-negative counts below use the existing 0.5 threshold; PR-AUC/ROC-AUC are threshold-independent ranking metrics.

## Fold Summary

| Fold | PR-AUC | ROC-AUC | FP @0.5 | FN @0.5 | FP with zero polygon overlap | FP with 1–5% overlap |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0.0872 | 0.7388 | 1007 | 36 | 958 | 30 |
| 1 | 0.1073 | 0.7498 | 3089 | 2 | 3012 | 53 |
| 2 | 0.1303 | 0.7620 | 3222 | 54 | 3162 | 36 |
| 3 | 0.1646 | 0.8636 | 1771 | 144 | 1731 | 24 |

At threshold 0.5, the OOF set contains **9089 false positives** and **236 false negatives**. These threshold errors are separate from ranking scores above.

## Polygon-Coverage Evidence

Mapped errors were joined by `grid_id` to the existing processed grid geometry and intersected with 332 local source flood polygons. Recomputed coverage is polygon-union intersection area divided by cell area; it is checked against the stored `flood_fraction`. Label/geometry mismatches among error cells: **0**.

False positives have `flood_label=0`, which under the source rule means polygon coverage does not exceed 5%; it does not mean a confirmed no-flood location. Of 9089 FPs, 8863 have no polygon overlap and 143 have 1–5% coverage below the positive threshold. False negatives are positive mapped cells by construction; source polygon IDs and coverage are in `threshold_0_5_error_cells.csv`.

## Regional / Feature Patterns

The error files include fold × ward counts and means/medians of available geographic and drainage features, compared with each fold's validation population. These are descriptive associations, not causal explanations.

- Fold 0 has the weakest ranking PR-AUC. Fold 1's low precision is associated with 3,089 threshold FPs and only 2 FNs; its very high recall is a threshold tradeoff, not strong ranking performance.
- Fold 3 has the strongest ranking PR-AUC but the largest FN count (144) and lowest baseline recall among these folds; stronger ranking can still miss positives at 0.5.
- Fold 2 also has many FPs (3,222) because the thresholded classifier predicts broadly; its PR-AUC is higher than folds 0–1.
- The leading error wards are fold 0: E (467), D (261), C (120), B (115); fold 1: F/N (952), F/S (752), G/N (734), G/S (653); fold 3: S (784), N (643), T (487), M/W (1).
- Descriptive feature contrast vs. each fold's validation mean: fold-0 FPs have distance_to_water -1781.2 m and building_density +1058.0; fold-3 FNs have distance_to_drain -794.1 m and building_density +102.4. These contrasts identify differences, not causes.
- Existing proxy ablation was mixed: static drainage/hydrology proxies changed fold PR-AUC by -0.0159, +0.0046, +0.0120, and -0.0303 for folds 0–3 respectively. No consistent improvement is supported.

## Evidence vs. Hypotheses

**Evidence:** errors vary substantially by spatial fold; mapped polygon coverage reconstructs the binary labels under the 5% rule; false positives include both zero-overlap cells and sub-threshold overlap cells; the positive label is based on mapped BMC polygon presence, not a confirmed survey of negatives. Feature and ward summaries are saved for direct inspection.

**Hypotheses, not established causes:** zero-overlap FPs may reflect incomplete flood-location mapping, genuine non-flood areas, or geographic distribution shift. Low-coverage FPs may reflect the hard 5% label threshold or polygon-boundary uncertainty. Fold-specific error patterns may also indicate omitted hydraulic/exposure variables. The available artifacts cannot distinguish these explanations or establish true negative status.

## Recommended Next Step

Use the error-cell CSV and intersecting source polygon IDs for a targeted label-coverage review with domain owners, prioritizing fold 1 zero-overlap FPs and fold 3 FNs. Keep uncertain negatives marked as unverified rather than relabeling them. Only after label coverage is clarified should another model comparison be run; any independent final evaluation needs a new untouched spatial holdout because fold 4 was previously inspected.

This is historical mapped-flood susceptibility analysis, not validated future-event forecasting. No fold-4 data, new model, threshold tuning, or label change was used.
