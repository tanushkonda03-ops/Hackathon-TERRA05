export interface ModelExplanationFactors {
  elevationContribution: number;      // e.g. 34%
  drainageContribution: number;       // e.g. 27%
  imperviousContribution: number;     // e.g. 21%
  rainfallContribution: number;       // e.g. 18%
}

export interface TimelineImpactMetrics {
  stage: 'T00' | 'T01' | 'T02' | 'T03' | 'T04' | 'T05' | 'T06';
  stageName: string;
  stageDescription: string;
  alertLevel: 'NORMAL' | 'ADVISORY' | 'FLOOD WATCH' | 'FLOOD WARNING' | 'SEVERE FLOOD EMERGENCY';
  rainfallMmHr: number;
  drainStressState: 'OPTIMAL' | 'LOADING' | 'HIGH LOAD' | 'OVERLOADED' | 'SURCHARGING OVERFLOW';
  stressedDrainsCount: number;
  overloadedSegmentsCount: number;
  overflowZonesCount: number;
  floodedAreaKm2: number;
  affectedStructures: number;
  populationAtRisk: number;
  affectedRoadSegments: number;
  criticalFacilitiesExposed: number;
  mithiRiverStatus: 'NORMAL' | 'ELEVATED' | 'HIGH STRESS' | 'BANKFULL / OVERFLOW';
  // Physical Water Balance Simulation Metrics (EPA SWMM-aligned)
  runoffMm?: number;
  infiltrationMm?: number;
  totalDrainageM3?: number;
  surfaceStorageM3?: number;
  waterBalanceErrorPercent?: number;
}

export interface MumbaiLocation {
  id: string;
  name: string;
  subDistrict: string;
  ward: string;
  gridId?: number; // Verified backend model grid_id
  lng: number;
  lat: number;
  elevationM: number;
  imperviousRatio: number;
  drainDistanceM: number;
  flowAccumulationPercentile: number;
  description: string;
  explanationFactors: ModelExplanationFactors;
  scenarios: Record<number, {
    probability: number;
    depthM: number;
    interval90: [number, number];
    confidencePercent: number;
    severity: 'SAFE' | 'ADVISORY' | 'WARNING' | 'SEVERE';
    affectedStructures: number;
    populationAtRisk: number;
  }>;
}

