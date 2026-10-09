# SWMM Phase 1 Assumptions

- Manning roughness is ASSUMED by shape: closed/arch 0.016, circular 0.013, open rectangular 0.025.
- OREC is interpreted as RECT_OPEN (ASSUMED); all other shape labels are mapped to analogous SWMM shapes.
- Horton rates: 50 mm/h maximum, 5 mm/h minimum, 3 1/h decay, 7 day drying time (ASSUMED MVP values).
- Subcatchment roughness: 0.015 impervious, 0.20 pervious; depression storage 2/5 mm (ASSUMED).
- Built-up fraction is a land-cover imperviousness proxy, not a measured impervious surface fraction.
- Where DEM-derived cover is less than the largest connected conduit height + 0.3 m, SWMM node rim depth is explicitly assumed at that minimum; source DEM values remain recorded.
- Directed graph sinks are FREE pilot boundaries for execution only. They are not verified BMC outfalls or receiving-water boundaries.
- The 15-minute 26 July 2005 profile is reconstructed from coarse totals; tide is disabled; the model is uncalibrated.
