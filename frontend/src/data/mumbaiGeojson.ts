// Geographically referenced GIS datasets for Mithi Basin, critical infrastructure, roads, drainage & urban simulation
import type { FeatureCollection, Polygon, LineString, Point } from 'geojson';

// 1. MITHI RIVER GEOGRAPHIC WATER CHANNEL (Actual course through Kurla, BKC, Mahim Bay)
export const MITHI_RIVER_GEOJSON: FeatureCollection<LineString> = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { 
        name: 'Mithi River', 
        type: 'PRIMARY_NATURAL_CHANNEL',
        lengthKm: 17.8,
        catchmentAreaKm2: 72.4,
      },
      geometry: {
        type: 'LineString',
        coordinates: [
          [72.8845, 19.1210], // Powai/Vihar overflow
          [72.8790, 19.1025], // Saki Naka
          [72.8725, 19.0880], // Kurla / Airport periphery
          [72.8680, 19.0750], // CST Road crossing
          [72.8635, 19.0665], // BKC northern boundary
          [72.8580, 19.0560], // Dharavi boundary
          [72.8475, 19.0490], // Mahim Creek
          [72.8385, 19.0420], // Mahim Bay outfall into Arabian Sea
        ],
      },
    },
  ],
};

// 2. BMC STORMWATER DRAINAGE NETWORK
export const BMC_DRAINAGE_GEOJSON: FeatureCollection<LineString> = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { 
        id: 'drain-vakola',
        name: 'Vakola Nullah Trunk Outfall', 
        category: 'MAJOR_TRUNK',
        capacityCms: 85,
      },
      geometry: {
        type: 'LineString',
        coordinates: [
          [72.8480, 19.0850],
          [72.8550, 19.0810],
          [72.8610, 19.0782],
          [72.8680, 19.0750],
        ],
      },
    },
    {
      type: 'Feature',
      properties: { 
        id: 'drain-kurla',
        name: 'Kurla Bail Bazar Box Culvert', 
        category: 'MAJOR_TRUNK',
        capacityCms: 45,
      },
      geometry: {
        type: 'LineString',
        coordinates: [
          [72.8860, 19.0760],
          [72.8820, 19.0740],
          [72.8797, 19.0726],
          [72.8725, 19.0710],
          [72.8680, 19.0750],
        ],
      },
    },
    {
      type: 'Feature',
      properties: { 
        id: 'drain-sion',
        name: 'Sion-Chunabhatti Box Conduit', 
        category: 'SECONDARY_SWD',
        capacityCms: 38,
      },
      geometry: {
        type: 'LineString',
        coordinates: [
          [72.8814, 19.0528],
          [72.8720, 19.0460],
          [72.8622, 19.0390],
          [72.8580, 19.0410],
        ],
      },
    },
    {
      type: 'Feature',
      properties: { 
        id: 'drain-bkc',
        name: 'BKC Storm Holding Conduit', 
        category: 'SECONDARY_SWD',
        capacityCms: 60,
      },
      geometry: {
        type: 'LineString',
        coordinates: [
          [72.8710, 19.0620],
          [72.8670, 19.0640],
          [72.8656, 19.0657],
          [72.8635, 19.0665],
        ],
      },
    },
    {
      type: 'Feature',
      properties: { 
        id: 'drain-vidyavihar',
        name: 'Vidya Vihar Central Railway Culvert Line', 
        category: 'SECONDARY_SWD',
        capacityCms: 32,
      },
      geometry: {
        type: 'LineString',
        coordinates: [
          [72.8990, 19.0830],
          [72.8974, 19.0798],
          [72.8880, 19.0770],
          [72.8797, 19.0726],
        ],
      },
    },
  ],
};

