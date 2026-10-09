# Ward L SWMM MVP Diagnostic

**Evidence reviewed:** saved `ward_L_kurla.inp`, `.rpt`, and `.out`; Ward L conduit, junction, and outfall CSVs; rainfall preparation code. No network regeneration or SWMM rerun was performed. The saved run is SWMM 5.2.4, completed 2026-10-09 06:27:33.

## Warning 04 Findings

The report contains 24 unique instances of the exact message `WARNING 04: minimum elevation drop used for Conduit <ID>`. Every listed link has identical upstream and downstream invert elevations in both the pilot CSV and the available derived engineering GeoJSON. Thus, CSV rounding did not create these flat pairs. The source-derived slope is 0 at the stored precision; the CSV `slope_m_per_m` field is `0.0001`, but the INP link offsets preserve the equal endpoint inverts, so the effective INP slope remains 0. SWMM reports that it used a minimum elevation drop. The source still does not establish whether these are genuinely level conduits or whether the engineering source itself contains rounded/incomplete survey values; no invert was changed to silence the warning.

`Ground THD` and `source max depth` below are attributes from the node CSVs, not observed flood levels. `CSV slope` is the exported field, which is clamped; `INP slope` is recomputed from the node elevations and conduit offsets actually written to the model.

| Link | US -> DS | Source inverts U/D (m THD) | Length (m) | Invert slope (m/m) | CSV slope (m/m) | INP slope (m/m) | Ground THD U/D (m) | Source max depth U/D (m) | Classification |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| C_26786 | 2176086301 -> 2176086201 | 25.273 / 25.273 | 30.0 | 0.000000 | 0.0001 | 0.000000 | 28.586 / 28.432 | 3.313 / 3.159 | Potential geometry/elevation issue (flat) |
| C_28143 | 2177092502 -> 2177092503 | 26.990 / 26.990 | 5.8 | 0.000000 | 0.0001 | 0.000000 | 30.672 / 29.841 | 3.682 / 2.851 | Potential geometry/elevation issue (flat) |
| C_28153 | 2177092602 -> 2177092603 | 26.994 / 26.994 | 8.1 | 0.000000 | 0.0001 | 0.000000 | 32.933 / 32.933 | 5.939 / 5.939 | Potential geometry/elevation issue (flat) |
| C_28207 | 2177095004 -> 2177095003 | 26.031 / 26.031 | 3.3 | 0.000000 | 0.0001 | 0.000000 | 36.134 / 36.134 | 10.103 / 10.103 | Potential geometry/elevation issue (flat) |
| C_28222 | 2177096801! -> 2177096802! | 26.133 / 26.133 | 2.1 | 0.000000 | 0.0001 | 0.000000 | 32.332 / 32.332 | 6.199 / 6.199 | Potential geometry/elevation issue (flat) |
| C_28223 | 2177096801 -> 2177096802 | 26.133 / 26.133 | 2.1 | 0.000000 | 0.0001 | 0.000000 | 32.332 / 32.332 | 6.199 / 6.199 | Potential geometry/elevation issue (flat) |
| C_28228 | 2177096804! -> 2177096805! | 26.129 / 26.129 | 8.7 | 0.000000 | 0.0001 | 0.000000 | 34.832 / 34.832 | 8.703 / 8.703 | Potential geometry/elevation issue (flat) |
| C_28229 | 2177096804 -> 2177096805 | 26.129 / 26.129 | 8.7 | 0.000000 | 0.0001 | 0.000000 | 34.832 / 34.832 | 8.703 / 8.703 | Potential geometry/elevation issue (flat) |
| C_28244 | 2177096907! -> 2177096801! | 26.133 / 26.133 | 5.0 | 0.000000 | 0.0001 | 0.000000 | 32.332 / 32.332 | 6.199 / 6.199 | Potential geometry/elevation issue (flat) |
| C_28245 | 2177096907 -> 2177096801 | 26.133 / 26.133 | 5.0 | 0.000000 | 0.0001 | 0.000000 | 32.332 / 32.332 | 6.199 / 6.199 | Potential geometry/elevation issue (flat) |
| C_28255 | 2177097603 -> 2177097604 | 26.101 / 26.101 | 5.4 | 0.000000 | 0.0001 | 0.000000 | 32.836 / 32.836 | 6.735 / 6.735 | Potential geometry/elevation issue (flat) |
| C_28276 | 2177098404 -> 2177098403 | 26.081 / 26.081 | 9.9 | 0.000000 | 0.0001 | 0.000000 | 32.324 / 32.324 | 6.243 / 6.243 | Potential geometry/elevation issue (flat) |
| C_28280 | 2177098501 -> 2177098405 | 26.082 / 26.082 | 7.1 | 0.000000 | 0.0001 | 0.000000 | 38.057 / 32.324 | 11.975 / 6.242 | Potential geometry/elevation issue (flat) |
| C_29131 | 2178092602! -> 2178092603! | 26.658 / 26.658 | 11.4 | 0.000000 | 0.0001 | 0.000000 | 30.440 / 30.440 | 3.782 / 3.782 | Potential geometry/elevation issue (flat) |
| C_29478 | 2178115901! -> 2178115902! | 35.500 / 35.500 | 7.9 | 0.000000 | 0.0001 | 0.000000 | 48.701 / 51.585 | 13.201 / 16.085 | Potential geometry/elevation issue (flat) |
| C_29479 | 2178115901 -> 2178115902 | 35.500 / 35.500 | 7.9 | 0.000000 | 0.0001 | 0.000000 | 48.701 / 51.585 | 13.201 / 16.085 | Potential geometry/elevation issue (flat) |
| C_29495 | 2178116901 -> 2178116902 | 35.800 / 35.800 | 5.6 | 0.000000 | 0.0001 | 0.000000 | 48.000 / 48.000 | 12.200 / 12.200 | Potential geometry/elevation issue (flat) |
| C_29536 | 2178125001! -> 2178125002! | 37.600 / 37.600 | 3.9 | 0.000000 | 0.0001 | 0.000000 | 46.178 / 46.178 | 8.578 / 8.578 | Potential geometry/elevation issue (flat) |
| C_29537 | 2178125001 -> 2178125002 | 37.600 / 37.600 | 3.9 | 0.000000 | 0.0001 | 0.000000 | 46.178 / 46.178 | 8.578 / 8.578 | Potential geometry/elevation issue (flat) |
| C_29548 | 2178125102! -> 2178125103! | 42.100 / 42.100 | 32.6 | 0.000000 | 0.0001 | 0.000000 | 49.205 / 51.536 | 7.105 / 9.436 | Potential geometry/elevation issue (flat) |
| C_29549 | 2178125102 -> 2178125103 | 42.100 / 42.100 | 32.6 | 0.000000 | 0.0001 | 0.000000 | 49.205 / 51.536 | 7.105 / 9.436 | Potential geometry/elevation issue (flat) |
| C_30068 | 2179104101 -> 2179104102 | 25.271 / 25.271 | 31.8 | 0.000000 | 0.0001 | 0.000000 | 34.149 / 33.102 | 8.878 / 7.831 | Potential geometry/elevation issue (flat) |
| C_30255 | 2179122602 -> 2179122603 | 49.707 / 49.707 | 12.4 | 0.000000 | 0.0001 | 0.000000 | 57.432 / 57.509 | 7.725 / 7.802 | Potential geometry/elevation issue (flat) |
| C_30284 | 2179123502 -> 2179123501 | 46.478 / 46.478 | 8.1 | 0.000000 | 0.0001 | 0.000000 | 55.508 / 55.508 | 9.030 / 9.030 | Potential geometry/elevation issue (flat) |

