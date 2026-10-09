"""FastAPI adapter for the persisted TERRA05 susceptibility model and local data."""

from __future__ import annotations

import csv
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

from scripts.static_flood_inference import DEFAULT_ARTIFACT_PATH, FEATURES, StaticFloodPredictor


ROOT = Path(__file__).resolve().parents[1]
ML_DATASET = ROOT / "data" / "ml_ready" / "ml_master_spatial_features.csv"
GRID_GEOJSON = ROOT / "data" / "processed" / "flood_grid_100m.geojson"
RAINFALL_CATALOG = ROOT / "data" / "swmm_ready" / "swmm_rainfall_catalog.csv"
DRAINAGE_GEOJSON = ROOT / "data" / "processed" / "bmc_storm_water_drains_working.geojson"
MODEL_VERSION = DEFAULT_ARTIFACT_PATH.name
MODEL_LIMITATIONS = [
    "Historical mapped-flood susceptibility only; not event-specific forecasting.",
    "Unlabelled grid cells are not confirmed non-flood locations.",
    "The score is not a calibrated flood probability.",
    "The current classifier does not simulate rainfall, tides, water depth, or SWMM hydraulics.",
]


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grid_id: int | None = Field(default=None, ge=0)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def validate_location(self):
        has_grid_id = self.grid_id is not None
        has_coordinates = self.latitude is not None and self.longitude is not None
        partial_coordinates = (self.latitude is None) != (self.longitude is None)
        if partial_coordinates or has_grid_id == has_coordinates:
            raise ValueError("Provide either grid_id or both latitude and longitude")
        return self


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    scenario_id: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        predictor = StaticFloodPredictor()
        if not ML_DATASET.is_file() or not GRID_GEOJSON.is_file():
            raise FileNotFoundError("ML dataset or processed grid GeoJSON is missing")

        rows_by_id: dict[int, dict[str, Any]] = {}
        with ML_DATASET.open(newline="", encoding="utf-8-sig") as file:
            for row in csv.DictReader(file):
                grid_id = int(row["grid_id"])
                rows_by_id[grid_id] = {
                    feature: (float(row[feature]) if row.get(feature, "") not in (None, "") else None)
                    for feature in FEATURES
                }
                rows_by_id[grid_id]["ward"] = row.get("ward") or None

        grid_document = json.loads(GRID_GEOJSON.read_text(encoding="utf-8"))
        grid_entries = []
        shapes = []
        grid_ids = []
        for feature in grid_document.get("features", []):
            properties = feature.get("properties", {})
            grid_id = int(properties["grid_id"])
            if grid_id not in rows_by_id:
                continue
            geometry = shape(feature["geometry"])
            grid_entries.append({
                "grid_id": grid_id,
                "properties": properties,
                "geometry": feature["geometry"],
                "bounds": geometry.bounds,
            })
            shapes.append(geometry)
            grid_ids.append(grid_id)
        if not grid_entries:
            raise ValueError("No matching ML rows and grid geometries were found")

        app.state.resources = {
            "predictor": predictor,
            "rows_by_id": rows_by_id,
            "grid_entries": grid_entries,
            "grid_tree": STRtree(shapes),
            "grid_ids": grid_ids,
            "transformer": Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True),
            "grid_crs": "EPSG:32643",
            "grid_count": len(grid_entries),
            "grid_source": GRID_GEOJSON,
        }
        app.state.startup_error = None
    except Exception as exc:
        app.state.resources = None
        app.state.startup_error = f"{type(exc).__name__}: {exc}"
    yield
    app.state.resources = None


app = FastAPI(
    title="TERRA05 Flood Susceptibility API",
    version="1.0.0",
    description="Historical mapped-flood susceptibility inference and local spatial data. This service does not simulate rainfall or hydraulics.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)


def _resources(request: Request) -> dict:
    resources = getattr(request.app.state, "resources", None)
    if resources is None:
        detail = getattr(request.app.state, "startup_error", None) or "Model resources are unavailable"
        raise HTTPException(status_code=503, detail=detail)
    return resources


def _prediction_response(resources: dict, grid_id: int) -> dict:
    row = resources["rows_by_id"].get(grid_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"grid_id {grid_id} is not present in the ML dataset")
    try:
        result = resources["predictor"].predict({feature: row[feature] for feature in FEATURES})
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "grid_id": grid_id,
        "ward": row.get("ward"),
        "susceptibility_score": result["model_score"],
        "predicted_class": result["predicted_class_at_selected_development_threshold"],
        "decision_threshold": result["decision_threshold"],
        "model": "LogisticRegression C=0.1",
        "model_version": MODEL_VERSION,
        "score_semantics": result["score_interpretation"],
        "limitations": MODEL_LIMITATIONS,
    }


@app.get("/health")
def health(request: Request) -> dict:
    resources = getattr(request.app.state, "resources", None)
    system = _system_status(request)
    return {"status": "degraded" if not resources or not system["swmm_model"]["ready"] else "ok", "components": system}


def _system_status(request: Request) -> dict:
    resources = getattr(request.app.state, "resources", None)
    startup_error = getattr(request.app.state, "startup_error", None)
    model_ready = resources is not None
    return {
        "api": "TERRA05 FastAPI backend",
        "model": {
            "ready": model_ready,
            "path": str(DEFAULT_ARTIFACT_PATH.relative_to(ROOT)),
            "detail": "Logistic Regression C=0.1 historical susceptibility model loaded." if model_ready else startup_error,
        },
        "rainfall_catalogue": {
            "ready": RAINFALL_CATALOG.is_file(),
            "path": str(RAINFALL_CATALOG.relative_to(ROOT)),
            "detail": "Local 15-minute rainfall catalogue is available; historical series are reconstructions, not independent verification." if RAINFALL_CATALOG.is_file() else "Local rainfall catalogue is missing.",
        },
        "geospatial_data": {
            "ready": model_ready,
            "path": str(GRID_GEOJSON.relative_to(ROOT)),
            "detail": f"{resources['grid_count']} 100 m cells available in EPSG:32643." if resources else "Grid/model data could not be loaded.",
        },
        "swmm_model": {
            "ready": False,
            "path": None,
            "detail": "No HTTP hydrodynamic simulation endpoint is provided by the susceptibility classifier; /api/v1/simulation/run returns 501.",
        },
    }