// 3. SURFACE RUNOFF FLOW PATHS (Moving toward low elevation, drains & Mithi River)
export const RUNOFF_FLOW_PATHS_GEOJSON: FeatureCollection<LineString> = {
  type: 'FeatureCollection',
  features: [
    // Santacruz ridge down to Kalina / CST road
    {
      type: 'Feature',
      properties: { direction: 'SOUTH_EAST', slope: 0.04 },
      geometry: {
        type: 'LineString',
        coordinates: [
          [72.8520, 19.0860],
          [72.8560, 19.0820],
          [72.8611, 19.0782],
        ],
      },
    },
    // Kurla hills / Sakinaka down to Bail Bazar basin
    {
      type: 'Feature',
      properties: { direction: 'SOUTH_WEST', slope: 0.06 },
      geometry: {
        type: 'LineString',
        coordinates: [
          [72.8880, 19.0850],
          [72.8840, 19.0780],
          [72.8797, 19.0726],
        ],
      },
    },
    // Sion Hill down to Sion Circle railway depression
    {
      type: 'Feature',
      properties: { direction: 'WEST', slope: 0.05 },
      geometry: {
        type: 'LineString',
        coordinates: [
          [72.8680, 19.0430],
          [72.8650, 19.0410],
          [72.8622, 19.0390],
        ],
      },
    },
    // Chunabhatti EEH overland flow down to Mithi Creek
    {
      type: 'Feature',
      properties: { direction: 'WEST', slope: 0.03 },
      geometry: {
        type: 'LineString',
        coordinates: [
          [72.8860, 19.0560],
          [72.8814, 19.0528],
          [72.8740, 19.0510],
          [72.8635, 19.0560],
        ],
      },
    },
  ],
};

// 4. MAJOR ROAD ARTERIALS (For road-level inundation status: Safe -> At Risk -> Partially Flooded -> Impassable)
export const MUMBAI_MAJOR_ROADS_GEOJSON: FeatureCollection<LineString> = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { 
        id: 'road-lbs-marg',
        name: 'LBS Marg (Kurla Section)', 
        elevationM: 4.8,
        criticalThresholdM: 0.25,
      },
      geometry: {
        type: 'LineString',
        coordinates: [
          [72.8760, 19.0850],
          [72.8785, 19.0770],
          [72.8797, 19.0726],
          [72.8810, 19.0650],
          [72.8830, 19.0550],
        ],
      },
    },
    {
      type: 'Feature',
      properties: { 
        id: 'road-cst-road',
        name: 'CST Road (Kalina Corridor)', 
        elevationM: 6.4,
        criticalThresholdM: 0.30,
      },
      geometry: {
        type: 'LineString',
        coordinates: [
          [72.8520, 19.0790],
          [72.8611, 19.0782],
          [72.8680, 19.0750],
          [72.8750, 19.0730],
        ],
      },
    },
    {
      type: 'Feature',
      properties: { 
        id: 'road-sion-bandra',
        name: 'Sion-Bandra Link Road', 
        elevationM: 5.2,
        criticalThresholdM: 0.28,
      },
      geometry: {
        type: 'LineString',
        coordinates: [
          [72.8510, 19.0510],
          [72.8580, 19.0460],
          [72.8622, 19.0390],
          [72.8700, 19.0430],
        ],
      },
    },
    {
      type: 'Feature',
      properties: { 
        id: 'road-eeh',
        name: 'Eastern Express Highway (Chunabhatti)', 
        elevationM: 7.1,
        criticalThresholdM: 0.40,
      },
      geometry: {
        type: 'LineString',
        coordinates: [
          [72.8840, 19.0430],
          [72.8814, 19.0528],
          [72.8850, 19.0650],
          [72.8880, 19.0770],
          [72.8920, 19.0880],
        ],
      },
    },
    {
      type: 'Feature',
      properties: { 
        id: 'road-bkc-connector',
        name: 'BKC Flyover & Connector', 
        elevationM: 8.2,
        criticalThresholdM: 0.45,
      },
      geometry: {
        type: 'LineString',
        coordinates: [
          [72.8560, 19.0580],
          [72.8620, 19.0620],
          [72.8656, 19.0657],
          [72.8710, 19.0670],
        ],
      },
    },
  ],
};