### Adverse Slopes Are Separate

Neither previously flagged adverse-slope conduit appears in the Warning 04 list:

| Link | US -> DS | Source inverts (m THD) | Length (m) | Source-derived slope (m/m) | CSV slope field (m/m) |
|---|---|---:|---:|---:|---:|
| C_28238 | 2177096904! -> 2177096903! | 24.980 -> 26.138 | 19.7 | -0.058782 | 0.0001 |
| C_29481 | 2178115902 -> 2178116901 | 35.500 -> 35.800 | 62.9 | -0.004769 | 0.0001 |

The source slope is derived from the endpoint inverts and length. The exported positive slope field is clamped and does not represent these uphill invert pairs. The INP offsets preserve the source elevations and direction. Their absence from Warning 04 means only that they are not the links named by this warning; it does not establish that their hydraulics are sound.

Six sets of warned conduits are exact duplicate geometries in the derived engineering GeoJSON, with identical length, shape, dimensions, inverts, and `Existing` status: `C_28222/C_28223`, `C_28228/C_28229`, `C_28244/C_28245`, `C_29478/C_29479`, `C_29536/C_29537`, and `C_29548/C_29549`. In each pair, one record uses `!`-suffixed node IDs; those IDs and their unsuffixed counterparts have identical exported coordinates and node elevations. Distinct GIS `OBJECTID`s exist, but no separate asset identifier or evidence establishes whether these are intentional parallel assets or duplicated digitization. The model includes both representations. Treat this as a potential source/topology duplication that can affect conveyance; do not deduplicate until the asset source is checked.

