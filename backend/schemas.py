from typing import Any
import math

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
    uncertainty_score: float | None = Field(default=None, ge=0, le=1)
    prediction_interval: tuple[float, float] | None = None
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
    tide_level: str = Field(default="normal", pattern="^(normal|high|extreme)$", description="Legacy UI selector; tide is not hydraulically applied without verified boundary data")
    max_timesteps: int | None = Field(default=None, gt=0, le=200, description="Optional cap on number of timesteps")
    include_recession: bool = Field(default=False, description="Append a zero-rainfall drainage tail after the rainfall event")
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
    historical_susceptibility: float | None = Field(default=None, ge=0, le=1)
    physical_event_score: float | None = Field(default=None, ge=0, le=1)
    hybrid_event_risk_score: float | None = Field(default=None, ge=0, le=1)
    event_inundated: bool | None = None
    wet_fraction_of_steps: float | None = Field(default=None, ge=0, le=1)
    risk_tier: str | None = None
    uncertainty_score: float | None = Field(default=None, ge=0, le=1)
    risk_interval: tuple[float, float] | None = None


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
    engine: str = "fast"
    validation_status: str = "ENGINE_EXECUTABLE_HYDRAULICALLY_UNVALIDATED"
    tide_mode_requested: str | None = None
    tide_mode_applied: bool = False
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
    provenance: dict[str, Any] | None = None
    event_forecast: dict[str, Any] | None = None


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


class MLPhase3PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grid_id: int = Field(gt=0)
    scenario_id: str = Field(default="historical_2005", pattern="^historical_2005$")


class SwmmSimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(default="historical_2005", min_length=1, max_length=100)
    rainfall_multiplier: float = Field(default=1.0, gt=0.0, le=5.0)
    infrastructure_mode: str = Field(default="existing", pattern="^(existing|proposal|existing_plus_proposal)$")
    tide_mode: str = Field(default="disabled", pattern="^(disabled|low|normal|high|very_high)$")
    rainfall_profile_mm: list[float] | None = Field(default=None, max_length=108, description="Optional 15-minute depths for up to the 27-hour historical event window")

    @model_validator(mode="after")
    def validate_profile(self) -> "SwmmSimulationRequest":
        if self.rainfall_profile_mm is not None:
            if not self.rainfall_profile_mm or any(value < 0 or not math.isfinite(value) for value in self.rainfall_profile_mm):
                raise ValueError("rainfall_profile_mm must contain finite non-negative interval depths")
        return self


class SwmmSimulationResponse(BaseModel):
    engine: str = "swmm"
    simulation_id: str
    scenario_id: str
    status: str
    cache_hit: bool
    validation_status: str
    summary: dict[str, Any] | None = None
    result_paths: dict[str, str] | None = None
    error: str | None = None


class SwmmComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_a: str = Field(pattern="^sim_[a-f0-9]{20}$")
    scenario_b: str = Field(pattern="^sim_[a-f0-9]{20}$")


class SwmmComparisonResponse(BaseModel):
    scenario_a: str
    scenario_b: str
    peak_depth_difference_m: float
    flooded_area_difference_km2: float | None
    flood_duration_difference_minutes: float | None
    time_to_flood_difference_minutes: float | None
    peak_drainage_flow_difference_m3s: float
    comparison_status: str


class ScenarioRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: str = Field(pattern="^(custom|historical_replay)$")
    event_id: str | None = Field(default=None, pattern="^E001$")
    total_rainfall_mm: float | None = Field(default=None, gt=0, le=5000)
    duration_minutes: int | None = Field(default=None, ge=15, le=1620)
    profile_mm: list[float] | None = Field(default=None, min_length=1, max_length=108)

    @model_validator(mode="after")
    def valid_rainfall_input(self) -> "ScenarioRunRequest":
        if self.mode == "historical_replay":
            if self.event_id != "E001" or any(x is not None for x in (self.total_rainfall_mm, self.duration_minutes, self.profile_mm)):
                raise ValueError("Historical replay requires event_id E001 only")
            return self
        if self.event_id is not None:
            raise ValueError("Custom rainfall cannot specify a historical event")
        manual = self.total_rainfall_mm is not None or self.duration_minutes is not None
        if manual and (self.total_rainfall_mm is None or self.duration_minutes is None or self.profile_mm is not None):
            raise ValueError("Manual rainfall requires total_rainfall_mm and duration_minutes only")
        if not manual and self.profile_mm is None:
            raise ValueError("Provide total_rainfall_mm with duration_minutes, or profile_mm")
        if self.duration_minutes is not None and self.duration_minutes % 15:
            raise ValueError("duration_minutes must be a multiple of 15")
        if self.profile_mm is not None and any(not math.isfinite(value) or value < 0 for value in self.profile_mm):
            raise ValueError("profile_mm values must be finite and non-negative")
        return self


class ScenarioJobResponse(BaseModel):
    simulation_id: str
    scenario_id: str
    mode: str
    status: str
    cache_hit: bool
    created_at: str
    updated_at: str
    rainfall_source: str
    rainfall_hash: str
    rainfall_total_mm: float
    duration_minutes: int
    physics_supported: bool
    prediction_mode: str
    validation_status: str
    progress: int | None = None
    error: str | None = None
    result_path: str | None = None
    risk_summary: dict[str, Any] | None = None
    performance: dict[str, Any] | None = None
    physics_simulation_id: str | None = None
    physics_cache_hit: bool | None = None
    physics_supported_cells: int | None = None
    elapsed_seconds: float | None = None


class ScenarioResultsResponse(BaseModel):
    scenario_id: str
    event_id: str | None
    rainfall_source: str
    prediction_semantics: str
    target_provenance: str
    risk_map: list[dict[str, Any]]
    critical_assets: list[dict[str, Any]]
    physics_supported_cells: int
    prediction_mode_counts: dict[str, int]
    summary: dict[str, Any]
    decision_support: list[str]
    performance: dict[str, Any]
