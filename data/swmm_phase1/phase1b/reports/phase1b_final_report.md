# TERRA05 Phase 1B Final Report

## Status: LEVEL C

Phase 1B preserved the original SWMM run, traced warnings/anomalies to source records and network context, and completed controlled rainfall sensitivity runs. No hydraulic input correction was justified by evidence; `validated.inp`, `validated.rpt`, and `validated.out` are byte-for-byte copies of the baseline.

## Results

- Baseline continuity errors: [-0.009, -0.05]% (runoff and routing); 36 Warning 04, two Warning 02.
- Highest depth: 23.276 m at source node 2178143402; highest conduit velocity: 14.978 m/s.
- Zero-flow conduits: 1292; zero-discharge artificial boundaries: 9 of 34.
- Rainfall scenarios completed: rainfall_25pct, rainfall_50pct, rainfall_75pct, diagnostic_10mm_1h, diagnostic_50mm_3h.
- Diagnostics, scenario metrics, baseline hashes, and validated copies are under `data/swmm_phase1/`.

## Recommendation

**Level C: engine-executable, hydraulically unvalidated.** Do not use simulated depth/velocity outputs as authoritative flood maps. Phase 2 should first validate vertical datum and node rim elevations, survey conduit inverts and the 36 minimum-drop links, verify physical outfalls and receiving-water/tide boundaries, refine rainfall observations and catchment routing, then calibrate against observed flows/water levels/flood extents. Keep the Phase 1B scenarios as sensitivity evidence only.
