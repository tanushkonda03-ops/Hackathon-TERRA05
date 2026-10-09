# TERRA05 Phase 1 SWMM Engineering Report

## Status

The real EPA SWMM ... EPA SWMM 5.2 (Build 5.2.4) engine executed a Dynamic Wave, Existing-only Ward L/Mithi-area model. This is an engineering-estimate MVP, not a calibrated or complete BMC municipal hydraulic model.

## Existing components reused

- BMC storm-drain GeoJSON, 100 m flood grid, DEM, and reconstructed rainfall catalogue.
- Existing project datum convention (+27.432 m from DEM MSL to BMC THD) and existing Manning/Horton MVP values, now explicitly classified.
- Existing 2D engine and ML assets were not modified.

## Network and event

- Source: 34711 conduits, 34345 endpoint node IDs; status counts {'Existing': 23465, 'Proposal': 11246}.
- Existing-only source graph: 23465 conduits, 24035 nodes, 858 components.
- Pilot: 3269 nodes, 3314 conduits, 20 connected components, 34 explicitly assumed pilot boundaries, 1516 100 m subcatchments.
- Area: 1516.000 ha, calculated from projected polygon geometry.
- Rain: reconstructed 26 July 2005 time series, 108 intervals at 15 minutes, 944.200 mm total. Not observed 15-minute rainfall.

## Execution

- Command: `runswmm.exe <model.inp> <model.rpt> <model.out>`
- Return code: 0; runtime: 210.925 s.
- RPT: `data\swmm_phase1\runs\2005\terra05_wardL_2005.rpt`; OUT: `data\swmm_phase1\runs\2005\terra05_wardL_2005.out`.
- Continuity error values (%): [-0.009, -0.05].
- Sanity checks: max depth 23.276 m; max absolute link velocity 14.978 m/s; max absolute link flow 159.808 m³/s; any runoff True.
- SWMM warnings: 38; sanity flags: {'continuity_below_1_percent': True, 'node_depth_over_10m': True, 'conduit_velocity_over_10m_s': True, 'zero_flow_conduits_present': True, 'boundary_outfalls_with_zero_flow': 9}.

## Parameter classification

### SOURCE-DERIVED

Conduit IDs, endpoint IDs, dimensions, endpoint inverts, lengths, status and shape labels; DEM samples; flood-grid polygons; source rainfall aggregation values.

### DERIVED

Projected coordinates, existing-only graph, pilot component membership, minimum endpoint invert per node, conduit endpoint offsets preserving source inverts, exact polygon area, nearest-node catchment outlet, built-up land-cover proxy.

### ASSUMED

Manning n by shape; OREC interpreted as open rectangular; Horton max/min rates 50/5 mm/h, decay 3 1/h and dry time 7 days; subcatchment roughness and depression storage; rim depth fallback at connected pipe height plus 0.3 m; FREE hydraulic boundaries at graph sinks. None are presented as measured/calibrated BMC values.

### SCENARIO

Existing-only infrastructure, reconstructed historical rainfall, no tide. The synthetic tide catalogue is not used.

## Limitations and unresolved data gaps

- The input network has 858 disconnected Existing-only components. Pilot components are separate and not artificially bridged.
- A graph sink is not evidence of a physical receiving-water outfall. SWMM boundary nodes are labeled pilot boundary assumptions; no historical tide/stage boundary is asserted.
- Repository vertical datum documentation supplies a 27.432 m offset, but raster metadata do not independently verify the vertical datum. Nodes with insufficient DEM cover use an explicitly assumed rim depth.
- Land-cover built-up fraction is an imperviousness proxy; nearest-node outlet association is an MVP spatial assignment.
- Manning, Horton, storage, and selected boundary parameters are uncalibrated assumptions. No flood labels were used to calibrate them.
- SWMM reports zero engine errors but numerical success does not validate hydraulic calibration or physical representativeness.
- The run has flagged sanity results (depth/velocity thresholds and low-flow/network warnings); these require engineering review before treating hydraulic depths as decision outputs.

## Reproduction

```powershell
.venv\Scripts\python.exe scripts\swmm_phase1.py --audit
.venv\Scripts\python.exe scripts\swmm_phase1.py --build
.venv\Scripts\python.exe scripts\swmm_phase1.py --run
```

## Artifacts

- `data/swmm_phase1/audit/drainage_source_audit.json` and `.csv`
- `data/swmm_phase1/audit/geometry_audit.csv`, `terminal_node_classification.csv`
- `data/swmm_phase1/network/pilot_nodes.csv`, `pilot_conduits.csv`, `pilot_subcatchments.csv` and GeoJSONs
- `data/swmm_phase1/models/terra05_wardL_2005.inp`
- `data/swmm_phase1/runs/2005/terra05_wardL_2005.rpt` and `.out`
- `data/swmm_phase1/results/node_results.csv`, `conduit_results.csv`, `subcatchment_results.csv`, GeoJSONs and `water_balance.json`
- `data/swmm_phase1/reports/swmm_build_report.json`, `swmm_run_report.json`, `swmm_validation_report.json`
- `data/swmm_phase1/metadata/model_manifest.json`
- `data/swmm_phase1/metadata/environment_report.json`
- `data/swmm_phase1/results/swmm_to_grid_mapping.csv`

## Definition of Done

**PHASE_1_BLOCKED**: the model builds and runs, but hydraulic sanity review remains outstanding. Current flags include peak node depth 23.28 m, peak conduit velocity 14.98 m/s, 36 minimum-elevation-drop warnings, 1292 conduits with no flow, and 9 pilot boundaries with no outflow. See `data/swmm_phase1/reports/diagnostics.md` for issue observations and next actions.
