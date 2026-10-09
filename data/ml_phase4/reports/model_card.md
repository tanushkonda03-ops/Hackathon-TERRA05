# TERRA05 Phase 4 Model Card

- **Candidate version:** `terra05-ml-v2.0.0` (scenario pipeline version; no new supervised estimator was fit)
- **Serving baseline:** Phase 3 XGBoost `terra05-xgb-v1.0.0`; Random Forest retained as its Phase 3 benchmark.
- **Training/validation/test events:** none eligible for event-held-out training or testing. E001 event-grid labels are retained only as a supplied-label audit candidate because target event/date matching is unverified.
- **Target:** `flood_label` / `flood_fraction` from the supplied flood grid, type `supplied_historical_waterlogging_label`; not independently verified for E001.
- **Feature groups:** GIS, rainfall summary, and SWMM hydraulic features. The existing model has 25 GIS, 8 rainfall and 6 nonempty SWMM features.
- **SWMM:** EPA SWMM 5.2.4 Dynamic Wave; executable but not calibrated or validated against event-matched observed depths/flows.
- **Physics coverage:** 1,516 Ward L cells of 47,758. Nearest-node depth is `HYDRAULIC_PROXY`; not surface water depth.
- **Evaluation:** Phase 3 three-way 2 km spatial block split within one supplied-label event; no unseen-event validation. Scores are uncalibrated ranking values.
- **Threshold:** existing Phase 3 physics-model validation-selected threshold, 0.00129476. It does not define an official warning threshold.
- **Known limitations:** no defensible multi-event target set; reconstructed E001 15-minute rainfall; uncertain target provenance; incomplete citywide SWMM coverage; uncalibrated hydraulic network; scenario inference is extrapolation; no external live/forecast rainfall source.
- **Production selection:** no Phase 4 replacement selected. Phase 3 test metrics show the Random Forest benchmark slightly ahead on PR-AUC and ROC-AUC; absent event-matched validation, Phase 4 cannot establish a stable production winner.