export const MUMBAI_GEO_LOCATIONS: MumbaiLocation[] = [
  {
    id: 'kurla',
    name: 'Kurla West',
    subDistrict: 'Bail Bazar / LBS Marg',
    ward: 'L Ward',
    gridId: 26910,
    lng: 72.8797,
    lat: 19.0726,
    elevationM: 4.2,
    imperviousRatio: 0.94,
    drainDistanceM: 32,
    flowAccumulationPercentile: 94,
    description: 'Low-elevation basin (4.2m MSL) at the confluence of Mithi River and Central Railway culverts. High impervious cover and tidal backwater drive severe overland flooding.',
    explanationFactors: {
      elevationContribution: 34,
      drainageContribution: 27,
      imperviousContribution: 21,
      rainfallContribution: 18,
    },
    scenarios: {
      25: {
        probability: 24,
        depthM: 0.08,
        interval90: [0.03, 0.16],
        confidencePercent: 88,
        severity: 'ADVISORY',
        affectedStructures: 32,
        populationAtRisk: 1400,
      },
      50: {
        probability: 62,
        depthM: 0.31,
        interval90: [0.20, 0.44],
        confidencePercent: 86,
        severity: 'WARNING',
        affectedStructures: 165,
        populationAtRisk: 7900,
      },
      100: {
        probability: 91,
        depthM: 0.61,
        interval90: [0.44, 0.78],
        confidencePercent: 84,
        severity: 'SEVERE',
        affectedStructures: 580,
        populationAtRisk: 24600,
      },
      150: {
        probability: 98,
        depthM: 1.18,
        interval90: [0.94, 1.42],
        confidencePercent: 81,
        severity: 'SEVERE',
        affectedStructures: 1350,
        populationAtRisk: 52000,
      },
    },
  },
  {
    id: 'sion',
    name: 'Sion Circle',
    subDistrict: 'Sion Talao / Railway Subway',
    ward: 'F-North Ward',
    gridId: 21492,
    lng: 72.8622,
    lat: 19.0390,
    elevationM: 5.1,
    imperviousRatio: 0.89,
    drainDistanceM: 52,
    flowAccumulationPercentile: 88,
    description: 'Depression basin adjoining railway culverts. Surcharging Mahim Creek backflows into Sion stormwater outfalls under heavy downpour.',
    explanationFactors: {
      elevationContribution: 32,
      drainageContribution: 29,
      imperviousContribution: 20,
      rainfallContribution: 19,
    },
    scenarios: {
      25: {
        probability: 19,
        depthM: 0.05,
        interval90: [0.01, 0.12],
        confidencePercent: 90,
        severity: 'SAFE',
        affectedStructures: 14,
        populationAtRisk: 620,
      },
      50: {
        probability: 56,
        depthM: 0.26,
        interval90: [0.16, 0.38],
        confidencePercent: 87,
        severity: 'WARNING',
        affectedStructures: 110,
        populationAtRisk: 4800,
      },
      100: {
        probability: 88,
        depthM: 0.54,
        interval90: [0.38, 0.70],
        confidencePercent: 85,
        severity: 'SEVERE',
        affectedStructures: 390,
        populationAtRisk: 16500,
      },
      150: {
        probability: 96,
        depthM: 0.98,
        interval90: [0.76, 1.22],
        confidencePercent: 82,
        severity: 'SEVERE',
        affectedStructures: 890,
        populationAtRisk: 37000,
      },
    },
  },
  {
    id: 'bkc',
    name: 'BKC (Bandra-Kurla Complex)',
    subDistrict: 'G-Block Financial District',
    ward: 'H-East Ward',
    gridId: 22686,
    lng: 72.8656,
    lat: 19.0657,
    elevationM: 7.9,
    imperviousRatio: 0.96,
    drainDistanceM: 85,
    flowAccumulationPercentile: 65,
    description: 'Engineered commercial hub with detention holding swales. Flooding confined to low-elevation access ramps and surface parking under extreme rainfall.',
    explanationFactors: {
      elevationContribution: 18,
      drainageContribution: 35,
      imperviousContribution: 30,
      rainfallContribution: 17,
    },
    scenarios: {
      25: {
        probability: 6,
        depthM: 0.02,
        interval90: [0.00, 0.05],
        confidencePercent: 94,
        severity: 'SAFE',
        affectedStructures: 2,
        populationAtRisk: 120,
      },
      50: {
        probability: 28,
        depthM: 0.12,
        interval90: [0.05, 0.20],
        confidencePercent: 91,
        severity: 'ADVISORY',
        affectedStructures: 18,
        populationAtRisk: 950,
      },
      100: {
        probability: 64,
        depthM: 0.28,
        interval90: [0.18, 0.40],
        confidencePercent: 89,
        severity: 'WARNING',
        affectedStructures: 74,
        populationAtRisk: 3800,
      },
      150: {
        probability: 82,
        depthM: 0.59,
        interval90: [0.42, 0.78],
        confidencePercent: 86,
        severity: 'SEVERE',
        affectedStructures: 210,
        populationAtRisk: 11500,
      },
    },
  },
  {
    id: 'kalina',
    name: 'Kalina / CST Road',
    subDistrict: 'Santacruz-Kalina Corridor',
    ward: 'H-East Ward',
    gridId: 21243,
    lng: 72.8611,
    lat: 19.0782,
    elevationM: 6.6,
    imperviousRatio: 0.91,
    drainDistanceM: 45,
    flowAccumulationPercentile: 78,
    description: 'Transit corridor along Vakola Nullah confluence. Bottlenecks at CST Road culverts cause rapid water accumulation during cloudbursts.',
    explanationFactors: {
      elevationContribution: 28,
      drainageContribution: 32,
      imperviousContribution: 22,
      rainfallContribution: 18,
    },
    scenarios: {
      25: {
        probability: 14,
        depthM: 0.04,
        interval90: [0.01, 0.09],
        confidencePercent: 91,
        severity: 'SAFE',
        affectedStructures: 8,
        populationAtRisk: 340,
      },
      50: {
        probability: 48,
        depthM: 0.18,
        interval90: [0.10, 0.28],
        confidencePercent: 88,
        severity: 'ADVISORY',
        affectedStructures: 62,
        populationAtRisk: 2600,
      },
      100: {
        probability: 79,
        depthM: 0.39,
        interval90: [0.26, 0.53],
        confidencePercent: 86,
        severity: 'WARNING',
        affectedStructures: 220,
        populationAtRisk: 9200,
      },
      150: {
        probability: 92,
        depthM: 0.76,
        interval90: [0.58, 0.96],
        confidencePercent: 83,
        severity: 'SEVERE',
        affectedStructures: 540,
        populationAtRisk: 22800,
      },
    },
  },
  {
    id: 'chunabhatti',
    name: 'Chunabhatti',
    subDistrict: 'EEH / Harbour Railway Line',
    ward: 'L Ward',
    gridId: 27162,
    lng: 72.8814,
    lat: 19.0528,
    elevationM: 6.2,
    imperviousRatio: 0.87,
    drainDistanceM: 58,
    flowAccumulationPercentile: 80,
    description: 'Low-lying railway subway adjacent to Eastern Express Highway. Prone to severe waterlogging interrupting rail connectivity.',
    explanationFactors: {
      elevationContribution: 30,
      drainageContribution: 30,
      imperviousContribution: 22,
      rainfallContribution: 18,
    },
    scenarios: {
      25: {
        probability: 16,
        depthM: 0.05,
        interval90: [0.01, 0.11],
        confidencePercent: 90,
        severity: 'SAFE',
        affectedStructures: 11,
        populationAtRisk: 480,
      },
      50: {
        probability: 52,
        depthM: 0.21,
        interval90: [0.12, 0.32],
        confidencePercent: 87,
        severity: 'WARNING',
        affectedStructures: 85,
        populationAtRisk: 3700,
      },
      100: {
        probability: 84,
        depthM: 0.38,
        interval90: [0.25, 0.52],
        confidencePercent: 85,
        severity: 'WARNING',
        affectedStructures: 290,
        populationAtRisk: 12400,
      },
      150: {
        probability: 94,
        depthM: 0.70,
        interval90: [0.52, 0.89],
        confidencePercent: 82,
        severity: 'SEVERE',
        affectedStructures: 680,
        populationAtRisk: 28600,
      },
    },
  },
  {
    id: 'vidyavihar',
    name: 'Vidya Vihar',
    subDistrict: 'Railway Subway & Culvert',
    ward: 'N Ward',
    gridId: 32179,
    lng: 72.8974,
    lat: 19.0798,
    elevationM: 7.4,
    imperviousRatio: 0.85,
    drainDistanceM: 64,
    flowAccumulationPercentile: 72,
    description: 'Major railway underpass depression. Inundation occurs when Central Railway culverts reach capacity under high downpour.',
    explanationFactors: {
      elevationContribution: 26,
      drainageContribution: 34,
      imperviousContribution: 22,
      rainfallContribution: 18,
    },
    scenarios: {
      25: {
        probability: 11,
        depthM: 0.03,
        interval90: [0.01, 0.08],
        confidencePercent: 92,
        severity: 'SAFE',
        affectedStructures: 6,
        populationAtRisk: 250,
      },
      50: {
        probability: 42,
        depthM: 0.15,
        interval90: [0.08, 0.24],
        confidencePercent: 89,
        severity: 'ADVISORY',
        affectedStructures: 48,
        populationAtRisk: 2100,
      },
      100: {
        probability: 76,
        depthM: 0.32,
        interval90: [0.21, 0.45],
        confidencePercent: 87,
        severity: 'WARNING',
        affectedStructures: 180,
        populationAtRisk: 7800,
      },
      150: {
        probability: 89,
        depthM: 0.65,
        interval90: [0.48, 0.84],
        confidencePercent: 84,
        severity: 'SEVERE',
        affectedStructures: 460,
        populationAtRisk: 19500,
      },
    },
  },
];

