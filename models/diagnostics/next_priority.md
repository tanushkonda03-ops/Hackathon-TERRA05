# Ward L Next-Priority Diagnostic

Read-only diagnostic of rainfall duration and the ten largest baseline junction depths. No simulation was run; the existing `models/ward_L_kurla.inp`, `.rpt`, `.out`, and prepared datasets were read as-is.

## Rainfall Duration

| Artifact | Start timestamp | End timestamp / coverage | Records or intervals | Timestep | Total rainfall |
|---|---|---|---:|---:|---:|
| E001 event metadata | 2005-07-26 00:00 | 2005-07-27 03:00 | elapsed 27 h | n/a | `rainfall_24h_mm` = 944.2 mm |
| E001 derived observations | 2005-07-26 03:00 | 2005-07-27 03:00 | 9 values (3 h accumulation field) | 3 h values | 944.20 mm |
| Generated SWMM time series | 2005-07-26 00:00 | last record 2005-07-27 02:45; coverage ends 2005-07-27 03:00 | 108 records / 108 rainfall intervals (27 h) | 15 min | 944.200 mm |
| Baseline INP reference `TS_2005_JULY26` | 2005-07-26 00:00 | last record 2005-07-27 02:45; INP run ends 2005-07-27 03:00 | 108 records | 15 min | 944.200 mm |

The baseline rain gage references `TS_2005_JULY26` with a 15-minute `VOLUME` interval. The parsed timestamp/value rows in the embedded series match the generated series: **True**. The model run window is 27 h. Event metadata and the generated/embedded SWMM forcing therefore span 27 h, while the same 944.2 mm is labeled as a 24-hour total. The nine source observations are timestamped every 3 h from 2005-07-26 03:00 to 2005-07-27 03:00; their first 0.9 mm value is also treated as a 3-hour interval beginning at 26 July 00:00.

**Source location of the duration discrepancy:** [scripts/build_rainfall_observations.py#L21](scripts/build_rainfall_observations.py#L21), [scripts/build_rainfall_observations.py#L35](scripts/build_rainfall_observations.py#L35), and [scripts/build_rainfall_observations.py#L41](scripts/build_rainfall_observations.py#L41) create the leading 0.9 mm interval; [scripts/build_rainfall_feature.py#L62](scripts/build_rainfall_feature.py#L62) sums all nine 3-hour values into `rainfall_24h`; and [scripts/prepare_swmm_datasets.py#L359](scripts/prepare_swmm_datasets.py#L359) / [scripts/prepare_swmm_datasets.py#L381](scripts/prepare_swmm_datasets.py#L381) / [scripts/prepare_swmm_datasets.py#L396](scripts/prepare_swmm_datasets.py#L396) explicitly generate nine 3-hour blocks (108 15-minute intervals). The event fields are at [scripts/build_rainfall_events.py#L11](scripts/build_rainfall_events.py#L11) and [scripts/build_rainfall_events.py#L15](scripts/build_rainfall_events.py#L15). The local artifacts do not establish whether the leading interval should be included in the intended 24-hour rainfall window; no duration/value correction is assumed here.

## Ten Highest Junction Depths

Ranked by maximum depth in the existing baseline RPT. `OUT sampled max` is the largest 15-minute binary-output depth for that node; it can be lower than the RPT maximum because it is sampled at report timesteps.

| Junction ID | Invert THD (m) | RPT max depth (m) | OUT sampled max depth (m) | RPT max ponded depth (m) | Prepared ground THD (m) | Prepared ground MSL (m) | Ponding enabled |
|---|---:|---:|---:|---:|---:|---:|---|
| 2177117804 | 34.100 | 91.800 | 91.605 | 82.444 | 43.459 | 16.027 | YES |
| 2177117803 | 33.859 | 91.520 | 91.358 | 81.924 | 43.459 | 16.027 | YES |
| 2177117802 | 33.410 | 91.430 | 91.284 | 84.403 | 40.437 | 13.005 | YES |
| 2177117801 | 33.373 | 91.360 | 91.219 | 84.299 | 40.437 | 13.005 | YES |
| 2177129101 | 44.660 | 91.090 | 91.029 | 80.883 | 54.871 | 27.439 | YES |
| 2177129001 | 44.288 | 89.640 | 89.384 | 81.398 | 52.531 | 25.099 | YES |
| 2178110902 | 44.079 | 88.880 | 88.518 | 82.303 | 50.661 | 23.229 | YES |
| 2177119801 | 40.480 | 88.690 | 88.635 | 79.742 | 49.426 | 21.994 | YES |
| 2178110903 | 43.902 | 88.140 | 88.011 | 81.482 | 50.564 | 23.132 | YES |
| 2177118801 | 39.110 | 88.000 | 87.845 | 75.193 | 51.917 | 24.485 | YES |

Invert elevations are from the baseline INP `[JUNCTIONS]` values in THD. Prepared ground elevations are the dataset's `ground_elev_thd_m` / `ground_elev_msl_m`, not verified surveyed rim measurements. The prepared-data producer derives node invert as the minimum incident conduit invert ([scripts/prepare_swmm_datasets.py#L130](scripts/prepare_swmm_datasets.py#L130)); ground elevation is DEM-sampled when valid ([scripts/prepare_swmm_datasets.py#L135](scripts/prepare_swmm_datasets.py#L135)), otherwise estimated ([scripts/prepare_swmm_datasets.py#L138](scripts/prepare_swmm_datasets.py#L138)), then may be raised by a minimum-depth constraint ([scripts/prepare_swmm_datasets.py#L146](scripts/prepare_swmm_datasets.py#L146)). The prepared CSV does not retain a per-node flag showing which ground-elevation path was used, so that provenance cannot be resolved for each listed node from existing artifacts. Ponding is globally enabled in the baseline (`ALLOW_PONDING YES`).

## Recommendation

Resolve the E001 rainfall window/first 3-hour interval semantics in the source data definition before further model tuning: the forcing artifacts agree with each other, but their 27-hour construction conflicts with the `rainfall_24h_mm` label. This is a sensitivity/input-definition issue, not evidence for choosing which duration is correct.
