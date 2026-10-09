# TERRA05 Phase 4 Final Report

## 1. Objective
Extend the existing Phase 3 pipeline with provenance-audited event handling and asynchronous SWMM-to-ML scenario execution.

## 2. Existing Phase 3 Baseline
Retained `terra05-xgb-v1.0.0`, its Phase 3 spatial-block evaluation and the Random Forest benchmark. These are E001 supplied-label spatial tests, not event-holdout validation.

## 3. Historical Event Registry
Five events E001–E005 are recorded in `event_registry.csv`.

## 4. Event Eligibility
E001: insufficient target provenance; E002: rain-only partial bulletin; E003/E004: insufficient rainfall amounts; E005: insufficient provenance/candidate. No Phase 4 supervised-eligible event.

## 5. Multi-Event Dataset
47,758 event-grid candidate rows retained from E001 with `event_target_eligibility=INSUFFICIENT_PROVENANCE`; zero rows admitted to train/validation/test. 47,758 unique event/grid keys; 0 duplicates and 0 conflicts.

## 6. SWMM Event Simulations
One new deterministic synthetic custom hyetograph was executed through existing EPA SWMM Dynamic Wave; runtime 93.46899999992456 s. Historical E001 is replayable through the preserved Phase 1 result cache. No additional historical events were simulated because available rainfall inputs are incomplete or ambiguous.

## 7. Physics Feature Generation
Existing spatial mapping and extraction reused. The demonstration produced 1,516 physics-supported Ward L cells; nearest-node depth remains `HYDRAULIC_PROXY`. No surface depth is returned.

## 8. ML Training
No Phase 4 model was fitted because no event-matched target is defensible. The Phase 3 model is reused only as an explicitly marked exploratory scenario-ranking baseline.

## 9. Spatial Validation
Existing Phase 3 2 km spatial-block validation remains unchanged and applies to one supplied-label dataset only.

## 10. Unseen Event Validation
MULTI_EVENT_SUPERVISED_VALIDATION_NOT_SUPPORTED. No defensible event-level generalization metric can be reported.

## 11. GIS Baseline
Phase 3 spatial test PR-AUC 0.1853, ROC-AUC 0.5670, precision 0.1478, recall 0.9677, F1 0.2564.

## 12. GIS + Rainfall
Phase 3 spatial test PR-AUC 0.1926, ROC-AUC 0.5807, precision 0.1526, recall 0.9355, F1 0.2624.

## 13. GIS + Rainfall + SWMM
Phase 3 spatial test PR-AUC 0.2408, ROC-AUC 0.6204, precision 0.1445, recall 0.9839, F1 0.2521. These are not multi-event results.

## 14. Random Forest
Phase 3 same-split benchmark test PR-AUC 0.2489, ROC-AUC 0.6489, precision 0.1706, recall 0.9355, F1 0.2886.

## 15. Physics Contribution
On the Phase 3 test split, SWMM features add +0.0482 absolute PR-AUC vs GIS + rainfall. This is single-event supplied-label association, not evidence of unseen-event benefit.

## 16. Final Model Selection
No Phase 4 model selected. Phase 3 Random Forest has higher test PR-AUC/ROC-AUC than the XGBoost physics model, but data provenance prevents declaring an event-generalizing production winner. Existing API baseline remains in place.

## 17. Real-Time Scenario Engine
Manual total/duration, normalized 15-minute profiles and E001 historical replay supported. Jobs are asynchronous and cache-keyed. External live/forecast sources are not configured; UI states this.

## 18. API Architecture
`POST /api/v1/scenario/run`; `GET /api/v1/scenario/{id}`; `GET /api/v1/scenario/{id}/results`. Existing ML and SWMM APIs remain.

## 19. Frontend Integration
Added a scenario panel with historical replay/custom rainfall, job polling, cache/status, risk summary, top-ranked cells and provenance caveats. A separate Scenario ML Risk fill/outline layer updates for the mapped Ward L grid cells; the existing risk grid and fast 2D engine remain separate.

## 20. Critical Infrastructure
Scenario result ranks cells with existing hospital/critical-asset flags and surfaces top exposed asset cells. This is grid-level exposure, not asset-specific impact measurements.

## 21. Decision Support
Outputs field-review priorities for high-risk and critical-asset grid cells and explicitly states scores are uncalibrated and need current observation confirmation.

## 22. Performance
Demo job end-to-end (cached SWMM): 9.982 s; ML inference: 5.554912 s for 47758 citywide cells; cold SWMM solver runtime: 93.46899999992456 s; final SWMM cache hit: True. Timings are measured on this machine.

## 23. Limitations
No valid event-matched labels for event holdout; target source date unresolved; reconstructed rainfall; SWMM uncalibrated; surface coupling absent; only Ward L hydraulic coverage; scenario scores are out-of-domain extrapolations; no live rainfall provider.

## 24. Reproducibility
Run `python scripts/build_phase4_audit.py`, `python scripts/run_phase4_demo.py`, and `python scripts/build_phase4_reports.py`. Model comparison source and hashes are preserved under `data/ml_phase3` and `data/ml_phase4`.

## 25. Final Verdict
PHASE_4_COMPLETE_WITH_DATA_LIMITATIONS for the implemented/audited scenario workflow and exercised demo. Multi-event supervised training and unseen-event validation remain unsupported by the repository's labels; no scientific generalization claim is made.