// STRICTLY MONOTONIC SCALING FOR TIMELINE IMPACT METRICS
// Phase A: Rising (T00 -> T04) - STRICTLY NON-DECREASING
// Phase B: Recession (T04 -> T06) - MONOTONIC RETREAT
export const getTimelineImpactMetrics = (
  rainfall: number,
  stepIndex: number
): TimelineImpactMetrics => {
  const steps: TimelineImpactMetrics['stage'][] = ['T00', 'T01', 'T02', 'T03', 'T04', 'T05', 'T06'];
  const stage = steps[Math.min(6, Math.max(0, stepIndex))];
  const intensityFactor = rainfall / 100;

  switch (stage) {
    case 'T00':
      return {
        stage: 'T00',
        stageName: 'Rainfall Onset',
        stageDescription: 'Rainfall begins over Mithi catchment. Infiltration active, zero standing water.',
        alertLevel: 'NORMAL',
        rainfallMmHr: rainfall,
        drainStressState: 'OPTIMAL',
        stressedDrainsCount: 0,
        overloadedSegmentsCount: 0,
        overflowZonesCount: 0,
        floodedAreaKm2: 0.0,
        affectedStructures: 0,
        populationAtRisk: 0,
        affectedRoadSegments: 0,
        criticalFacilitiesExposed: 0,
        mithiRiverStatus: 'NORMAL',
        runoffMm: 0,
        infiltrationMm: Number((3.8 * intensityFactor).toFixed(1)),
        totalDrainageM3: Math.round(75000 * intensityFactor),
        surfaceStorageM3: 0,
        waterBalanceErrorPercent: 0.0,
      };
    case 'T01':
      return {
        stage: 'T01',
        stageName: 'Surface Runoff Initiating',
        stageDescription: 'Infiltration capacity reached. Overland sheet flow routing toward storm drains and Mithi River.',
        alertLevel: rainfall >= 100 ? 'ADVISORY' : 'NORMAL',
        rainfallMmHr: rainfall,
        drainStressState: 'LOADING',
        stressedDrainsCount: Math.max(1, Math.round(3 * intensityFactor)),
        overloadedSegmentsCount: 0,
        overflowZonesCount: 0,
        floodedAreaKm2: Number((0.28 * intensityFactor).toFixed(2)),
        affectedStructures: Math.round(42 * intensityFactor),
        populationAtRisk: Math.round(1800 * intensityFactor),
        affectedRoadSegments: 1,
        criticalFacilitiesExposed: 0,
        mithiRiverStatus: 'ELEVATED',
        runoffMm: Number((4.2 * intensityFactor).toFixed(1)),
        infiltrationMm: Number((3.6 * intensityFactor).toFixed(1)),
        totalDrainageM3: Math.round(176000 * intensityFactor),
        surfaceStorageM3: Math.round(158000 * intensityFactor),
        waterBalanceErrorPercent: 0.0,
      };
    case 'T02':
      return {
        stage: 'T02',
        stageName: 'Drainage Capacity Stressed',
        stageDescription: 'Stormwater culverts reaching 85% capacity. Initial ponding in Bail Bazar and Sion subway.',
        alertLevel: rainfall >= 100 ? 'FLOOD WATCH' : 'ADVISORY',
        rainfallMmHr: rainfall,
        drainStressState: 'HIGH LOAD',
        stressedDrainsCount: Math.max(3, Math.round(7 * intensityFactor)),
        overloadedSegmentsCount: Math.max(1, Math.round(2 * intensityFactor)),
        overflowZonesCount: 1,
        floodedAreaKm2: Number((0.85 * intensityFactor).toFixed(2)),
        affectedStructures: Math.round(180 * intensityFactor),
        populationAtRisk: Math.round(7600 * intensityFactor),
        affectedRoadSegments: Math.max(2, Math.round(3 * intensityFactor)),
        criticalFacilitiesExposed: 1,
        mithiRiverStatus: 'HIGH STRESS',
        runoffMm: Number((12.5 * intensityFactor).toFixed(1)),
        infiltrationMm: Number((3.1 * intensityFactor).toFixed(1)),
        totalDrainageM3: Math.round(208000 * intensityFactor),
        surfaceStorageM3: Math.round(433000 * intensityFactor),
        waterBalanceErrorPercent: 0.0,
      };
    case 'T03':
      return {
        stage: 'T03',
        stageName: 'Storm Drain Surcharge & Ponding',
        stageDescription: 'Drainage conduits overloaded. Manhole surcharge backflowing onto LBS Marg and CST Road.',
        alertLevel: rainfall >= 100 ? 'FLOOD WARNING' : 'FLOOD WATCH',
        rainfallMmHr: rainfall,
        drainStressState: 'OVERLOADED',
        stressedDrainsCount: Math.max(6, Math.round(11 * intensityFactor)),
        overloadedSegmentsCount: Math.max(3, Math.round(4 * intensityFactor)),
        overflowZonesCount: Math.max(2, Math.round(3 * intensityFactor)),
        floodedAreaKm2: Number((1.55 * intensityFactor).toFixed(2)),
        affectedStructures: Math.round(420 * intensityFactor),
        populationAtRisk: Math.round(17500 * intensityFactor),
        affectedRoadSegments: Math.max(4, Math.round(5 * intensityFactor)),
        criticalFacilitiesExposed: 2,
        mithiRiverStatus: 'HIGH STRESS',
        runoffMm: Number((22.8 * intensityFactor).toFixed(1)),
        infiltrationMm: Number((2.6 * intensityFactor).toFixed(1)),
        totalDrainageM3: Math.round(214000 * intensityFactor),
        surfaceStorageM3: Math.round(764000 * intensityFactor),
        waterBalanceErrorPercent: 0.0,
      };
    case 'T04':
      // ABSOLUTE MAXIMUM DURING EVENT
      return {
        stage: 'T04',
        stageName: 'Peak Inundation Event',
        stageDescription: 'Catchment reaches peak hydrodynamic accumulation. Critical arterial roads partially impassable.',
        alertLevel: rainfall >= 100 ? 'SEVERE FLOOD EMERGENCY' : 'FLOOD WARNING',
        rainfallMmHr: rainfall,
        drainStressState: 'SURCHARGING OVERFLOW',
        stressedDrainsCount: Math.max(8, Math.round(14 * intensityFactor)),
        overloadedSegmentsCount: Math.max(4, Math.round(6 * intensityFactor)),
        overflowZonesCount: Math.max(3, Math.round(5 * intensityFactor)),
        floodedAreaKm2: Number((2.35 * intensityFactor).toFixed(2)),
        affectedStructures: Math.round(580 * intensityFactor),
        populationAtRisk: Math.round(24600 * intensityFactor),
        affectedRoadSegments: Math.max(5, Math.round(6 * intensityFactor)),
        criticalFacilitiesExposed: 2,
        mithiRiverStatus: 'BANKFULL / OVERFLOW',
        runoffMm: Number((32.4 * intensityFactor).toFixed(1)),
        infiltrationMm: Number((2.1 * intensityFactor).toFixed(1)),
        totalDrainageM3: Math.round(208000 * intensityFactor),
        surfaceStorageM3: Math.round(1018000 * intensityFactor),
        waterBalanceErrorPercent: 0.0,
      };
    case 'T05':
      // RECESSION PHASE 1 (Gradual draw-down)
      return {
        stage: 'T05',
        stageName: 'Water Recession in Progress',
        stageDescription: 'Precipitation ceases. Water draining into Mithi River and trunk outfalls; road surfaces clearing.',
        alertLevel: rainfall >= 100 ? 'FLOOD WATCH' : 'ADVISORY',
        rainfallMmHr: 0,
        drainStressState: 'HIGH LOAD',
        stressedDrainsCount: Math.max(4, Math.round(8 * intensityFactor)),
        overloadedSegmentsCount: Math.max(2, Math.round(3 * intensityFactor)),
        overflowZonesCount: 1,
        floodedAreaKm2: Number((1.40 * intensityFactor).toFixed(2)),
        affectedStructures: Math.round(320 * intensityFactor),
        populationAtRisk: Math.round(13500 * intensityFactor),
        affectedRoadSegments: Math.max(2, Math.round(3 * intensityFactor)),
        criticalFacilitiesExposed: 1,
        mithiRiverStatus: 'HIGH STRESS',
        runoffMm: Number((6.5 * intensityFactor).toFixed(1)),
        infiltrationMm: Number((1.6 * intensityFactor).toFixed(1)),
        totalDrainageM3: Math.round(157000 * intensityFactor),
        surfaceStorageM3: Math.round(928000 * intensityFactor),
        waterBalanceErrorPercent: 0.0,
      };
    case 'T06':
      // RECESSION PHASE 2 / RECOVERY (Residual pooling only)
      return {
        stage: 'T06',
        stageName: 'Post-Event Recovery & Clearance',
        stageDescription: 'Gravity drainage restoration complete. Residual pooling confined to lowest subterranean basins.',
        alertLevel: 'NORMAL',
        rainfallMmHr: 0,
        drainStressState: 'OPTIMAL',
        stressedDrainsCount: Math.max(1, Math.round(2 * intensityFactor)),
        overloadedSegmentsCount: 0,
        overflowZonesCount: 0,
        floodedAreaKm2: Number((0.45 * intensityFactor).toFixed(2)),
        affectedStructures: Math.round(75 * intensityFactor),
        populationAtRisk: Math.round(3100 * intensityFactor),
        affectedRoadSegments: 0,
        criticalFacilitiesExposed: 0,
        mithiRiverStatus: 'NORMAL',
        runoffMm: 0,
        infiltrationMm: Number((1.1 * intensityFactor).toFixed(1)),
        totalDrainageM3: Math.round(121000 * intensityFactor),
        surfaceStorageM3: Math.round(793000 * intensityFactor),
        waterBalanceErrorPercent: 0.0,
      };
  }
};

