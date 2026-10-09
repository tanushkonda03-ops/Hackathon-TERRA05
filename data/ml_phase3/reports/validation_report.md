# Phase 3 validation report

## Physics-supported benchmark
Spatial blocking: 2 km projected blocks. Groups: train 7, validation 3, test 3; no block is shared. Rows/positives: {"train": {"cells": 463, "positive": 37}, "validation": {"cells": 626, "positive": 181}, "test": {"cells": 427, "positive": 62}}. Threshold selected on validation only.

## Citywide GIS-only benchmark
Existing five-region spatial fold 4 is threshold validation; fold 2 is untouched test. Metrics: {"validation": {"pr_auc": 0.07709771233282355, "roc_auc": 0.7058618125849906, "precision": 0.10044642857142858, "recall": 0.052508751458576426, "f1": 0.06896551724137931, "balanced_accuracy": 0.5168983837155444, "confusion_matrix_tn_fp_fn_tp": [[21134, 403], [812, 45]], "threshold": 0.8984069764614104}, "test": {"pr_auc": 0.1628125101144901, "roc_auc": 0.7840848330393494, "precision": 0.0, "recall": 0.0, "f1": 0.0, "balanced_accuracy": 0.5, "confusion_matrix_tn_fp_fn_tp": [[6682, 0], [412, 0]], "threshold": 0.8984069764614104}}.

## Constraints
There is one event and the historical label's event/date linkage is not independently established in repository metadata. Metrics describe spatial holdout agreement with supplied labels, not generalization to other events or calibrated probabilities.
