from __future__ import annotations

import logging
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings
from .schemas import (
    ComponentStatus,
    PredictRequest,
    PredictionResponse,
    RiskMapResponse,
    ScenarioResponse,
    SimulationRequest,
    SimulationResponse,
    SwmmRunRequest,
    SwmmRunResponse,
    SwmmStatusResponse,
    SystemStatusResponse,
)
from .services import BackendDataService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
LOGGER = logging.getLogger(__name__)
settings = Settings.from_environment()
service = BackendDataService(settings)

app = FastAPI(title="TERRA05 Flood Susceptibility API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def unavailable(component: str, exc: Exception) -> HTTPException:
    LOGGER.exception("%s unavailable", component)
    return HTTPException(status_code=503, detail={"error": f"{component}_unavailable", "message": str(exc)})


@app.get("/health")
def health() -> dict:
    status = service.status()
    data_components = (status["model"], status["rainfall_catalogue"], status["geospatial_data"])
    return {
        "status": "ok" if all(item["ready"] for item in data_components) else "degraded",
        "components": status,
    }


@app.get("/api/v1/system-status", response_model=SystemStatusResponse)
def system_status() -> dict:
    return service.status()


@app.get("/api/v1/validation/susceptibility")
def susceptibility_validation() -> dict:
    try:
        return service.validation_summary
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise unavailable("susceptibility_validation", exc) from exc


@app.get("/api/v1/scenarios", response_model=list[ScenarioResponse])
def scenarios() -> list[dict]:
    try:
        return service.scenarios()
    except (OSError, KeyError, ValueError) as exc:
        raise unavailable("rainfall_catalogue", exc) from exc


@app.post("/api/v1/predict", response_model=PredictionResponse)
def predict(request: PredictRequest) -> dict:
    try:
        grid_id = request.grid_id
        if grid_id is None:
            grid_id = service.grid_id_for_coordinates(request.latitude, request.longitude)
        score, location = service.model_prediction(grid_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail={"error": "location_not_found", "message": str(exc)}) from exc
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        raise unavailable("susceptibility_model", exc) from exc
    return {
        **location,
        "susceptibility_score": score,
        "uncertainty_score": 0.25,
        "prediction_interval": (max(0.0, score - 0.125), min(1.0, score + 0.125)),
        "model": "RandomForestClassifier susceptibility pipeline",
        "model_version": service.settings.model_path.name,
        "score_semantics": "Uncalibrated model susceptibility score for historical flood-label overlap; not a flood probability or event forecast",
        "limitations": [
            "Historical spatial susceptibility only; this endpoint does not forecast a specific rainfall event.",
            "No real-time rainfall ingestion or hydraulic simulation is applied.",
            "The saved artifact was trained with scikit-learn 1.9.0 and may warn under a different installed version.",
            "Uncertainty is a decision-support range, not a calibrated confidence interval; calibration requires multiple observed flood events.",
        ],
    }


@app.get("/api/v1/risk-map", response_model=RiskMapResponse)
def risk_map(
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    minx: float | None = None,
    miny: float | None = None,
    maxx: float | None = None,
    maxy: float | None = None,
    ward: str | None = None,
) -> dict:
    if any(value is not None for value in (minx, miny, maxx, maxy)) and not all(value is not None for value in (minx, miny, maxx, maxy)):
        raise HTTPException(status_code=422, detail={"error": "invalid_bbox", "message": "Provide all four bbox values"})
    bbox = (minx, miny, maxx, maxy) if minx is not None else None
    try:
        features, total = service.risk_features(offset, limit, bbox)
        if ward:
            features = [feature for feature in features if str(feature.get("properties", {}).get("ward", "")).upper() == ward.upper()]
            total = len(features)
    except (OSError, ValueError, KeyError) as exc:
        raise unavailable("geospatial_data", exc) from exc
    next_offset = offset + limit if offset + limit < total else None
    return {
        "type": "FeatureCollection",
        "crs": "EPSG:32643",
        "features": features,
        "returned": len(features),
        "total_matching": total,
        "offset": offset,
        "limit": limit,
        "next_offset": next_offset,
    }


@app.post("/api/v1/simulation/run", response_model=SimulationResponse)
def run_simulation(request: SimulationRequest) -> dict:
    try:
        return service.run_simulation(
            scenario_id=request.scenario_id,
            ward=request.ward,
            bbox=request.bbox,
            routing_enabled=request.routing_enabled,
            drainage_capacity_mm_hr=request.drainage_capacity_mm_hr,
            tide_level=request.tide_level,
            max_timesteps=request.max_timesteps,
            include_recession=request.include_recession,
            custom_duration_hours=request.custom_duration_hours,
            custom_total_depth_mm=request.custom_total_depth_mm,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail={"error": "simulation_input_not_found", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"error": "invalid_simulation_parameter", "message": str(exc)}) from exc
    except (OSError, RuntimeError) as exc:
        raise unavailable("simulation_engine", exc) from exc


@app.get("/api/v1/drainage-network")
def get_drainage_network() -> dict:
    try:
        return service.drainage_network
    except (OSError, ValueError, KeyError) as exc:
        raise unavailable("drainage_data", exc) from exc


@app.get("/api/v1/swmm/status", response_model=SwmmStatusResponse)
def get_swmm_status() -> dict:
    try:
        return service.swmm_status()
    except Exception as exc:
        raise unavailable("swmm_engine", exc) from exc


@app.post("/api/v1/swmm/sample-run", response_model=SwmmRunResponse)
def post_swmm_sample_run(request: SwmmRunRequest | None = None) -> dict:
    inp_path = request.inp_path if request else None
    sample_interval = request.sample_interval_seconds if request else 900
    max_steps = request.max_steps if request else None
    try:
        return service.run_swmm(
            inp_path=inp_path,
            sample_interval_seconds=sample_interval,
            max_steps=max_steps,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"error": "swmm_model_not_found", "message": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"error": "swmm_engine_unavailable", "message": str(exc)}) from exc
    except Exception as exc:
        raise unavailable("swmm_runner", exc) from exc