## Ponding and Extreme Depths

The INP sets `ALLOW_PONDING YES`. Every one of the 1,816 junction records has `Apond=100.0 m2`, `SurDepth=0`, and a source-derived `MaxDepth`; the source preparation code assigns the same 100 m2 to every junction with the stated intent of simulating street ponding. No per-node surface footprint or floodplain-area measurements support that uniform value. Under SWMM ponding behavior, once node depth exceeds `MaxDepth`, the assigned ponded area provides additional storage. It is therefore the explicit configuration that permits above-rim depth/storage; the 100 m2 value maps retained overflow volume into modeled ponded depth. The 636.459 ML in the Node Flooding Summary is accumulated node flooding/ponding volume, not the same quantity as routing-continuity `Flooding Loss` (0.000 because ponding is allowed and the water is retained rather than lost from the model).

At the worst routing-step node, `2177117804`, the source/INP values are invert 34.100 m THD, rim 43.459 m THD, and `MaxDepth=9.359 m`; the RPT maximum node depth is about 91.8 m at 14:21, with HGL about 125.9 m. The Node Flooding Summary reports maximum ponded depth 82.444 m there; `9.359 + 82.444` accounts for the approximately 91.8 m depth. The binary `.out` is sampled only every 15 minutes and peaks at 91.605 m at 14:30, so it does not capture the routing-step maximum. The depth above rim is thus directly explained by ponding storage under the fixed 100 m2 setting, not by an observed 82 m-deep street flood. Actual ponding area is unknown, so neither this depth nor the flood volume is physically validated.

Separately, the generated node `MaxDepth` values are based on DEM-sampled ground elevation plus the 27.432 m THD/MSL offset and an uncapped `ground - invert` difference. The pilot CSV has 490 junctions with `MaxDepth > 10 m`, 54 above 20 m, 12 above 30 m, and 2 above 40 m (maximum 49.382 m). Those are configured source values, not a consequence of ponding. They warrant checking DEM sampling, datum consistency, and node-to-drain association against surveyed rims before treating surcharge depths as physically realistic. The available evidence flags questionable magnitudes but cannot alone prove which node values are wrong.

## Saved Simulation Results

- **Run status:** SWMM 5.2.4 completed with 24 warnings and 0 SWMM errors. Runoff and routing continuity errors were -0.084% and -0.058%.
- **Duration/output:** the RPT run is 27 hours, 2005-07-26 00:00 through 2005-07-27 03:00, with a 5-second routing step and 15-minute report step. The `.out` has 108 periods from 00:15 through 03:00; it does not preserve every 5-second routing state. The final time coincides with the last rainfall interval, so no post-event drain-down period is simulated.
- **Rain/runoff:** 944.200 mm precipitation over the generated 27-hour window; 901.551 mm surface runoff; 40.012 mm infiltration. The binary series peaks at 276.284 mm/h system rainfall at 10:15 and 1,155.319 CMS system runoff at 10:45.
- **Flooding/ponding:** the report lists 208 flooded nodes and 636.459 ML total flooding volume. The largest Node Flooding Summary ponded depth is 84.403 m; the largest routing-step node depth is about 91.8 m. The binary depth series reaches 91.605 m at node `2177117804` at the 14:30 report sample. These are model outputs, not observed flood depths. The fixed 100 m2 ponded area explains the conversion of retained overflow into extreme modeled ponding depth; it does not validate the spatial extent or physical depth of flooding. The continuity summary's `Flooding Loss` is 0 because ponded water is retained in the model balance; it does not negate the Node Flooding Summary.
- **Surcharge/capacity:** 815 nodes appear in the Node Surcharge Summary; maximum height above crown is 90.303 m. The Conduit Surcharge Summary lists 938 conduits; 550 links have report `Max/Full Flow` above 1, with a maximum ratio of 30.7 on `C_29548`. Treat these as model stress indicators, not validated capacity exceedances; extreme ponding and flat-slope warnings affect interpretation.
- **Outfalls/end state:** the report's system row gives 13,481.564 ML total outfall volume and 987.341 CMS maximum system flow under the current boundaries. At the final binary-output time, system outfall flow is still 34.680 CMS, runoff is 13.754 CMS, and stored volume is about 191.9 ML. Routing continuity reports final storage 191.852 ML. The response has not drained down; total event outflow, stored/flooded volume, and surcharge duration are truncated by the 03:00 end time.

