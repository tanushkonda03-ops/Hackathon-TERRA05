# Phase 1B Diagnostics

## Baseline integrity

Phase 1 input/report/output were snapshotted under `data/swmm_phase1/baseline/` before any Phase 1B run. SHA-256 hashes are in `baseline_manifest.json`. `validated.inp/.rpt/.out` are copied unchanged because there is no defensible source correction to apply.

## Findings

- Source-audit inputs: 34,711 source conduits and 34,345 endpoint node IDs; pilot has 3,269 nodes, 3,314 conduits, 34 artificial pilot boundaries, and 1,516 grid catchments.
- Baseline SWMM 5.2.4 completed with runoff/routing continuity errors [-0.009, -0.05]%; warnings: 36 Warning 04 and two Warning 02.
- Warning 04 cases: 36/36 joined to source conduit/endpoints. The detailed file preserves node elevations, their source classification, source endpoint inverts, length, and raw slope. It is a data/input condition; do not replace elevations with SWMM's minimum slope.
- Extreme node result: 2178143402 reaches 23.276 m. Top 20 node table includes network distance, boundary role, inflow/outflow and flooding quantities. These are simulated maxima under assumed rim/elevation and rainfall inputs, not validated flood depths.
- Max conduit velocity 14.978 m/s. Top 20 records preserve source slope, endpoint inverts, and peak flow.
- Zero-flow links: 1292 of 3,314. They are retained in the network and individually annotated with component, upstream catchment reachability, and downstream boundary reachability; zero flow alone does not establish a disconnected link.
- Boundary analysis: 34 objects; 9 carry zero reported outflow. They are artificial computational boundaries, and physical outfalls/receiving-water levels are not verified.
- Catchment assignments: 1516 records, 0 invalid outlet references and 203 outlets over 500 m. Long nearest-node distances are potential spatial representativeness issues.
- INP graph has 3273 nodes and 3314 conduits; all pilot conduit IDs and endpoint pairs match (0 missing IDs, 0 unexpected IDs, 0 missing endpoint pairs, 0 unexpected endpoint pairs). The 20 selected source components form 23 INP graph components after boundary aliases.

## Sensitivity runs

`scenario_metrics.json` and `baseline_vs_validated.csv` record the 25%, 50%, and 75% scaled 2005 profile runs plus 10 mm/1 h and 50 mm/3 h constant-intensity diagnostic runs. These isolate rainfall-volume sensitivity and basic execution response; they are not calibration or design storms.

## Decision

**LEVEL C** — the engine executes and continuity is good, but the hydraulic outputs are not suitable for operational interpretation while the elevations, roughness, rainfall profile, DEM datum, boundary placement, and catchment routing remain unverified and the baseline exhibits extreme depths/velocities and numerous zero-flow links. No elevations, slopes, roughnesses, or boundary conditions were silently changed.
