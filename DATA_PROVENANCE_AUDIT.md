# TERRA05: Study-Area Data Provenance & Geospatial Audit
**System:** Mumbai Urban Stormwater Flood Prediction System  
**Auditor:** Senior Hydrologic & Geospatial Engineer  
**Date:** 2026-10-09  
**Reference Coordinate System:** EPSG:32643 (UTM Zone 43N, WGS84 Datum, Metric Units)  
**Geographic Domain:** Greater Mumbai Municipal Corporation (MCGM/BMC) Boundary & Mithi River Basin (Ward L Corridor)

---

## 1. Executive Summary of Spatial Assets

| Dataset | Primary Source | License / Access | Native CRS | Processed CRS | Native Resolution | Units | Total Records / Pixels | Missing / Null Values |
|---|---|---|---|---|---|---|---|---|
| **Digital Elevation Model (DEM)** | NASA SRTM v3.0 / ISRO CartoDEM | Open Access (NASA Open Data / ISRO Bhuvan) | EPSG:4326 | EPSG:32643 | 1 arc-second (~30m) | Metres MSL | 1384 × 727 (1,006,168 px) | 0 in Mumbai terrestrial boundary |
| **Topographic Slope** | Derived from SRTM/CartoDEM | Derived Product | EPSG:32643 | EPSG:32643 | 30.42m | Degrees (0° – 90°) | 1384 × 727 px | 0 in land area |
| **Land Cover (Imperviousness)** | ESA WorldCover 10m v200 | Creative Commons CC-BY 4.0 | EPSG:4326 | EPSG:32643 | 10m | Categorical / Built-up fraction (0.0 – 1.0) | 4610 × 2419 px | 0 |
| **Soil Physical Properties** | ISRIC SoilGrids v2.0 (0–5cm) | Creative Commons CC-BY 4.0 | EPSG:4326 | EPSG:32643 | 250m | % Clay, % Sand, % Silt, Class | 47,758 grid cells | 0 |
| **Hydrology & Flow Accumulation** | DEM D8 Routing Engine | Derived Hydrologic Product | EPSG:32643 | EPSG:32643 | 100m raster centroid | Cell count & Drainage Area ($km^2$) | 47,758 grid cells | 66 (water body centroids) |
| **Municipal Drainage Network** | BMC Stormwater Drainage Dept. (BRIMSTOWAD) | Municipal Open GIS / MCGM Portal | EPSG:4326 | EPSG:32643 | Polyline vectors | Length ($m$), inverts ($m$), diameter ($m$) | 1,438 conduits (Ward L), 30,000+ citywide | 0 after topological repair |
| **Rainfall Hyetographs** | IMD Santacruz / Colaba AWS & BMC Disasters | IMD Open Portal / BMC Disaster Management | N/A | N/A | 15-minute intervals | Depth ($mm$), Intensity ($mm/hr$) | 204 intervals across 9 scenarios | 0 |
| **Historical Flood Benchmark** | BMC Chronic Waterlogging Spots (2019–2023) | MCGM Disaster Management Dept. | EPSG:4326 | EPSG:32643 | Point ground observations | Binary presence, flood depth notes | 1,953 positive grid cells | 0 |

---

## 2. Detailed Dataset Profiles & Transformations

### 2.1 Digital Elevation Models (`dem_mumbai_utm43.tif` & `dem_isro_mumbai_utm43.tif`)
* **Source:** Shuttle Radar Topography Mission (SRTM 1 Arc-Second Global) and ISRO CartoDEM (Cartosat-1 stereo pairs `cdne43a`, `cdne43g`).
* **Datum & Projections:** Originally WGS84 geographic coordinates. Reprojected to UTM Zone 43N using bilinear resampling to preserve hydraulic slopes.
* **Pixel Spacing:** Exactly $30.416\text{ m} \times 30.416\text{ m}$.
* **Vertical Datum:** Orthometric height above Mean Sea Level (MSL), EGM96 geoid. Invert elevation records in BMC drainage are referenced to Town Hall Datum (THD), where $\text{MSL} = \text{THD} - 27.432\text{ m}$.
* **Transformations Applied:** Sinks and pits filled with Wang & Liu priority-flood algorithm to enforce continuous drainage toward outfalls.

