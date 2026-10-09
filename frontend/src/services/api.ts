/**
 * TERRA05 Centralized API Client
 * Connects frontend to the FastAPI backend (http://127.0.0.1:8000).
 */
import proj4 from 'proj4';

// Configure UTM Zone 43N (EPSG:32643) for Mumbai geospatial grid
proj4.defs('EPSG:32643', '+proj=utm +zone=43 +datum=WGS84 +units=m +no_defs');

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

// --- Types & Schemas ---

export interface ComponentStatus {
  ready: boolean;
  path: string | null;
  detail: string;
}

export interface SystemStatusResponse {
  api: string;
  model: ComponentStatus;
  rainfall_catalogue: ComponentStatus;
  geospatial_data: ComponentStatus;
  swmm_model: ComponentStatus;
}

export interface HealthResponse {
  status: 'ok' | 'degraded';
  components: SystemStatusResponse;
}

export interface ScenarioInterval {
  timeseries_id: string;
  datetime: string;
  rainfall_15min_mm: number;
  intensity_mm_per_hr: number;
}

export interface ScenarioResponse {
  timeseries_id: string;
  family: string;
  classification: string;
  interval_minutes: number;
  duration_hours: number;
  record_count: number;
  total_depth_mm: number;
  peak_intensity_mm_per_hr: number;
  units: Record<string, string>;
  validation_status: string;
  intervals: ScenarioInterval[];
}

export interface PredictRequest {
  grid_id?: number;
  latitude?: number;
  longitude?: number;
}

export interface PredictionResponse {
  grid_id: number;
  ward: string | null;
  susceptibility_score: number;
  model: string;
  model_version: string;
  score_semantics: string;
  limitations: string[];
}

export interface RiskGridProperties {
  grid_id: number;
  ward: string;
  elevation_mean: number;
  slope_mean: number;
  built_up_fraction: number;
  vegetation_fraction: number;
  water_fraction: number;
  mangrove_fraction: number;
  drain_density: number;
  distance_to_drain: number;
  distance_to_water: number;
  building_count: number;
  building_density: number;
  flood_fraction: number;
  flood_label: number;
}

export interface RiskMapResponse {
  type: string;
  crs: string;
  features: Array<{
    type: string;
    properties: RiskGridProperties;
    geometry: {
      type: string;
      coordinates: any;
    };
  }>;
  returned: number;
  total_matching: number;
  offset: number;
  limit: number;
  next_offset: number | null;
}

export interface SimulationRequest {
  scenario_id: string;
  ward?: string | null;
  bbox?: [number, number, number, number] | null;
  routing_enabled?: boolean;
  drainage_capacity_mm_hr?: number;
  max_timesteps?: number | null;
  custom_duration_hours?: number | null;
  custom_total_depth_mm?: number | null;
}

export interface SimulationTimestepMetrics {
  step_index: number;
  datetime: string;
  elapsed_minutes: number;
  rainfall_mm: number;
  rainfall_intensity_mm_per_hr: number;
  rainfall_excess_mm: number;
  infiltrated_depth_mm: number;
  drainage_removed_volume_m3: number;
  surface_storage_volume_m3: number;
  max_water_depth_m: number;
  mean_water_depth_m: number;
  inundated_cells_count: number;
  inundated_area_km2: number;
}

export interface SimulationCellResult {
  grid_id: number;
  ward: string;
  centroid_lat: number;
  centroid_lng: number;
  elevation_m: number;
  built_up_fraction: number;
  depth_by_timestep: number[];
  max_depth_m: number;
  final_depth_m: number;
}

export interface SimulationWaterBalance {
  total_rainfall_volume_m3: number;
  total_infiltration_volume_m3: number;
  total_depression_storage_volume_m3: number;
  total_drainage_removed_volume_m3: number;
  total_surface_storage_volume_m3: number;
  mass_balance_error_m3: number;
  mass_balance_error_percent: number;
}

export interface SimulationDomainSummary {
  cell_count: number;
  total_area_km2: number;
  cell_resolution_m: number;
  crs: string;
  ward: string | null;
  routing_method: string;
}

export interface SimulationResponse {
  scenario_id: string;
  scenario_family: string;
  duration_hours: number;
  interval_minutes: number;
  domain_summary: SimulationDomainSummary;
  water_balance: SimulationWaterBalance;
  metrics: {
    timestep_count: number;
    peak_rainfall_intensity_mm_per_hr: number;
    peak_water_depth_m: number;
    peak_inundated_cells_count: number;
    peak_inundated_area_km2: number;
    final_surface_storage_volume_m3: number;
  };
  timesteps: SimulationTimestepMetrics[];
  cells: SimulationCellResult[];
  limitations: string[];
}

export interface RiskMapParams {
  offset?: number;
  limit?: number;
  minx?: number;
  miny?: number;
  maxx?: number;
  maxy?: number;
  ward?: string;
  signal?: AbortSignal;
}

// --- Coordinate Transformation Utility ---

function transformCoords32643To4326(coords: any): any {
  if (typeof coords[0] === 'number') {
    return proj4('EPSG:32643', 'EPSG:4326', [coords[0], coords[1]]);
  }
  return coords.map(transformCoords32643To4326);
}

