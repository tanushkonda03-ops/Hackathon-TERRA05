# Ward L Conduit Roughness Sensitivity

This is a controlled sensitivity analysis, not calibration or validation. It compares the existing Ward L baseline with candidate copies that multiply every conduit Manning roughness by 0.8 and 1.2. Only the roughness field in `[CONDUITS]` is changed; node, subcatchment, rainfall, elevations, connectivity, infiltration, and outfall settings remain unchanged.

Run from the repository root:

```powershell
python scripts/run_swmm_roughness_sensitivity.py
```

Each scenario has its own directory containing the exact input used and its SWMM `.rpt` and `.out` outputs. The script writes `roughness_sensitivity_comparison.csv`, `run_log.txt`, and `artifact_integrity.json` in this directory. The manifest records baseline artifact hashes, candidate roughness ranges and changed-conduit counts, and the baseline reference check. Candidates are checked against a masked baseline before any simulation.

Metrics use the same SWMM report tables and PySWMM binary-output validation for every case. Volumes are reported in megaliters (ML), flows in cubic meters per second (m³/s), depths in meters, and continuity errors in percent. Failed, interrupted, parser-invalid, or SWMM-error cases are marked ineligible; do not use them as valid comparisons.

Results describe sensitivity to the specified uniform multipliers only. They do not establish calibrated roughness values, predictive accuracy, or hydraulic validity; all runs retain the baseline's event duration and other assumptions.