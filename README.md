# Mumbai Urban Stormwater Flood Prediction — Data Package

## Supplied BMC data audited

### 1. BMC flooding spots
- Original features: 937
- Records marked `Delete`: 602
- Active records before deduplication: 335
- Duplicate active records by FEATUREID: 2
- Clean working features: 333

**Use:** flood labels / historical validation.

**Important:** Do NOT train on the deleted records. The cleaned file removes records whose NAME contains "Delete".

### 2. BMC storm-water drains
- Features: 34711
- Geometry: line network
- Useful fields include conduit length, width, height and invert elevations.

**Use:** derive:
- distance_to_drain
- drain_density
- drain_capacity_proxy

The capacity value is only a proxy, not a hydraulic capacity calculation.

---

# Recommended model features

1. elevation
2. slope
3. built_up_fraction
4. vegetation_fraction
5. distance_to_water
6. distance_to_drain
7. drain_density
8. drain_capacity_proxy
9. building_density
10. rainfall_1h
11. rainfall_3h
12. rainfall_24h
13. tide_condition

## Avoid data leakage

The following BMC flood attributes should be treated as impact/validation information rather than direct ML predictors:

- AFFECT_POPULATION
- AFFECT_ROAD
- AFFECT_RAIL
- AFFECTED_HUT
- NO_DE_WATER_PUMP

---

# Additional data to import

## MUST HAVE
- Mumbai boundary / ward polygons — BMC GIS
- DEM — NASA SRTM/NASADEM
- Land cover — ESA WorldCover
- Water bodies / hydro lines / coast — BMC GIS
- Rainfall — IMD

## HIGH PRIORITY
- Buildings — BMC GIS
- Roads — BMC GIS or OpenStreetMap
- Population — Census / WorldPop

## MEDIUM
- Tide — INCOIS
- Hospitals — BMC GIS
- Police — BMC GIS
- Fire stations — BMC GIS
- Shelters — BMC GIS
- Vulnerable settlements — BMC GIS

## BONUS
- Sentinel-1 historical flood mask — Copernicus / Google Earth Engine

---

# Suggested data flow

BMC flood spots + terrain + land cover + drainage + rainfall
→ Random Forest flood susceptibility/risk
→ uncertainty
→ flood-risk map

Then:

flood-risk map + population/buildings/roads/hospitals/etc.
→ exposure/impact analysis

Sentinel-1 should preferably be used for independent historical validation.

---

# Directory structure

data/
├── raw/
│   ├── flooding_spots.geojson
│   └── storm_water_drains.geojson
└── processed/
    ├── bmc_flooding_spots_clean.geojson
    └── bmc_storm_water_drains_working.geojson

DATA_MANIFEST.json
README.md


# External download plan

## BMC GIS

Official BMC ArcGIS REST service:

https://prsrvgisapp.mcgm.gov.in/server/rest/services/mcgm/MCGMGIS_Departments_Master_All_Layers/MapServer

Confirmed useful layer IDs:

- 238 Wards
- 281 Landuse
- 283 Building
- 284 Railway Lines
- 286 Hydro Line
- 156 Road Centerline
- 450 Bridges
- 213 Fire Stations
- 214 Hospitals
- 221 Police Stations
- 232 Temporary Shelters
- 346 Vulnerable Settlements
- 345 Flow Level Sensor
- 217 Mumbai Contour
- 237 Disaster Management Wards

The BMC service supports GeoJSON queries and has a 1000-record page size, so `download_bmc_layers.py` paginates automatically.

## ESA WorldCover

WorldCover 2021 v200 is a global 10 m land-cover product. Mumbai is covered by the N18E072 3x3-degree tile.

Public source:
https://esa-worldcover.org/en/data-access

## DEM

For the prototype, the download script uses public SRTM 1-arc-second tiles for:
N18E072, N18E073, N19E072, N19E073.

For a formal paper, cite/use NASA SRTMGL1 or another authoritative DEM distribution.

## IMD rainfall

Official IMD API documentation:
https://mausam.imd.gov.in/imd_latest/contents/api.pdf

Useful public rainfall endpoint documented by IMD:
https://mausam.imd.gov.in/api/districtwise_rainfall_api.php

For the hackathon model, rainfall can initially be supplied as scenario values (1h/3h/24h), then connected to IMD.

## Important modeling rule

Do not use BMC flood-impact fields such as affected population, affected roads, affected rail, etc. as predictors. They are better reserved for impact/exposure analysis to avoid leakage.

## Current computed data

The existing BMC files have already been:
- cleaned
- projected to EPSG:32643
- converted into a 100 m grid
- labeled using active BMC flood spots
- assigned nearest-drain distance
- assigned exact drain length/density per cell

See:
`data/derived/`
