# Phase 3 target leakage audit

Only the explicit GIS, rainfall, and SWMM feature whitelists are considered predictors. `flood_label` and `flood_fraction` are target-only. All flood-derived, identifier, mapping classification, validation, and provenance columns are excluded.

| feature | source | allowed_as_feature | reason |
|---|---|---:|---|
| grid_id | target / identifier / provenance / split metadata | False | Identifier, label, quality/provenance field, or unapproved column; excluded from predictors. |
| ward | target / identifier / provenance / split metadata | False | Identifier, label, quality/provenance field, or unapproved column; excluded from predictors. |
| flood_label | target / identifier / provenance / split metadata | False | Target or target-derived field is excluded from X. |
| flood_fraction | target / identifier / provenance / split metadata | False | Target or target-derived field is excluded from X. |
| spatial_cv_fold | target / identifier / provenance / split metadata | False | Identifier, label, quality/provenance field, or unapproved column; excluded from predictors. |
| elevation_mean | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| slope_mean | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| flow_accumulation | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| flow_accumulation_area_km2 | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| flow_accumulation_log | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| drain_density | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| distance_to_drain | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| distance_to_water | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| built_up_fraction | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| vegetation_fraction | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| water_fraction | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| mangrove_fraction | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| building_count | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| building_density | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| clay_percent | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| sand_percent | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| silt_percent | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| infiltration_proxy | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| topographic_wetness_index | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| drain_capacity_proxy_m2 | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| drainage_stress_index | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| road_length_m | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| has_railway | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| has_hospital | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| is_critical_asset_cell | existing GIS master | True | Explicitly whitelisted feature group; see source/provenance fields. |
| event_id | target / identifier / provenance / split metadata | False | Identifier, label, quality/provenance field, or unapproved column; excluded from predictors. |
| timestamp_or_event_window | target / identifier / provenance / split metadata | False | Identifier, label, quality/provenance field, or unapproved column; excluded from predictors. |
| rainfall_total_mm | Phase 2B reconstructed event rainfall | True | Explicitly whitelisted feature group; see source/provenance fields. |
| rainfall_1h_mm | Phase 2B reconstructed event rainfall | True | Explicitly whitelisted feature group; see source/provenance fields. |
| rainfall_3h_mm | Phase 2B reconstructed event rainfall | True | Explicitly whitelisted feature group; see source/provenance fields. |
| rainfall_6h_mm | Phase 2B reconstructed event rainfall | True | Explicitly whitelisted feature group; see source/provenance fields. |
| rainfall_12h_mm | Phase 2B reconstructed event rainfall | True | Explicitly whitelisted feature group; see source/provenance fields. |
| rainfall_24h_mm | Phase 2B reconstructed event rainfall | True | Explicitly whitelisted feature group; see source/provenance fields. |
| peak_15min_mm | Phase 2B reconstructed event rainfall | True | Explicitly whitelisted feature group; see source/provenance fields. |
| peak_1h_mm | Phase 2B reconstructed event rainfall | True | Explicitly whitelisted feature group; see source/provenance fields. |
| swmm_nearest_node_depth_proxy_m | Phase 2B SWMM | True | Explicitly whitelisted feature group; see source/provenance fields. |
| swmm_node_flooding_m3 | Phase 2B SWMM | True | Explicitly whitelisted feature group; see source/provenance fields. |
| swmm_peak_conduit_flow_m3s | Phase 2B SWMM | True | Explicitly whitelisted feature group; see source/provenance fields. |
| swmm_peak_conduit_velocity_m_s | Phase 2B SWMM | True | Explicitly whitelisted feature group; see source/provenance fields. |
| swmm_subcatchment_runoff_mm | Phase 2B SWMM | True | Explicitly whitelisted feature group; see source/provenance fields. |
| swmm_surface_runoff_mm | Phase 2B SWMM | True | Explicitly whitelisted feature group; see source/provenance fields. |
| swmm_runoff_coefficient | target / identifier / provenance / split metadata | False | Identifier, label, quality/provenance field, or unapproved column; excluded from predictors. |
| physics_quality_status | target / identifier / provenance / split metadata | False | Identifier, label, quality/provenance field, or unapproved column; excluded from predictors. |
| hydraulic_validation_status | target / identifier / provenance / split metadata | False | Identifier, label, quality/provenance field, or unapproved column; excluded from predictors. |
| data_quality_status | target / identifier / provenance / split metadata | False | Identifier, label, quality/provenance field, or unapproved column; excluded from predictors. |
| rainfall_provenance | target / identifier / provenance / split metadata | False | Identifier, label, quality/provenance field, or unapproved column; excluded from predictors. |
| surface_provenance | target / identifier / provenance / split metadata | False | Identifier, label, quality/provenance field, or unapproved column; excluded from predictors. |
| swmm_provenance | target / identifier / provenance / split metadata | False | Identifier, label, quality/provenance field, or unapproved column; excluded from predictors. |
| hydraulic_coverage | target / identifier / provenance / split metadata | False | Identifier, label, quality/provenance field, or unapproved column; excluded from predictors. |
| mapping_classification | target / identifier / provenance / split metadata | False | Identifier, label, quality/provenance field, or unapproved column; excluded from predictors. |
| physics_coverage | target / identifier / provenance / split metadata | False | Identifier, label, quality/provenance field, or unapproved column; excluded from predictors. |
| scenario_id | target / identifier / provenance / split metadata | False | Identifier, label, quality/provenance field, or unapproved column; excluded from predictors. |
| swmm_model_version | target / identifier / provenance / split metadata | False | Identifier, label, quality/provenance field, or unapproved column; excluded from predictors. |
| feature_source | target / identifier / provenance / split metadata | False | Identifier, label, quality/provenance field, or unapproved column; excluded from predictors. |