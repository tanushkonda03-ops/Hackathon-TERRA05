# TERRA05 Phase 2A — Physics Engine

## Engine

- SWMM version: EPA SWMM 5.2.4 (existing Phase 1 baseline output reused).
- Routing: Dynamic Wave.
- Model: Existing-only Ward L/Mithi pilot; 3,314 conduits, 3,269 source nodes, 34 computational boundary objects and 1,516 subcatchments.
- Baseline solver execution: 210.925 seconds (Phase 1 record); Phase 2A extraction reuses the saved `.out` and does not rerun SWMM.

## Spatial physics

- Citywide 100 m grid cells mapped to nearest hydraulic objects: 47,758.
- Cells with direct pilot subcatchment assignment: 1,516; this is the modeled SWMM grid support.
- Pilot nodes/conduits/subcatchments mapped: 1,694/1,712/1,516.
- Grid nearest-node depth is retained only as `HYDRAULIC_PROXY`. `surface_water_depth_m` and surface storage are null because no validated surface coupling exists.
- SWMM runoff is a direct drainage input, node flooding is direct SWMM overflow, and nearest-object grid interpolation is an engineering proxy. No SWMM runoff is added to the fast surface model.

## Scenarios and execution

Scenario definitions support `historical_2005` and the 0.25, 0.50, 0.75, and 1.00 rainfall multipliers with existing infrastructure and tide disabled. Proposal modes and low/normal/high/very-high tide settings are represented in configuration but rejected for execution until their asset/boundary data is verified. SWMM submissions are asynchronous, deterministic-hash cached, and reuse completed Phase 1B outputs for the precomputed multipliers. Other supported multipliers run in an isolated directory. Fast 2D simulation remains available through `/api/v1/simulation/run`.

SWMM API: `POST /api/v1/simulation/swmm` submits a job; `GET /api/v1/simulation/swmm/{simulation_id}` returns status; `GET /api/v1/simulation/swmm/{simulation_id}/results/{table}` retrieves a normalized table; `POST /api/v1/simulation/swmm/compare` compares completed runs. Requests may supply a 15-minute `rainfall_profile_mm` with up to 108 intervals.

## Validation

- **ENGINE STATUS:** executable; Dynamic Wave output extracted with full 15-minute reporting time series.
- **HYDRAULIC VALIDATION STATUS:** hydraulically unvalidated; current baseline max node depth 23.276 m and max conduit velocity 14.978 m/s need engineering review.
- **OBSERVATIONAL CALIBRATION STATUS:** not performed.
- Tide is disabled in the SWMM scenario engine. Fast mode no longer converts tide labels into hidden drainage-capacity scaling.
- Flood state thresholds are configurable engineering thresholds, not calibrated municipal warning thresholds.

## Phase boundary

The surface engine remains a separate Mode A approximation. SWMM is Mode B. Mode C hybrid coupling is intentionally not inferred from nearest-node depth or duplicated runoff; it requires validated surface exchange locations/capacities and explicit volume-transfer bookkeeping. Continue to Phase 2B observational validation and calibration before treating results as authoritative flood predictions.