### 2.2 Land Cover & Surface Imperviousness (`worldcover_mumbai_utm43.tif`)
* **Source:** European Space Agency (ESA) WorldCover 10m 2021 Product.
* **Classes:** Class 50 (Built-up / Impervious), Class 10 (Tree Cover), Class 20 (Shrubland), Class 30 (Grassland), Class 80 (Permanent Water Bodies), Class 95 (Mangroves).
* **Grid Cell Aggregation:** Inside each 100m computational cell ($10,000\text{ m}^2$), 100 WorldCover pixels are sampled. The impervious fraction $f_{\text{imp}}$ equals $\frac{\sum \text{Built-up Pixels}}{100}$.

### 2.3 Soil Hydrological Parameters (`soil_100m.csv`)
* **Source:** ISRIC World Soil Information (SoilGrids 250m v2.0) at 0–5 cm depth.
* **Observed Soil Types across Mumbai:**
  * **Loam:** 39,608 cells (82.9%) — Sand ~42%, Silt ~38%, Clay ~20%.
  * **Clay Loam:** 8,150 cells (17.1%) — Heavy coastal alluvium adjoining Mithi River, Mahim Creek, and Thane Creek.
* **Hydrologic Soil Group (HSG):** Group B (Loam) and Group C/D (Clay Loam).
* **Derived Infiltration Capacity (Horton Model):**
  * Group B (Loam): Initial $f_0 = 50.0\text{ mm/hr}$, saturated $f_c = 5.0\text{ mm/hr}$, decay $k = 3.0\text{ hr}^{-1}$.
  * Group C/D (Clay Loam): Initial $f_0 = 30.0\text{ mm/hr}$, saturated $f_c = 2.5\text{ mm/hr}$, decay $k = 3.5\text{ hr}^{-1}$.

### 2.4 Rainfall Scenario Catalogue (`swmm_rainfall_catalog.csv`)
* **15-Minute Reconstructed Extreme:**
  * `TS_2005_JULY26`: 108 records (27.0 hours), 944.2 mm total storm depth, peak intensity 276.3 mm/hr.
  * *Scientific Disclaimer:* Reconstructed via synthetic temporal disaggregation of 3-hour autographic chart records from IMD Santacruz observatory; 15-minute sub-hourly fluctuations are model approximations.
* **Synthetic Design Scenarios (Peak-Intensity):**
  * `DESIGN_YELLOW_25MM`: Peak 25.0 mm/hr, 3-hour total 18.75 mm.
  * `DESIGN_ORANGE_50MM`: Peak 50.0 mm/hr, 3-hour total 37.50 mm.
  * `DESIGN_RED_100MM`: Peak 100.0 mm/hr, 3-hour total 75.00 mm.
  * `DESIGN_CLOUDBURST_150MM`: Peak 150.0 mm/hr, 3-hour total 112.50 mm.
* **Synthetic Design Scenarios (Total-Depth):**
  * `DEPTH_25MM_3H`, `DEPTH_50MM_3H`, `DEPTH_100MM_3H`, `DEPTH_150MM_3H`.

---

## 3. Computational Grid Justification

The $100\text{ m} \times 100\text{ m}$ regular lattice ($1.0\text{ ha}$ per cell) was audited for suitability:
1. **Computational Feasibility:** Citywide Mumbai consists of 47,758 cells; Ward L (Mithi corridor) consists of 1,516 cells. A 100m resolution allows sub-second 2D overland routing across 12 to 48 timesteps without memory overflow or numerical divergence in web environments.
2. **Data Concordance:** Matches the cell resolution of municipal flood reporting spots and building density aggregation.
3. **Preservation:** The 100m grid is preserved intact to ensure consistency across the Random Forest susceptibility model, risk map layers, and hydrodynamic routing.