@app.get("/api/v1/system-status")
def system_status(request: Request) -> dict:
    return _system_status(request)


@app.get("/api/v1/scenarios")
def scenarios() -> list[dict]:
    if not RAINFALL_CATALOG.is_file():
        raise HTTPException(status_code=503, detail="Local rainfall catalogue is unavailable")
    grouped: dict[str, list[dict]] = {}
    with RAINFALL_CATALOG.open(newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            grouped.setdefault(row["timeseries_id"], []).append(row)

    output = []
    for series_id, rows in grouped.items():
        values = [float(row["rainfall_15min_mm"]) for row in rows]
        intensities = [float(row["intensity_mm_per_hr"]) for row in rows]
        is_design = series_id.startswith("DESIGN_")
        intervals = [{
            "timeseries_id": series_id,
            "datetime": row["datetime"],
            "rainfall_15min_mm": float(row["rainfall_15min_mm"]),
            "intensity_mm_per_hr": float(row["intensity_mm_per_hr"]),
        } for row in rows]
        output.append({
            "timeseries_id": series_id,
            "family": "design_storm" if is_design else "historical_reconstruction",
            "classification": "configured rainfall scenario" if is_design else "local 27-hour rainfall reconstruction",
            "interval_minutes": 15,
            "duration_hours": len(rows) * 0.25,
            "record_count": len(rows),
            "total_depth_mm": round(sum(values), 3),
            "peak_intensity_mm_per_hr": round(max(intensities, default=0.0), 3),
            "units": {"rainfall": "mm per 15-minute interval", "intensity": "mm/hour"},
            "validation_status": "configured; not a hydraulic prediction" if is_design else "reconstructed local series; not independently verified",
            "intervals": intervals,
        })
    return output


@app.get("/api/v1/risk-map")
def risk_map(
    request: Request,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=350, ge=1, le=1000),
    minx: float | None = None,
    miny: float | None = None,
    maxx: float | None = None,
    maxy: float | None = None,
    ward: str | None = None,
) -> dict:
    resources = _resources(request)
    bounds_values = (minx, miny, maxx, maxy)
    if any(value is not None for value in bounds_values) and any(value is None for value in bounds_values):
        raise HTTPException(status_code=422, detail="Provide all four projected bbox parameters: minx, miny, maxx, maxy")
    if minx is not None and (minx > maxx or miny > maxy):
        raise HTTPException(status_code=422, detail="bbox minimums must not exceed maximums")

    matching = []
    for entry in resources["grid_entries"]:
        properties = entry["properties"]
        if ward and str(properties.get("ward", "")).strip().casefold() != ward.strip().casefold():
            continue
        bounds = entry["bounds"]
        if minx is not None and (bounds[2] < minx or bounds[0] > maxx or bounds[3] < miny or bounds[1] > maxy):
            continue
        matching.append(entry)
    page = matching[offset : offset + limit]
    features = []
    for entry in page:
        prediction = _prediction_response(resources, entry["grid_id"])
        props = dict(entry["properties"])
        props["susceptibility_score"] = prediction["susceptibility_score"]
        props["predicted_class"] = prediction["predicted_class"]
        props["decision_threshold"] = prediction["decision_threshold"]
        features.append({"type": "Feature", "properties": props, "geometry": entry["geometry"]})
    next_offset = offset + len(page) if offset + len(page) < len(matching) else None
    return {
        "type": "FeatureCollection",
        "crs": resources["grid_crs"],
        "features": features,
        "returned": len(features),
        "total_matching": len(matching),
        "offset": offset,
        "limit": limit,
        "next_offset": next_offset,
    }


@app.post("/api/v1/predict")
def predict(request: Request, payload: PredictRequest) -> dict:
    resources = _resources(request)
    if payload.grid_id is not None:
        grid_id = payload.grid_id
    else:
        x, y = resources["transformer"].transform(payload.longitude, payload.latitude)
        point = Point(x, y)
        candidates = [int(index) for index in resources["grid_tree"].query(point, predicate="intersects")]
        if not candidates:
            raise HTTPException(status_code=404, detail="No 100 m ML grid cell contains the supplied coordinate")
        grid_id = min(resources["grid_ids"][index] for index in candidates)
    return _prediction_response(resources, grid_id)


@app.post("/api/v1/simulation/run")
def simulation_unavailable(payload: SimulationRequest) -> None:
    raise HTTPException(
        status_code=501,
        detail=(
            "The available backend model predicts historical mapped-flood susceptibility from static cell features. "
            "It does not simulate rainfall, tides, water depth, or SWMM timesteps."
        ),
    )


@app.get("/api/v1/drainage-network")
def drainage_network() -> dict:
    if not DRAINAGE_GEOJSON.is_file():
        raise HTTPException(status_code=503, detail="Processed municipal drainage GeoJSON is unavailable")
    try:
        document = json.loads(DRAINAGE_GEOJSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail=f"Could not load drainage GeoJSON: {exc}") from exc
    if document.get("type") != "FeatureCollection":
        raise HTTPException(status_code=500, detail="Processed drainage file is not a GeoJSON FeatureCollection")
    return document