export function transformRiskMapToGeoJSON4326(data: RiskMapResponse): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: (data.features || []).map((feature) => ({
      type: 'Feature',
      properties: feature.properties,
      geometry: {
        type: feature.geometry.type as any,
        coordinates: transformCoords32643To4326(feature.geometry.coordinates),
      },
    })),
  };
}

export function convertBounds4326To32643(
  minLng: number,
  minLat: number,
  maxLng: number,
  maxLat: number
): { minx: number; miny: number; maxx: number; maxy: number } {
  const min = proj4('EPSG:4326', 'EPSG:32643', [minLng, minLat]);
  const max = proj4('EPSG:4326', 'EPSG:32643', [maxLng, maxLat]);
  return {
    minx: Math.floor(min[0]),
    miny: Math.floor(min[1]),
    maxx: Math.ceil(max[0]),
    maxy: Math.ceil(max[1]),
  };
}

export function simulationDataToGeoJSON(
  simData: SimulationResponse,
  stepIndex: number,
  minDepthThresholdM: number = 0.005
): GeoJSON.FeatureCollection {
  if (!simData || !simData.cells || simData.cells.length === 0) {
    return { type: 'FeatureCollection', features: [] };
  }

  const step = Math.min(Math.max(0, stepIndex), (simData.timesteps?.length || 1) - 1);
  const halfSizeM = (simData.domain_summary?.cell_resolution_m || 100) / 2;
  const dLat = halfSizeM / 111320;

  const features: GeoJSON.Feature[] = [];

  for (const cell of simData.cells) {
    const depth = cell.depth_by_timestep[step] ?? 0;
    if (depth < minDepthThresholdM) continue;

    const cosLat = Math.cos((cell.centroid_lat * Math.PI) / 180);
    const dLng = halfSizeM / (111320 * (cosLat > 0.1 ? cosLat : 0.94));

    const w = cell.centroid_lng - dLng;
    const e = cell.centroid_lng + dLng;
    const s = cell.centroid_lat - dLat;
    const n = cell.centroid_lat + dLat;

    features.push({
      type: 'Feature',
      properties: {
        grid_id: cell.grid_id,
        ward: cell.ward,
        depth: Number(depth.toFixed(4)),
        max_depth: Number(cell.max_depth_m.toFixed(4)),
        elevation_m: Number(cell.elevation_m.toFixed(1)),
        built_up_fraction: Number(cell.built_up_fraction.toFixed(2)),
        is_inundated: depth >= 0.05 ? 1 : 0,
      },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [w, s],
            [e, s],
            [e, n],
            [w, n],
            [w, s],
          ],
        ],
      },
    });
  }

  return {
    type: 'FeatureCollection',
    features,
  };
}

// --- API Functions ---

async function fetchJson<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Accept': 'application/json',
        ...(options.headers || {}),
      },
    });

    if (!response.ok) {
      let errorMsg = `Server error ${response.status}: ${response.statusText}`;
      try {
        const errorJson = await response.json();
        if (errorJson.detail) {
          if (typeof errorJson.detail === 'string') {
            errorMsg = errorJson.detail;
          } else if (errorJson.detail.message) {
            errorMsg = errorJson.detail.message;
          }
        }
      } catch {
        // Fallback to status text
      }
      throw new Error(errorMsg);
    }

    return await response.json();
  } catch (err: any) {
    if (err.name === 'AbortError') {
      throw err;
    }
    const cleanMsg = err.message || 'Network request failed';
    throw new Error(cleanMsg);
  }
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return fetchJson<HealthResponse>('/health', { signal });
}

export async function getSystemStatus(signal?: AbortSignal): Promise<SystemStatusResponse> {
  return fetchJson<SystemStatusResponse>('/api/v1/system-status', { signal });
}

export async function getScenarios(signal?: AbortSignal): Promise<ScenarioResponse[]> {
  return fetchJson<ScenarioResponse[]>('/api/v1/scenarios', { signal });
}

export async function getRiskMap(params: RiskMapParams = {}): Promise<RiskMapResponse> {
  const query = new URLSearchParams();
  if (params.offset !== undefined) query.set('offset', String(params.offset));
  if (params.limit !== undefined) query.set('limit', String(params.limit));
  if (params.minx !== undefined) query.set('minx', String(params.minx));
  if (params.miny !== undefined) query.set('miny', String(params.miny));
  if (params.maxx !== undefined) query.set('maxx', String(params.maxx));
  if (params.maxy !== undefined) query.set('maxy', String(params.maxy));
  if (params.ward) query.set('ward', params.ward);

  const qs = query.toString();
  return fetchJson<RiskMapResponse>(`/api/v1/risk-map${qs ? `?${qs}` : ''}`, {
    signal: params.signal,
  });
}

export async function getPrediction(
  request: PredictRequest,
  signal?: AbortSignal
): Promise<PredictionResponse> {
  return fetchJson<PredictionResponse>('/api/v1/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  });
}

export async function runSimulation(
  request: SimulationRequest,
  signal?: AbortSignal
): Promise<SimulationResponse> {
  return fetchJson<SimulationResponse>('/api/v1/simulation/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  });
}

export async function getDrainageNetwork(
  signal?: AbortSignal
): Promise<GeoJSON.FeatureCollection> {
  return fetchJson<GeoJSON.FeatureCollection>('/api/v1/drainage-network', { signal });
}