// 5. CRITICAL INFRASTRUCTURE ASSETS (Hospitals, Shelters, Stations)
export const CRITICAL_INFRASTRUCTURE_GEOJSON: FeatureCollection<Point> = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { 
        id: 'infra-kurla-bhabha',
        name: 'Bhabha Municipal Hospital', 
        category: 'HOSPITAL',
        elevationM: 5.4,
        locality: 'Kurla West',
      },
      geometry: { type: 'Point', coordinates: [72.8770, 19.0695] },
    },
    {
      type: 'Feature',
      properties: { 
        id: 'infra-sion-hospital',
        name: 'Lokmanya Tilak Municipal General Hospital (Sion)', 
        category: 'HOSPITAL',
        elevationM: 5.6,
        locality: 'Sion',
      },
      geometry: { type: 'Point', coordinates: [72.8605, 19.0375] },
    },
    {
      type: 'Feature',
      properties: { 
        id: 'infra-kurla-station',
        name: 'Kurla Railway Junction', 
        category: 'TRANSIT_HUB',
        elevationM: 4.6,
        locality: 'Kurla',
      },
      geometry: { type: 'Point', coordinates: [72.8797, 19.0680] },
    },
    {
      type: 'Feature',
      properties: { 
        id: 'infra-sion-station',
        name: 'Sion Railway Station', 
        category: 'TRANSIT_HUB',
        elevationM: 4.9,
        locality: 'Sion',
      },
      geometry: { type: 'Point', coordinates: [72.8630, 19.0420] },
    },
    {
      type: 'Feature',
      properties: { 
        id: 'infra-bkc-fire',
        name: 'BKC Fire Command Center', 
        category: 'FIRE_STATION',
        elevationM: 8.1,
        locality: 'BKC',
      },
      geometry: { type: 'Point', coordinates: [72.8680, 19.0645] },
    },
    {
      type: 'Feature',
      properties: { 
        id: 'infra-kalina-shelter',
        name: 'Kalina Municipal Emergency Relief Shelter', 
        category: 'SHELTER',
        elevationM: 7.0,
        locality: 'Kalina',
      },
      geometry: { type: 'Point', coordinates: [72.8625, 19.0765] },
    },
  ],
};

// 6. BMC CHRONIC FLOODING SPOTS
export const BMC_FLOOD_SPOTS_GEOJSON: FeatureCollection<Point> = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { name: 'Bail Bazar Lowland', ward: 'L', depthBenchmark: '1.2m' },
      geometry: { type: 'Point', coordinates: [72.8805, 19.0732] },
    },
    {
      type: 'Feature',
      properties: { name: 'Sion Circle Railway Subway', ward: 'F-North', depthBenchmark: '1.1m' },
      geometry: { type: 'Point', coordinates: [72.8625, 19.0395] },
    },
    {
      type: 'Feature',
      properties: { name: 'CST Road Underpass', ward: 'H-East', depthBenchmark: '0.8m' },
      geometry: { type: 'Point', coordinates: [72.8615, 19.0778] },
    },
    {
      type: 'Feature',
      properties: { name: 'Chunabhatti Station Underpass', ward: 'L', depthBenchmark: '0.9m' },
      geometry: { type: 'Point', coordinates: [72.8820, 19.0535] },
    },
    {
      type: 'Feature',
      properties: { name: 'BKC Bharat Nagar Swale', ward: 'H-East', depthBenchmark: '0.6m' },
      geometry: { type: 'Point', coordinates: [72.8640, 19.0630] },
    },
  ],
};

// 7. DETERMINISTIC PHYSICAL INUNDATION STATE SURFACES
// Core basins with realistic topographic edge geometries
interface BasinGeometryDef {
  id: string;
  name: string;
  elevationM: number;
  center: [number, number];
  offsets: [number, number][]; // 16-20 deterministic topographical offsets
  maxRadiiKm: Record<number, number>; // max radius at T+04 for 25, 50, 100, 150 mm/hr
  maxDepthsM: Record<number, number>; // max depth at T+04
}

