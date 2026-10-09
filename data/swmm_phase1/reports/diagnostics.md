# SWMM Phase 1 Diagnostics

## Resolved execution issue: SWMM ERROR 141

**ISSUE:** EPA SWMM rejected four graph terminals because each had more than one inlet link.

**OBSERVATION:** SWMM requires an outfall object to have one inlet link. The source graph contains multi-inlet directed terminal nodes.

**POSSIBLE CAUSES:** (1) source terminal represents a junction rather than an outfall; (2) source node aggregation combines several discharge endpoints; (3) physical BMC topology is incomplete.

**SELECTED CAUSE:** The source has graph terminals with multiple incoming links, but does not establish whether each is a physical outfall.

**WHY:** The machine-readable source graph has no surveyed receiving-water designation at those node IDs.

**FIX:** Represented each incoming conduit with a colocated, separately labeled pilot-boundary outfall. Added no synthetic connector and retained source endpoint invert/geometry.

**VALIDATION:** EPA SWMM 5.2.4 rerun completed with return code 0, no fatal errors, and both `.rpt` and `.out` generated.

**REMAINING RISK:** These are execution boundaries, not verified physical outfalls; splitting removes flow mixing at the original source terminal.

## Unresolved hydraulic sanity findings

**ISSUE:** The numerical run contains extreme values and many idle links/outlets.

**OBSERVATION:** Maximum node depth is 23.276 m; maximum conduit velocity is 14.978 m/s; 36 SWMM WARNING 04 minimum elevation-drop notices; 2 WARNING 02 node-depth increases; 1292 of 3314 conduits have no simulated flow; 9 of 34 pilot-boundary objects have zero outflow. Continuity errors are [-0.009, -0.05]%.

**POSSIBLE CAUSES:** (1) source inverts/DEM vertical datum mismatch; (2) nearest-node catchment assignment is not a hydraulic delineation; (3) disconnected components or directed topology do not reflect actual flow paths; (4) engineering-estimate roughness/infiltration/boundary assumptions; (5) extreme reconstructed storm forcing.

**SELECTED CAUSE:** Not determinable from repository data alone.

**WHY:** No verified node rim survey, complete physical outfall inventory, calibrated flows, or authoritative catchment-to-inlet mapping is supplied. The source-level invert/DEM offset cannot be independently confirmed from raster metadata.

**FIX:** No hydraulic values were tuned to suppress these findings. Raw slopes, elevations, warnings, zero-flow links, and boundary assumptions remain traceable in audit/result artifacts.

**VALIDATION:** EPA SWMM 5.2.4 ran Dynamic Wave. Runoff continuity error is -0.009%; flow-routing continuity error is -0.050%. Source-data, geometry, references, rainfall, and CSV/GeoJSON extraction completed. Full `pytest` suite: 31 passed.

**REMAINING RISK:** Do not use the depth/velocity outputs as operational flood forecasts. **PHASE_1_BLOCKED** pending independent engineering review of vertical datum/rims, boundary placement, idle network sections, and outlet assignments.

## Exact next action

Obtain/verify BMC node rim elevations and vertical datum, receiving-water/outfall designations, and inlet/catchment connectivity for the selected Ward L components. Reconcile those against `audit/elevation_audit.csv`, `audit/terminal_node_classification.csv`, `network/pilot_subcatchments.csv`, and the conduit IDs cited in `runs/2005/terra05_wardL_2005.rpt`; then rebuild and rerun without changing source values silently.
