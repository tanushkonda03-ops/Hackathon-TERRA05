# Final SWMM quality report — Phase 2B

## 1. Executive summary
Frozen status: **SWMM_CALIBRATION_READY_DATA_LIMITED**. EPA SWMM 5.2.4 Dynamic Wave baseline is preserved and copied byte-for-byte to `final/`. No hydraulic calibration or observational hydraulic validation is claimed. The ML handoff contains event-level, pilot-grid features with explicit proxy/missingness flags.

## 2. Model architecture
The existing infrastructure model has 3,314 conduits, 3,269 nodes, 1,516 subcatchments, 34 assumed computational boundaries, and a reconstructed July 2005 storm. Phase 2A spatial mapping and scenario API are reused.

## 3–5. Source data, limitations, and observation inventory
See `calibration/observations_registry.csv`. `rainfall_observations_v1.csv` contains verified IMD Santacruz 3-hour interval rainfall for E001 and supports rainfall validation. BMC flood-spot labels lack demonstrated event date, depth, timing, and event-matched spatial extent; they are ineligible for E001 hydraulic calibration. BMC flow-level sensor file provides sensor inventory geometry, not readings. E002–E005 do not supply matching hydraulic event observations.

## 6. Rainfall validation
The model storm is a reconstruction (108 × 15 minutes; 944.182 mm in the SWMM input). `calibration/rainfall_validation.csv` compares the reconstructed 15-minute bins aggregated into 3-hour intervals against nine independently reported IMD intervals. The event total is checked against 944.2 mm; this validates interval accumulation to the coarser source resolution, not the reconstructed within-interval 15-minute shape. Hydraulic parameters were not adjusted to compensate. Rainfall scale sensitivity outputs from Phase 1B are retained; no new full-model parameter perturbations were run.

## 7–8. Elevation validation and Warning 04
All 36 Warning 04 cases are in `calibration/elevation_validation.csv`. Source node elevation and invert values are retained. The DEM-derived ground and cover are not treated as authoritative because a vertical datum tie, including the proposed 27.432 m transformation, is not documented. Cases are UNCERTAIN; no artificial elevation drops were introduced. The existing Phase 1B report identifies source endpoint differences below SWMM's minimum as the warning mechanism.

## 9. Outfall validation
`calibration/outfall_validation.csv` reviews all 34 assumed computational boundaries. No repository evidence verifies coast, river, Mithi, open-drain or receiving-water identity or stage; all remain unknown/low confidence. Tide remains disabled.

## 10. Catchment validation
`calibration/catchment_outlet_review.csv` lists assignments over 500 m (203 expected from Phase 1B). Distance alone cannot prove a routing error; source network topology/flow direction is insufficient to remap, so assignments remain unchanged and UNKNOWN.

## 11. Parameter sensitivity
`calibration/parameter_sensitivity.csv` documents rainfall multiplier response for peak node depth, peak velocity, peak flow, and flooded-node count from the already executed 25/50/75/100% scenarios. This is rainfall uncertainty sensitivity only. Hydraulic parameter OAT is unavailable: no new ~211-second full runs were justified without observations; those sensitivities are explicitly marked not run. This is a documented limitation rather than a completed hydraulic-parameter sensitivity study.

## 12–13. Calibration methodology and results
No calibration objective/search was run. Direct hydraulic observations are absent, so calibrated parameters = none and best objective = N/A. Assumed parameters remain frozen at their Phase 1 baseline values. This avoids fitting SWMM to its own output or to unverified historical flood labels.

## 14. Validation results
Rainfall can be checked at the published IMD 3-hour intervals, but independent hydraulic validation is unavailable. No RMSE/MAE/NSE/IoU or event timing metrics are claimed.

## 15. Water balance
The Phase 2A baseline water-balance outputs remain the source for the computed SWMM accounting. These are internal numerical balance checks, not independent validation of real-world water fluxes. Surface storage and street flood depth remain unavailable; SWMM node depth is not represented as street depth.

## 16. Scenario results
Phase 2A retains historical_2005 and rainfall_025/050/075/100 plus custom 15-minute inputs with existing infrastructure. Proposal infrastructure and tide remain disabled. Final files are copies of the executed baseline; no scenario overwrote Phase 1 artifacts.

## 17. Uncertainty
Dominant uncertainties: reconstructed sub-hourly rainfall shape; assumed conduit roughness/infiltration/imperviousness; 34 unverified boundaries; unknown vertical datum; long-distance outlet assignments; no surface coupling. `calibration/parameter_sensitivity.csv` and the manifest distinguish known uncertainty from measured sensitivity.

## 18. Final model status
**SWMM_CALIBRATION_READY_DATA_LIMITED**. The model executes reproducibly and is frozen for ML handoff, but remains hydraulically unvalidated and uncalibrated.

## 19. ML handoff
`ml_ready/physics_features_v1.csv` contains one record per directly mapped Phase 2A pilot grid cell for E001, with event window, reconstructed rainfall summaries, direct SWMM hydraulic values where available, and explicit nulls/provenance flags for unavailable surface/terrain fields. Nulls are deliberate; no missing measurements were fabricated.

## 20. Remaining limitations
No event-matched depth/flow/stage/flood extent; datum unresolved; 34 assumed boundaries; 203 questionable/unknown long assignments; Warning 04 endpoint differences retained; no surface-water routing; hydraulic parameter sensitivity not run; no multi-event hydraulic validation. Reopen SWMM work only if authoritative source data or a critical correctness defect becomes available.
