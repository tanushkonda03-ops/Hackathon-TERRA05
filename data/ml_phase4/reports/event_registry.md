# Phase 4 Historical Event Registry

| Event | Rainfall evidence | Spatial target match | Eligibility | SWMM status |
|---|---|---|---|---|
| E001 | nine verified 3-hour intervals; 15-minute profile is reconstructed | event/date match not established; flood_fraction and flood_label retained as Phase 3 supplied target | INSUFFICIENT_PROVENANCE | SUITABLE_FOR_REPLAY; baseline 2005 run already exists |
| E002 | partial bulletin values: 106 mm/24h plus 63 mm/3h; timing overlap/window requires resolution | event/date match not established; flood_fraction and flood_label retained as Phase 3 supplied target | RAIN_ONLY | NOT_RUN; insufficiently defined temporal profile |
| E003 | event named but station/date rainfall values pending | event/date match not established; flood_fraction and flood_label retained as Phase 3 supplied target | INSUFFICIENT_RAINFALL | NOT_RUN; no quantitative hyetograph |
| E004 | event named but station/date rainfall values pending | event/date match not established; flood_fraction and flood_label retained as Phase 3 supplied target | INSUFFICIENT_RAINFALL | NOT_RUN; no quantitative hyetograph |
| E005 | specific rainfall period and flood match not verified | event/date match not established; flood_fraction and flood_label retained as Phase 3 supplied target | INSUFFICIENT_PROVENANCE | NOT_RUN |

The flood target source documents BMC flooding spots from 2019–2023; the supplied grid itself has no event/date field and cannot be independently matched to E001. Target type therefore remains `supplied_historical_waterlogging_label`. No events qualify for Phase 4 event-held-out supervised training or evaluation. Historical E001 replay remains available with reconstructed 15-minute rainfall explicitly identified. E002 is partial rainfall-only; E003/E004 lack verified rainfall amounts; E005 remains a candidate. No external live rainfall provider is configured.
