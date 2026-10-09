from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grid_id: int | None = Field(default=None, gt=0)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def require_location(self) -> "PredictRequest":
        if self.grid_id is None and (self.latitude is None or self.longitude is None):
            raise ValueError("Provide grid_id or both latitude and longitude")
        if self.grid_id is not None and (self.latitude is not None or self.longitude is not None):
            raise ValueError("Provide grid_id or coordinates, not both")
        return self


class PredictionResponse(BaseModel):
    grid_id: int
    ward: str | None
    susceptibility_score: float = Field(ge=0, le=1)
    model: str
    model_version: str
    score_semantics: str
    limitations: list[str]


class ScenarioResponse(BaseModel):
    timeseries_id: str
    family: str
    classification: str
    interval_minutes: int
    duration_hours: float
    record_count: int
    total_depth_mm: float
    peak_intensity_mm_per_hr: float
    units: dict[str, str]
    validation_status: str
    intervals: list[dict[str, Any]]


class RiskMapResponse(BaseModel):
    type: str
    crs: str
    features: list[dict[str, Any]]
    returned: int
    total_matching: int
    offset: int
    limit: int
    next_offset: int | None


class ComponentStatus(BaseModel):
    ready: bool
    path: str | None = None
    detail: str


class SystemStatusResponse(BaseModel):
    api: str
    model: ComponentStatus
    rainfall_catalogue: ComponentStatus
    geospatial_data: ComponentStatus
    swmm_model: ComponentStatus


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(default="DESIGN_RED_100MM", description="Rainfall scenario timeseries ID from catalogue, or CUSTOM for user-entered rainfall")
    ward: str | None = Field(default=None, description="Optional ward filter (e.g. 'L' for Kurla/Mithi corridor)")
    bbox: tuple[float, float, float, float] | None = Field(default=None, description="Optional bounding box (minx, miny, maxx, maxy) in EPSG:32643")
    routing_enabled: bool = Field(default=True, description="Enable 2D terrain diffusive overland routing between adjacent cells")
    drainage_capacity_mm_hr: float = Field(default=25.0, ge=0.0, le=200.0, description="Base municipal stormwater drainage extraction rate (mm/hr)")
    tide_level: str = Field(default="normal", pattern="^(normal|high|extreme)$", description="Coastal tide/backwater condition")
    max_timesteps: int | None = Field(default=None, gt=0, le=200, description="Optional cap on number of timesteps")
    custom_duration_hours: float | None = Field(default=None, gt=0, le=168, description="Custom rainfall duration in hours")
    custom_total_depth_mm: float | None = Field(default=None, gt=0, le=5000, description="Total custom rainfall depth in millimetres")

    @model_validator(mode="after")
    def validate_custom_rainfall(self) -> "SimulationRequest":
        custom_values = (self.custom_duration_hours, self.custom_total_depth_mm)
        if any(value is not None for value in custom_values) and not all(value is not None for value in custom_values):
            raise ValueError("Provide both custom_duration_hours and custom_total_depth_mm")
        if self.scenario_id == "CUSTOM" and not all(value is not None for value in custom_values):
            raise ValueError("CUSTOM rainfall requires duration and total depth")
        if self.scenario_id != "CUSTOM" and any(value is not None for value in custom_values):
            raise ValueError("Custom rainfall values can only be used with scenario_id CUSTOM")
        return self


class SimulationTimestepMetrics(BaseModel):
    step_index: int
    datetime: str
    elapsed_minutes: int
    rainfall_mm: float
    rainfall_intensity_mm_per_hr: float
    rainfall_excess_mm: float
    infiltrated_depth_mm: float
    drainage_removed_volume_m3: float
    surface_storage_volume_m3: float
    max_water_depth_m: float
    mean_water_depth_m: float
    inundated_cells_count: int
    inundated_area_km2: float


class SimulationCellResult(BaseModel):
    grid_id: int
    ward: str
    centroid_lat: float
    centroid_lng: float
    elevation_m: float
    built_up_fraction: float
    depth_by_timestep: list[float]
    max_depth_m: float
    final_depth_m: float


class SimulationWaterBalance(BaseModel):
    total_rainfall_volume_m3: float
    total_infiltration_volume_m3: float
    total_depression_storage_volume_m3: float
    total_drainage_removed_volume_m3: float
    total_surface_storage_volume_m3: float
    mass_balance_error_m3: float
    mass_balance_error_percent: float


class SimulationDomainSummary(BaseModel):
    cell_count: int
    total_area_km2: float
    cell_resolution_m: float
    crs: str
    ward: str | None
    routing_method: str


class SimulationResponse(BaseModel):
    scenario_id: str
    scenario_family: str
    duration_hours: float
    interval_minutes: int
    domain_summary: SimulationDomainSummary
    water_balance: SimulationWaterBalance
    metrics: dict[str, Any]
    timesteps: list[SimulationTimestepMetrics]
    cells: list[SimulationCellResult]
    limitations: list[str]


class SwmmStatusResponse(BaseModel):
    pyswmm_available: bool
    pyswmm_version: str | None
    swmm_engine_version: str | None
    benchmark_model_path: str | None
    benchmark_model_ready: bool
    mumbai_calibrated_model_available: bool
    status: str
    missing_prerequisites: list[str]
    disclaimer: str


class SwmmRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inp_path: str | None = Field(default=None, description="Path to .inp file; defaults to benchmark test model if omitted")
    sample_interval_seconds: int = Field(default=900, ge=30, le=3600, description="Snapshot interval in seconds")
    max_steps: int | None = Field(default=None, gt=0, le=10000, description="Optional step cap for testing")


class SwmmRunResponse(BaseModel):
    model_path: str
    is_synthetic_benchmark: bool
    engine_version: str
    flow_units: str
    total_steps_simulated: int
    snapshot_count: int
    continuity: dict[str, Any]
    system_summary: dict[str, Any]
    nodes: dict[str, Any]
    links: dict[str, Any]
    subcatchments: dict[str, Any]
    snapshots: list[dict[str, Any]]
    limitations: list[str]
