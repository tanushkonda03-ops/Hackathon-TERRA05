# Phase 4 Scenario Engine

## Supported inputs

- `custom`: manual total rainfall and duration or an array of 15-minute rainfall depths in millimetres.
- `historical_replay`: E001 only. Rainfall observations are 3-hour IMD totals; the SWMM profile is reconstructed at 15-minute resolution.
- External live rainfall: not configured. A provider adapter can implement `fetch_profile()` and submit normalized 15-minute millimetre depths; no mock/live data source is bundled.
- Forecast rainfall: not configured.

## Orchestration and state

`POST /api/v1/scenario/run` creates a durable file-backed job and returns `202`. The existing asynchronous SWMM executor runs or reuses the deterministic hydraulic cache. Scenario states are `QUEUED`, `RUNNING`, `PHYSICS_COMPLETE`, `ML_RUNNING`, `COMPLETE`, `FAILED_PHYSICS`, and `FAILED_ML`. Poll `GET /api/v1/scenario/{id}` and fetch results from `GET /api/v1/scenario/{id}/results` after completion. Results include the citywide ranked risk map, physics coverage, GIS fallback, critical-asset cells and review-oriented decision support.

The SWMM cache includes the model input hash, rainfall source/profile hash, simulation settings, and cache schema version. Custom rainfall profiles do not reuse E001 output. Repeated identical scenarios return the stored job/result. E001 replay reuses the preserved Phase 1 baseline.

## Scenario demonstration

`custom_demo_150mm_6h_run.json` records a synthetic user-defined 150 mm / 6-hour run with a deterministic 15-minute profile. It is not an observed storm. SWMM output has no validated surface coupling; node depth fields are hydraulic proxies. Scenario XGBoost scores are uncalibrated extrapolations from the Phase 3 supplied-label fit; citywide cells outside the 1,516-cell Ward L physics domain use the existing GIS-only XGBoost model.

## Performance

See the demo artifact and final report for measured end-to-end, SWMM and ML timings. Timings vary by machine and cold/warm cache state. New SWMM jobs are asynchronous; requests do not wait for the solver.