const DETERMINISTIC_BASINS: BasinGeometryDef[] = [
  {
    id: 'basin-kurla',
    name: 'Kurla West (Bail Bazar & LBS Marg Depression)',
    elevationM: 4.2,
    center: [72.8797, 19.0726],
    // Irregular catchment contours conforming to railway embankment and LBS Marg slope
    offsets: [
      [1.05, 0.20], [1.18, 0.45], [0.95, 0.82], [0.60, 1.12], 
      [0.15, 1.25], [-0.35, 1.15], [-0.75, 0.85], [-1.08, 0.50],
      [-1.22, 0.10], [-1.15, -0.40], [-0.85, -0.75], [-0.45, -1.05],
      [-0.05, -1.20], [0.40, -1.05], [0.75, -0.70], [0.98, -0.25],
    ],
    maxRadiiKm: { 25: 0.0022, 50: 0.0048, 100: 0.0078, 150: 0.0105 },
    maxDepthsM: { 25: 0.08, 50: 0.31, 100: 0.61, 150: 1.18 },
  },
  {
    id: 'basin-sion',
    name: 'Sion Circle Railway Subway & Connector',
    elevationM: 5.1,
    center: [72.8622, 19.0390],
    offsets: [
      [0.90, 0.15], [1.10, 0.50], [0.85, 0.90], [0.45, 1.20],
      [0.05, 1.10], [-0.45, 1.05], [-0.90, 0.70], [-1.15, 0.30],
      [-1.10, -0.15], [-0.95, -0.55], [-0.60, -0.90], [-0.20, -1.15],
      [0.25, -1.10], [0.65, -0.80], [0.85, -0.40], [0.95, -0.10],
    ],
    maxRadiiKm: { 25: 0.0018, 50: 0.0039, 100: 0.0068, 150: 0.0092 },
    maxDepthsM: { 25: 0.05, 50: 0.26, 100: 0.54, 150: 0.98 },
  },
  {
    id: 'basin-kalina',
    name: 'Kalina / CST Road Junction Lowland',
    elevationM: 6.6,
    center: [72.8611, 19.0782],
    offsets: [
      [1.15, 0.10], [1.02, 0.48], [0.70, 0.88], [0.30, 1.15],
      [-0.10, 1.18], [-0.60, 0.95], [-0.98, 0.60], [-1.12, 0.15],
      [-1.05, -0.30], [-0.75, -0.70], [-0.35, -1.02], [0.10, -1.12],
      [0.55, -0.95], [0.88, -0.65], [1.10, -0.28], [1.18, -0.05],
    ],
    maxRadiiKm: { 25: 0.0015, 50: 0.0032, 100: 0.0056, 150: 0.0076 },
    maxDepthsM: { 25: 0.04, 50: 0.18, 100: 0.39, 150: 0.76 },
  },
  {
    id: 'basin-chunabhatti',
    name: 'Chunabhatti / Eastern Express Swale',
    elevationM: 6.2,
    center: [72.8814, 19.0528],
    offsets: [
      [0.95, 0.25], [1.12, 0.55], [0.80, 0.95], [0.35, 1.12],
      [-0.15, 1.08], [-0.65, 0.85], [-1.02, 0.45], [-1.15, 0.05],
      [-1.02, -0.42], [-0.70, -0.82], [-0.25, -1.08], [0.20, -1.05],
      [0.60, -0.85], [0.90, -0.50], [1.05, -0.15], [1.02, 0.10],
    ],
    maxRadiiKm: { 25: 0.0014, 50: 0.0030, 100: 0.0052, 150: 0.0070 },
    maxDepthsM: { 25: 0.05, 50: 0.21, 100: 0.38, 150: 0.70 },
  },
  {
    id: 'basin-bkc',
    name: 'BKC G-Block Lowland & Holding Ponds',
    elevationM: 7.9,
    center: [72.8656, 19.0657],
    offsets: [
      [0.90, 0.20], [1.05, 0.50], [0.75, 0.90], [0.30, 1.05],
      [-0.20, 1.00], [-0.70, 0.75], [-1.00, 0.35], [-1.08, -0.05],
      [-0.95, -0.45], [-0.60, -0.80], [-0.15, -1.00], [0.30, -0.95],
      [0.70, -0.70], [0.95, -0.35], [1.02, -0.05], [0.95, 0.12],
    ],
    maxRadiiKm: { 25: 0.0008, 50: 0.0022, 100: 0.0042, 150: 0.0062 },
    maxDepthsM: { 25: 0.02, 50: 0.12, 100: 0.28, 150: 0.59 },
  },
  {
    id: 'basin-vidyavihar',
    name: 'Vidya Vihar Railway Underpass Depression',
    elevationM: 7.4,
    center: [72.8974, 19.0798],
    offsets: [
      [0.92, 0.18], [1.08, 0.52], [0.78, 0.92], [0.32, 1.10],
      [-0.18, 1.05], [-0.68, 0.80], [-1.02, 0.40], [-1.10, -0.02],
      [-0.98, -0.42], [-0.62, -0.78], [-0.18, -1.02], [0.28, -0.98],
      [0.68, -0.72], [0.92, -0.38], [1.00, -0.08], [0.96, 0.10],
    ],
    maxRadiiKm: { 25: 0.0010, 50: 0.0025, 100: 0.0046, 150: 0.0065 },
    maxDepthsM: { 25: 0.03, 50: 0.15, 100: 0.32, 150: 0.65 },
  },
];

