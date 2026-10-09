# Phase 3 dataset report

- Citywide target grid: 47,758 rows.
- Positive labels: 1,953 (4.09%); negatives: 45,805.
- `flood_fraction`: min 0.000, max 1.000, mean 0.0272, median 0.000.
- Physics-supported: 1,516; unsupported: 46,242. Unsupported SWMM fields remain null, not zero.
- Supported target distribution: positives 280 / 1,516.
- Feature groups: GIS 25, rainfall 8, nonempty SWMM 6.
- Rainfall is one E001 event; reconstructed 15-minute values, independently accumulated from IMD 3-hour observations.
- Spatial grid key: `grid_id`; GIS join and Phase 2 mapping are one-to-one.
- Historical label event/date provenance is not independently verified by source metadata; it is treated as the prescribed Phase 3 target but metrics describe agreement with these labels.
