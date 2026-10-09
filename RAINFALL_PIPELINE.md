# Rainfall Scenario Pipeline

Use the isolated generator from the repository root:

```powershell
python scripts/generate_rainfall_scenarios.py
python scripts/generate_rainfall_scenarios.py --dry-run
python scripts/generate_rainfall_scenarios.py --output-dir path\to\staging
```

The rainfall-only command writes only the five rainfall outputs in the selected directory. It does not load geospatial layers and does not create or modify citywide junction, outfall, conduit, subcatchment, Ward L, or ML files. Outputs are staged, validated, and atomically replaced; an existing file is restored if replacement fails.

## Scenario semantics

- `TS_2005_JULY26` has 108 records. Its 15-minute values are a synthetic temporal disaggregation of 3-hour source totals, not observed 15-minute measurements. The source-derived total is approximately 944.2 mm.
- `DESIGN_YELLOW_25MM`, `DESIGN_ORANGE_50MM`, `DESIGN_RED_100MM`, and `DESIGN_CLOUDBURST_150MM` are synthetic three-hour design storms. The number in each legacy ID is the target peak intensity in mm/hour.
- `DEPTH_25MM_3H`, `DEPTH_50MM_3H`, `DEPTH_100MM_3H`, and `DEPTH_150MM_3H` are synthetic three-hour total-depth scenarios.

Every value is rainfall depth for one 15-minute interval in millimetres. The catalogue intensity is the interval depth multiplied by four. The normalized twelve-interval profile is stored in `swmm_rainfall_metadata.json`, together with provenance and validation results.

## Application interface

`swmm_rainfall_catalog.csv` provides the stable base fields `timeseries_id`, `datetime`, `rainfall_15min_mm`, and `intensity_mm_per_hr`. The metadata sidecar provides scenario family, target, duration, units, provenance, and validation status. An application can aggregate catalogue rows by `timeseries_id` to expose scenario ID, interval values, peak intensity, total accumulated rainfall, duration, and provenance.

## SWMM limitation

The `.dat` files use the repository's existing named-series text convention and contain interval depths. No EPA-SWMM `.inp` model, rain-gauge definition, or rain-gauge reference is present in this repository. Therefore SWMM import and hydraulic simulation remain unverified. In particular, do not infer whether a target model expects `VOLUME` or `INTENSITY` until a real `.inp` rain-gauge and time-series configuration is available.

Run the focused tests with:

```powershell
python -m unittest discover -s tests -v
```