## Interpretation and Limitations

The Warning 04 cause is a zero endpoint-elevation drop in each named link, not the adverse slope of `C_28238` or `C_29481`. The equal elevations are present in the available source layer, but the true as-built drops remain unverified. Classify all 24 as **potential geometry/elevation issues; physical cause unresolved**. Do not reverse links or alter inverts without original engineering/survey evidence. The six exact-geometry pairs are an additional potential **source/topology duplication** issue, pending asset-level confirmation.

The extreme above-rim depths are demonstrably enabled by `ALLOW_PONDING YES` and the uniform `Apond=100 m2`; the specific predicted flooding volumes additionally depend on the storm hyetograph, network capacity, node elevations, and FREE outfalls. The event rainfall is severe and concentrated (431.7 mm in one reconstructed 3-hour block, with a 276.288 mm/h 15-minute-derived intensity peak), so large runoff is expected for this forcing. The saved run cannot distinguish how much of the modeled spatial flooding is realistic because its ponding area is unsupported, some `MaxDepth` values are very high, potential coincident duplicate assets remain, and the recession is cut off. These are demonstrated model assumptions plus unresolved geometry; they do not establish that rainfall alone explains the results.

All 43 outfalls use provisional `FREE` boundaries. No tide curve or observed tide data is applied; this omits coastal tailwater/backwater and can overstate discharge during high tide. Rainfall is one Santacruz series applied uniformly to all subcatchments. Its 15-minute depths are a static triangular disaggregation of observed 3-hour totals, not measured 15-minute observations; its timing and peak intensity are synthetic.

There is also an unresolved event-window mismatch: the event catalogue calls 944.2 mm a 24-hour total ending 03:00 UTC on 27 July, but the generator assigns the complete total to nine consecutive 3-hour blocks from 00:00 on 26 July through 03:00 on 27 July (27 hours). The model/event timestamps have no explicit timezone. Do not shift, drop, or compress an interval until the IMD table's time basis and interval-ending convention are reconciled. The current results therefore cannot be described simply as a simulation of the documented 24-hour rainfall window.

## Recommended Actions

1. Reconcile the 24-hour E001 rainfall window and timezone/interval convention with the source 3-hour observations. Use the same verified storm window for both models and retain the original hyetograph until that mapping is resolved.
2. Confirm whether the six coincident duplicate-geometry pairs are independent parallel assets or duplicate GIS records. Preserve both until the source owner confirms.
3. Verify the 24 flat links and DEM-derived rim/`MaxDepth` values (especially the 54 above 20 m) against survey, original profiles, and datum records. Change elevations only where those records support it.
4. Agree a surface-storage/overflow method from mapped/surveyed areas, or explicitly treat ponding as a shared sensitivity assumption. Do not use the current 100 m2 result as a physical flood-depth estimate.
5. For a controlled simulation comparison, harmonize conduit/node representation, rainfall values and timing, infiltration/roughness, outfall stage, ponding/max-depth settings, and simulation duration; include post-event drain-down and use the same reporting interval.
6. Compare capacity and surcharge only after the geometry review; validate against observed flood locations, water levels, and outfall flows before any accuracy claim.

No candidate INP was created: there is no evidence-based alternative ponded area, corrected invert, or adjudicated duplicate set yet, and the friend's assumptions are not available to define a fair comparison. The original INP and saved outputs were not changed or rerun.

## Readiness Verdict

- **Structural comparison:** Ready, with the 24 flat links, 6 exact-geometry conduit pairs, and 2 adverse-slope conduits explicitly flagged. Compare topology and object tables without assuming those records are verified assets.
- **Controlled simulation comparison:** Not ready. First reconcile the 24-hour/27-hour rainfall window and harmonize storage/ponding, node rim/depth, duplicate-asset, FREE/tide boundary, and drain-down assumptions. No model candidate or rerun is justified until those choices are supported and shared.
- **Flood accuracy against observed events:** Not ready. No collocated observed water levels, flood depths, timing, or outfall hydrographs were used to validate this run; SWMM completion and continuity closure are not calibration or hydraulic validation.

The model can support exploratory feature-pipeline/schema testing only if outputs remain labeled as unvalidated scenarios. Preserve synthetic rainfall provenance, FREE-boundary assumption, Warning 04 flags, storage/node-depth assumptions, potential duplicate assets, and the truncated recession with any extracted result.