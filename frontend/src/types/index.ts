export type SeverityLevel = 'SAFE' | 'ADVISORY' | 'WARNING' | 'SEVERE';

export interface RiskZone {
  id: string;
  name: string;
  ward: string;
  catchment: string;
  coordinates: { x: number; z: number }; // Relative coordinates in the 3D grid
  elevationMeters: number;
  imperviousPercent: number;
  drainProximityMeters: number;
  flowAccumulationIndex: number; // 0 - 100
  drainCapacityCms: number;
  // Dynamic simulation response across rainfall scenarios
  scenarioData: Record<number, {
    probability: number; // 0 - 100
    expectedDepthM: number;
    interval90: [number, number];
    severity: SeverityLevel;
    affectedStructures: number;
    populationAtRisk: number;
  }>;
  explanation: string;
}

export interface RainfallScenario {
  intensityMmHr: number;
  label: string;
  description: string;
  durationHours: number;
  totalRunoffEstimateM3: number;
  peakDrainStressPercent: number;
}

export interface SystemAlert {
  id: string;
  zoneId: string;
  zoneName: string;
  severity: SeverityLevel;
  metric: string;
  detail: string;
  timestamp: string;
  priorityIndex: number;
}

export interface DrainageNode {
  id: string;
  type: 'PRIMARY_OUTFALL' | 'MAJOR_TRUNK' | 'SECONDARY_CHANNEL' | 'MANHOLE';
  points: [number, number, number][]; // 3D line points [x, y, z]
  capacityCms: number;
  currentStressPercent: number;
  status: 'OPTIMAL' | 'CONGESTED' | 'OVERTOPPED';
}

export interface BuildingBlock {
  id: string;
  zoneId: string;
  x: number;
  z: number;
  width: number;
  depth: number;
  height: number;
  type: 'COMMERCIAL' | 'RESIDENTIAL' | 'CRITICAL_INFRA' | 'TRANSPORT';
  floodedAtRainfall: number; // threshold when water touches plinth
}

export interface HistoricalValidationData {
  eventDate: string;
  eventName: string;
  peakRainfallMm: number;
  metrics: {
    iou: number;
    precision: number;
    recall: number;
    f1Score: number;
    brierScore: number;
  };
  zones: {
    name: string;
    observedDepthM: number;
    predictedDepthM: number;
    differenceM: number;
    status: 'MATCH' | 'SLIGHT_OVER' | 'SLIGHT_UNDER';
  }[];
  disclaimer: string;
}

export interface LayerState {
  terrain: boolean;
  buildings: boolean;
  roads: boolean;
  stormwaterDrains: boolean;
  floodRisk: boolean;
  floodDepth: boolean;
  uncertainty: boolean;
  historicalFloodExtent: boolean;
}