// STRICT MONOTONIC SCALING FACTORS:
// Rising Phase (T00 -> T04):
// T00: 0.00 (Dry)
// T01: 0.18 (Localized puddles in lowest depressions)
// T02: 0.42 (Road ponding & drain backup)
// T03: 0.72 (Connected overland flow)
// T04: 1.00 (PEAK INUNDATION - absolute maximum extent)
//
// Recession Phase (T05 -> T06):
// T05: 0.70 (Receding from roads back to drainage channels)
// T06: 0.30 (Residual pooling in lowest depressions only)
//
// Guaranteed: T00 ⊆ T01 ⊆ T02 ⊆ T03 ⊆ T04 (Monotonic rising)
// And: T06 ⊆ T05 ⊆ T04 (Monotonic recession)
const PHASE_RADIUS_FACTORS = [0.0, 0.18, 0.42, 0.72, 1.00, 0.70, 0.30];
const PHASE_DEPTH_FACTORS  = [0.0, 0.15, 0.40, 0.70, 1.00, 0.65, 0.25];

export const getRealisticFloodPolygonsGeoJSON = (
  rainfall: number,
  stepIndex: number, // 0 to 6
  showUncertainty: boolean
): FeatureCollection<Polygon> => {
  const safeStep = Math.min(6, Math.max(0, stepIndex));
  const radiusScale = PHASE_RADIUS_FACTORS[safeStep];
  const depthScale = PHASE_DEPTH_FACTORS[safeStep];

  // Completely dry at T00
  if (radiusScale <= 0.001) {
    return { type: 'FeatureCollection', features: [] };
  }

  const features: any[] = [];
  const rainKey = rainfall >= 150 ? 150 : rainfall >= 100 ? 100 : rainfall >= 50 ? 50 : 25;

  DETERMINISTIC_BASINS.forEach((basin) => {
    const maxRadius = basin.maxRadiiKm[rainKey] || 0.005;
    const maxDepth = basin.maxDepthsM[rainKey] || 0.5;

    const currentRadius = maxRadius * radiusScale;
    const currentDepth = maxDepth * depthScale;
    const [cLng, cLat] = basin.center;

    // Build strictly deterministic polygon conforming to topography
    const coreCoords: [number, number][] = [];
    basin.offsets.forEach(([dx, dy]) => {
      // Longitude correction for ~19° latitude (cos(19°) ≈ 0.9455)
      const lng = cLng + (dx * currentRadius * 1.06);
      const lat = cLat + (dy * currentRadius);
      coreCoords.push([lng, lat]);
    });
    // Close the ring
    coreCoords.push([...coreCoords[0]]);

    features.push({
      type: 'Feature',
      properties: {
        id: `${basin.id}-core`,
        name: basin.name,
        depth: currentDepth,
        elevationM: basin.elevationM,
        layerType: 'CORE_WATER',
        stage: `T0${safeStep}`,
      },
      geometry: {
        type: 'Polygon',
        coordinates: [coreCoords],
      },
    });

    // 90% Confidence Uncertainty Envelope (outer bound)
    if (showUncertainty) {
      const outerRadius = currentRadius * 1.35;
      const uncertCoords: [number, number][] = [];
      basin.offsets.forEach(([dx, dy]) => {
        const lng = cLng + (dx * outerRadius * 1.06);
        const lat = cLat + (dy * outerRadius);
        uncertCoords.push([lng, lat]);
      });
      uncertCoords.push([...uncertCoords[0]]);

      features.push({
        type: 'Feature',
        properties: {
          id: `${basin.id}-uncert`,
          name: `${basin.name} (90% Uncertainty Bound)`,
          depth: currentDepth * 0.5,
          elevationM: basin.elevationM,
          layerType: 'UNCERTAINTY_BOUND',
          stage: `T0${safeStep}`,
        },
        geometry: {
          type: 'Polygon',
          coordinates: [uncertCoords],
        },
      });
    }
  });

  return {
    type: 'FeatureCollection',
    features,
  };
};

// 8. HISTORICAL 2019 REFERENCE GEOJSON
export const HISTORICAL_2019_GEOJSON: FeatureCollection<Polygon> = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { 
        event: 'Historical Benchmark: 2 July 2019 Mumbai Cloudburst (375mm / 24hr)', 
        observedPeakDepth: '1.35m',
        source: 'MCGM Flood Cell Official Record',
      },
      geometry: {
        type: 'Polygon',
        coordinates: [[
          [72.872, 19.066],
          [72.885, 19.069],
          [72.887, 19.078],
          [72.880, 19.080],
          [72.873, 19.075],
          [72.872, 19.066],
        ]],
      },
    },
  ],
};

// Backward-compatible alias for previous views
export const getFloodPolygonsGeoJSON = (rainfall: number, progress: number): FeatureCollection<Polygon> => {
  const step = Math.min(6, Math.max(0, Math.round(progress * 6)));
  return getRealisticFloodPolygonsGeoJSON(rainfall, step, false);
};