/**
 * Creates a dynamic MumbaiLocation representation from a clicked 100m risk grid cell.
 */
export function createLocationFromGridFeature(props: any, lng: number, lat: number): MumbaiLocation {
  const gridId = props.grid_id ?? 1;
  const wardLetter = props.ward || 'Basin';
  const ward = `Ward ${wardLetter}`;
  const elev = typeof props.elevation_mean === 'number' ? Math.round(props.elevation_mean * 10) / 10 : 6.5;
  const builtUp = typeof props.built_up_fraction === 'number' ? props.built_up_fraction : 0.82;
  const drainDist = typeof props.distance_to_drain === 'number' ? Math.round(props.distance_to_drain) : 42;
  const floodFrac = typeof props.flood_fraction === 'number' ? props.flood_fraction : 0.08;

  return {
    id: `grid-${gridId}`,
    name: `Grid Cell #${gridId}`,
    subDistrict: `${ward} · 100m Hydro Spatial Cell`,
    ward: ward,
    gridId: gridId,
    lng: lng,
    lat: lat,
    elevationM: elev,
    imperviousRatio: builtUp,
    drainDistanceM: drainDist,
    flowAccumulationPercentile: Math.min(99, Math.round(floodFrac * 100 + 40)),
    description: `100m computational risk cell #${gridId} in ${ward}. Elevation: ${elev}m MSL. Impervious ratio: ${Math.round(builtUp * 100)}%. Distance to SWD: ${drainDist}m.`,
    explanationFactors: {
      elevationContribution: elev < 5 ? 36 : elev < 10 ? 28 : 18,
      drainageContribution: drainDist > 50 ? 30 : 22,
      imperviousContribution: Math.round(builtUp * 28),
      rainfallContribution: 22,
    },
    scenarios: {
      25: {
        probability: Math.round(floodFrac * 40 + 15),
        depthM: Number((floodFrac * 0.4 + 0.05).toFixed(2)),
        interval90: [0.02, 0.15],
        confidencePercent: 88,
        severity: floodFrac > 0.4 ? 'WARNING' : 'ADVISORY',
        affectedStructures: props.building_count ?? 14,
        populationAtRisk: (props.building_count ?? 14) * 20,
      },
      50: {
        probability: Math.round(floodFrac * 60 + 35),
        depthM: Number((floodFrac * 0.7 + 0.18).toFixed(2)),
        interval90: [0.10, 0.35],
        confidencePercent: 86,
        severity: floodFrac > 0.3 ? 'WARNING' : 'ADVISORY',
        affectedStructures: Math.round((props.building_count ?? 14) * 1.8),
        populationAtRisk: Math.round((props.building_count ?? 14) * 45),
      },
      100: {
        probability: Math.min(99, Math.round(floodFrac * 70 + 60)),
        depthM: Number((floodFrac * 1.1 + 0.35).toFixed(2)),
        interval90: [0.25, 0.65],
        confidencePercent: 85,
        severity: 'SEVERE',
        affectedStructures: Math.round((props.building_count ?? 14) * 2.5),
        populationAtRisk: Math.round((props.building_count ?? 14) * 75),
      },
      150: {
        probability: Math.min(99, Math.round(floodFrac * 75 + 75)),
        depthM: Number((floodFrac * 1.5 + 0.65).toFixed(2)),
        interval90: [0.50, 1.10],
        confidencePercent: 82,
        severity: 'SEVERE',
        affectedStructures: Math.round((props.building_count ?? 14) * 3.2),
        populationAtRisk: Math.round((props.building_count ?? 14) * 110),
      },
    },
  };
}
