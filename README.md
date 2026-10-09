# TERRA05 — Mumbai Urban Stormwater Flood Prediction & Hydraulic Digital Twin

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8+-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![MapLibre GL](https://img.shields.io/badge/MapLibre_GL-5.1+-396EB0.svg?logo=maplibre&logoColor=white)](https://maplibre.org)
[![PySWMM](https://img.shields.io/badge/PySWMM-2.2.0-blue.svg)](https://pyswmm.org)
[![EPA-SWMM](https://img.shields.io/badge/EPA--SWMM-5.2.4-darkgreen.svg)](https://www.epa.gov/water-research/storm-water-management-model-swmm)
[![Tests](https://img.shields.io/badge/Tests-27%2F27%20Passing-brightgreen.svg)]()

> **TERRA05** is an end-to-end, physics-informed urban stormwater flood prediction and decision-support platform engineered for Mumbai. It couples a **2D numerical surface runoff and overland accumulation engine**, an **EPA-SWMM 5.2.4 subterranean drainage pipe adapter**, an **uncalibrated historical Random Forest susceptibility baseline**, and a high-performance **MapLibre 3D Digital Twin** frontend.

---

## Table of Contents

1. [Executive Architecture](#executive-architecture)
2. [Complete Tech Stack](#complete-tech-stack)
3. [Repository Directory Structure](#repository-directory-structure)
4. [Quickstart & Developer Setup Guide](#quickstart--developer-setup-guide)
   - [Backend Environment Setup](#1-backend-setup)
   - [Frontend Environment Setup](#2-frontend-setup)
   - [Running the Application](#3-running-the-full-stack-application)
   - [Running Automated Tests](#4-running-the-automated-test-suite)
5. [Hydrologic & Hydraulic Simulation Engine Details](#hydrologic--hydraulic-simulation-engine-details)
   - [Physics & Water Balance Formulations](#physics--water-balance-formulations)
   - [EPA-SWMM Engine & Synthetic Benchmark](#epa-swmm-engine--synthetic-benchmark)
   - [Separation: Hydraulic Depths vs ML Susceptibility](#separation-hydraulic-depths-vs-ml-susceptibility)
6. [API Endpoints Reference](#api-endpoints-reference)
7. [Data Sources & Provenance](#data-sources--provenance)
8. [Colleague Onboarding & Next Steps](#colleague-onboarding--next-steps)

---

## Executive Architecture

```
[ Rainfall Catalogue / IMD Alert Scenarios ]
                      │
                      ▼
     ┌──────────────────────────────────┐
     │ 2D Surface Runoff Engine         │ ◄─── DEM Elevation & Slope (EPSG:32643)
     │ • Horton Infiltration (SoilGrids)│ ◄─── ESA WorldCover Imperviousness
     │ • Depression Storage Abstraction │ ◄─── Municipal Conduit Densities
     │ • 2D Courant Diffusive Routing   │
     │ • Strict Mass Balance (0.0000%)  │
     └──────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
┌───────────────┐           ┌─────────────────────────────┐
│ FastAPI       │           │ PySWMM 2.2.0 Adapter        │
│ REST API      │           │ • EPA-SWMM 5.2.4 Core       │
│ (Port 8000)   │           │ • Junction Head & Surcharge │
└───────┬───────┘           │ • Conduit Hydrodynamics     │
        │                   │ • Benchmark Catchment       │
        ▼                   └─────────────────────────────┘
┌───────────────────────────────────┐
│ MapLibre GL 3D Digital Twin       │
│ • OpenFreeMap Vector Basemaps     │
│ • Dynamic Flood Depth (0.05 - 2m+)│
│ • 15-Minute Playback Scrubber     │
│ • Ward L / Mithi Corridor Focus   │
└───────────────────────────────────┘
```

---

## Complete Tech Stack

### 1. Frontend (`frontend/`)
* **Framework**: React 18.3 + TypeScript 5.8
* **Bundler & Build Tool**: Vite 6.4 (ESM native, HMR)
* **Map & Geospatial Visuals**: MapLibre GL JS v5.1.0 + OpenFreeMap (`https://tiles.openfreemap.org/styles/liberty`)
  * *Zero external proprietary token dependency (eliminates Mapbox token exhaustion & grey-out bugs).*
* **Coordinate Projection**: `proj4` (real-time reprojection between EPSG:32643 UTM 43N and EPSG:4326 WGS84)
* **Styling & UI**: TailwindCSS 3.4, Lucide React icons, Canvas-based rainfall particle effects
* **Testing & Linting**: Oxlint, TypeScript strict mode (`tsc -b`)

### 2. Backend & Services (`backend/`)
* **API Framework**: FastAPI 0.115+, Starlette, Pydantic v2 (Strict Schema validation & OpenAPI 3.1)
* **ASGI Server**: Uvicorn 0.34
* **Numerical & Hydrologic Computing**: NumPy 2.2+, SciPy, Pandas 2.2+
* **Subterranean Hydraulics**: `pyswmm` 2.2.0 + `swmm-toolkit` 0.17.0 (EPA-SWMM C-kernel v5.2.4)
* **Geospatial Processing**: GeoPandas, Shapely 2.2+, PyProj 3.7+, Tifffile
* **Machine Learning**: Scikit-Learn 1.9 (Random Forest Classifier for baseline spatial susceptibility)

---

## Repository Directory Structure

```
Hackathon-TERRA05/
├── backend/
│   ├── config.py                 # Environment settings & data path resolution
│   ├── data_pipeline.py          # Soil Horton parameter derivation & D8 flow routing
│   ├── main.py                   # FastAPI routing, middleware, and API endpoints
│   ├── schemas.py                # Pydantic v2 input/output schemas & validations
│   ├── services.py               # Singleton data service (features, scenarios, risk map)
│   ├── simulation.py             # 2D vectorized surface runoff & water balance engine
│   └── swmm_adapter.py           # PySWMM / EPA-SWMM 5.2.4 modular execution adapter
├── frontend/
│   ├── index.html                # Single-page application entrypoint
│   ├── package.json              # NPM dependencies & build scripts
│   ├── vite.config.ts            # Vite bundler configuration
│   ├── tsconfig.json             # TypeScript root compiler configuration
│   ├── src/
│   │   ├── App.tsx               # Root application shell & scenario lifecycle
│   │   ├── components/
│   │   │   ├── MapboxMumbai.tsx  # MapLibre GL 3D map canvas & flood layer rendering
│   │   │   ├── IntelligencePanel.tsx # Live telemetry, water balance & stats
│   │   │   └── ArchitectureView.tsx  # Technical architecture specifications
│   │   ├── services/
│   │   │   └── api.ts            # Centralized API client & GeoJSON transformers
│   │   └── types/                # Domain types & interfaces
│   └── public/                   # Static icons & brand assets
├── data/
│   ├── raw/                      # BMC cadastral geojsons, ISRO CartoDEM, WorldCover
│   ├── processed/                # flood_grid_100m.geojson, soil_100m.csv, hydrology_100m.csv
│   ├── ml_ready/                 # ml_master_spatial_features.csv (47,758 cells)
│   ├── swmm_models/
│   │   └── sample_benchmark.inp  # Validated synthetic EPA-SWMM benchmark model
│   └── swmm_ready/
│       ├── swmm_rainfall_catalog.csv  # 9 scenarios, 204 discretized 15-min intervals
│       └── swmm_rainfall_metadata.json
├── outputs/
│   └── models/
│       └── ward_flood_susceptibility_rf_tuned.joblib # Compressed spatial ML artifact (28MB)
├── scripts/                      # Data auditing & offline feature pipeline scripts
├── tests/
│   ├── test_backend.py           # FastAPI endpoints, pagination, 404/422 handling
│   ├── test_simulation.py        # Hydrologic water balance, bucket test, 2D routing
│   ├── test_swmm.py              # PySWMM execution, continuity error verification
│   └── test_rainfall_scenarios.py# Hyetograph sanity checks
├── DATA_PROVENANCE_AUDIT.md      # Authoritative datum & raster provenance documentation
└── README.md                     # Master project documentation
```

---

## Quickstart & Developer Setup Guide

### 1. Prerequisites
* **Operating System**: Windows 10/11, Linux (Ubuntu 22.04+), or macOS
* **Python**: `3.11.x` recommended (compatible with precompiled `pyswmm` wheels)
* **Node.js**: `v18.x` or `v20.x` LTS + `npm`

---

### 2. Backend Setup

```bash
# 1. Open a terminal in the Hackathon-TERRA05 repository root
cd Hackathon-TERRA05

# 2. Create and activate a Python virtual environment
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# 3. Upgrade pip and install backend dependencies
pip install --upgrade pip
pip install fastapi uvicorn pydantic numpy scipy pandas scikit-learn==1.9.1 joblib shapely pyproj tifffile pyswmm swmm-toolkit httpx
```

To verify that PySWMM and EPA-SWMM are operational:
```bash
python -c "import pyswmm; from pyswmm import Simulation; print('PySWMM operational!')"
```

---

### 3. Frontend Setup

```bash
# 1. Navigate to the frontend directory
cd frontend

# 2. Install NPM dependencies
npm install

# 3. Verify the TypeScript build passes
npm run build
```

---

### 4. Running the Full-Stack Application

Run both processes in separate terminal windows:

#### Terminal 1 — Backend API
```bash
cd Hackathon-TERRA05
.venv\Scripts\Activate.ps1  # or source .venv/bin/activate
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
*API Swagger Documentation will be available at:* `http://127.0.0.1:8000/docs`

#### Terminal 2 — Frontend Application
```bash
cd Hackathon-TERRA05/frontend
npm run dev
```
*Frontend Application will be available at:* `http://localhost:5173`

---

### 5. Running the Automated Test Suite

The test suite validates unit conversions, hydrologic mass conservation, downhill routing, PySWMM execution, and all FastAPI endpoints:

```bash
cd Hackathon-TERRA05
python -m unittest discover tests
```

Expected output:
```
Ran 27 tests in ~3.5s
OK
```

---

## Hydrologic & Hydraulic Simulation Engine Details

### 1. Physics & Water Balance Formulations

For every cell $i$ with plan area $A = 10,000\,\text{m}^2$ ($100\,\text{m} \times 100\,\text{m} = 1.0\,\text{ha}$) and timestep $\Delta t = 15\,\text{min} = 0.25\,\text{hr}$:

1. **Precipitation Volume Ingestion**:
   $$P_{\text{vol}, i} = \left(\frac{P_t}{1000}\right) \times A$$

2. **Cell-Specific Horton Infiltration**:
   $$f_i(t) = f_{c, i} + \left(f_{0, i} - f_{c, i}\right) e^{-k_i t}$$
   Soil textures are dynamically assigned from SoilGrids clay fractions ($f_0 \in [30, 90]\,\text{mm/hr}$, $f_c \in [3.5, 12]\,\text{mm/hr}$, $k \in [1.8, 2.2]\,\text{hr}^{-1}$).
   Infiltration is restricted to pervious surfaces: $(1 - \text{built\_up\_fraction}_i)$.

3. **Depression Storage Initial Abstraction**:
   * Impervious depression storage: $2.0\,\text{mm}$
   * Pervious depression storage: $5.0\,\text{mm}$
   * Overland ponding initiates only once depression storage is fully satisfied.

4. **Municipal Conduit Drainage Abstraction**:
   Base capacity $C_{\text{drain}} = 25.0\,\text{mm/hr}$ scaled by conduit density:
   $$Q_{\text{drain}, i} = \min\left(d_i, \frac{C_{\text{drain}} \cdot \Delta t}{1000} \cdot \text{scale}_i\right)$$

5. **2D Terrain-Gradient Diffusive Routing**:
   Water surface hydraulic head $H_i = z_i + d_i$. Flux between adjacent cells $(i, j)$ flows along steepest hydraulic head gradient:
   $$\Delta H = H_i - H_j$$
   $$\text{Flux}_{i \to j} = \min\left(d_i,\, 0.45 \cdot \Delta H\right) \times \text{CFL}_{\text{limiter}}$$
   where $\text{CFL}_{\text{limiter}} = 0.08$ guarantees numerical stability across the grid.

6. **Strict Domain Water Balance Verification**:
   $$\sum P_{\text{vol}} = \sum \text{Infiltration}_{\text{vol}} + \sum \text{Depression}_{\text{vol}} + \sum \text{Drainage}_{\text{vol}} + \sum \text{SurfaceStorage}(t)$$
   Verified at every 15-minute step with error $\le 0.0001\%$.

---

### 2. EPA-SWMM Engine & Synthetic Benchmark

* The system contains a native EPA-SWMM 5.2.4 adapter (`backend/swmm_adapter.py`).
* An automated synthetic benchmark model (`data/swmm_models/sample_benchmark.inp`) is included to verify PySWMM execution, link flow hydrographs, junction depths, and continuity errors ($< 0.01\%$).
* **Honest Engineering Disclosure**: Real Mumbai municipal `.inp` model execution is labeled as `operational_benchmark_only` because calibrated subterranean physical pipe network parameters (pipe invert levels in Town Hall Datum vs MSL, Manning's $n$, and Arabian Sea tidal stage hydrographs) are pending municipal field calibration.

---

### 3. Separation: Hydraulic Depths vs ML Susceptibility

* **Hydraulic Simulation Output**: Physical water depth ($0.05\,\text{m} - 2.5\,\text{m}+$), ponded storage volume ($\text{m}^3$), and inundated area ($\text{km}^2$) calculated directly from rainfall hyetographs and terrain physics.
* **Random Forest ML Output**: An **uncalibrated historical susceptibility score** ($0.0 - 1.0$) indicating static long-term predisposition based on 2005 flood label overlap. It does **not** represent an event depth or probability and is decoupled from the simulation.

---

## API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Healthcheck and component availability matrix |
| `GET` | `/api/v1/system-status` | Readiness of API, ML model, rainfall catalogue, and SWMM engine |
| `GET` | `/api/v1/scenarios` | Lists 9 validated rainfall hyetograph scenarios (204 timesteps) |
| `POST` | `/api/v1/simulation/run` | Executes 2D hydrologic simulation for a given scenario and ward |
| `GET` | `/api/v1/swmm/status` | Reports PySWMM engine version, benchmark model status, and disclosures |
| `POST` | `/api/v1/swmm/sample-run` | Executes the EPA-SWMM benchmark model and returns link/node hydrographs |
| `GET` | `/api/v1/risk-map` | Paginated GeoJSON risk grid with optional bounding box and ward filters |
| `POST` | `/api/v1/predict` | Computes historical ML susceptibility score for a given `grid_id` or coordinates |

---

## Data Sources & Provenance

* **Terrain DEM**: ISRO CartoDEM (30m) & SRTM, reprojected to UTM Zone 43N (EPSG:32643).
* **Land Cover**: ESA WorldCover (10m) 2021 global product.
* **Soils**: ISRIC SoilGrids 250m clay, silt, and sand fractions.
* **Drainage Network**: BMC Brihanmumbai Municipal Corporation open SWD GIS layers.
* **Vertical Datum**: Mean Sea Level (MSL), converted from Mumbai Town Hall Datum (THD) via $\text{MSL} = \text{THD} - 27.432\,\text{m}$.
* *Full audit documented in `DATA_PROVENANCE_AUDIT.md`.*

---

## Colleague Onboarding & Next Steps

If you are joining this repository to continue development, here are the immediate recommended priorities:

1. **Hydraulic Pumping Intervention Scenarios**:
   * Add a parameter to `/api/v1/simulation/run` for mobile de-watering pump suction (e.g. $+5,000\,\text{m}^3/\text{hr}$ at specific `grid_id` cells like Kurla or Kalina).
   * Render pump icons on the MapLibre frontend and show localized drawdown in the dynamic depth layer.
2. **Pilot Ward L SWMM Network Calibration**:
   * Use the tabular conduit CSVs in `data/swmm_ready/pilot_ward_L/` to construct a ward-scale `.inp` model and link it into `backend/swmm_adapter.py`.
3. **Automated Situation Report Export**:
   * Implement an endpoint (`/api/v1/report/export`) that compiles peak inundated area, affected railway/road assets, and water balance summaries into a downloadable PDF/GeoJSON report for disaster response authorities.
