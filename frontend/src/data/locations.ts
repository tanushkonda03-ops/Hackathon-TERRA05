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
  gridId?: number;
  lng: number;
  lat: number;
  elevationM: number;
  imperviousRatio: number;
  drainDistanceM: number;
  flowAccumulationPercentile: number;
  description: string;
  citizenAdvice?: string;
  authorityAction?: string;
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
    name: 'Kurla West (L Ward)',
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
    citizenAdvice: 'Avoid LBS Marg and Kurla station underpass. Ground-floor residents move electrical appliances up.',
    authorityAction: 'Deploy 4 heavy dewatering pumps at Bail Bazar. Keep NDRF rescue boats on standby along Mithi riverbank.',
    explanationFactors: { elevationContribution: 34, drainageContribution: 27, imperviousContribution: 21, rainfallContribution: 18 },
    scenarios: {
      25: { probability: 24, depthM: 0.08, interval90: [0.03, 0.16], confidencePercent: 88, severity: 'ADVISORY', affectedStructures: 32, populationAtRisk: 1400 },
      50: { probability: 62, depthM: 0.31, interval90: [0.20, 0.44], confidencePercent: 86, severity: 'WARNING', affectedStructures: 165, populationAtRisk: 7900 },
      100: { probability: 91, depthM: 0.61, interval90: [0.44, 0.78], confidencePercent: 84, severity: 'SEVERE', affectedStructures: 580, populationAtRisk: 24600 },
      150: { probability: 98, depthM: 1.18, interval90: [0.94, 1.42], confidencePercent: 81, severity: 'SEVERE', affectedStructures: 1350, populationAtRisk: 52000 },
    },
  },
  {
    id: 'hindmata',
    name: 'Hindmata & Dadar (F-South Ward)',
    subDistrict: 'Dr. Ambedkar Road / Parel Basin',
    ward: 'F-South Ward',
    gridId: 19842,
    lng: 72.8423,
    lat: 19.0118,
    elevationM: 3.8,
    imperviousRatio: 0.96,
    drainDistanceM: 25,
    flowAccumulationPercentile: 92,
    description: 'Historic saucer-shaped topographic depression. Surface runoff from surrounding elevated ridges concentrates rapidly on Dr. Ambedkar Road.',
    citizenAdvice: 'Dr. Ambedkar Road traffic diverted to flyovers. Avoid walking through waterlogged subway junctions.',
    authorityAction: 'Activate underground holding tank pumps at Pramod Mahajan Park. Divert BEST buses via flyovers.',
    explanationFactors: { elevationContribution: 38, drainageContribution: 25, imperviousContribution: 22, rainfallContribution: 15 },
    scenarios: {
      25: { probability: 28, depthM: 0.12, interval90: [0.05, 0.20], confidencePercent: 89, severity: 'ADVISORY', affectedStructures: 45, populationAtRisk: 2100 },
      50: { probability: 74, depthM: 0.42, interval90: [0.28, 0.56], confidencePercent: 87, severity: 'WARNING', affectedStructures: 210, populationAtRisk: 9800 },
      100: { probability: 94, depthM: 0.78, interval90: [0.58, 0.95], confidencePercent: 85, severity: 'SEVERE', affectedStructures: 620, populationAtRisk: 28000 },
      150: { probability: 99, depthM: 1.35, interval90: [1.05, 1.60], confidencePercent: 82, severity: 'SEVERE', affectedStructures: 1480, populationAtRisk: 59000 },
    },
  },
  {
    id: 'sion',
    name: 'Sion Circle (F-North Ward)',
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
    citizenAdvice: 'Sion station underpass impassable. Use foot-over bridges and avoid Sion Talao junction.',
    authorityAction: 'Close railway subways. Start standby dewatering pumps at Sion Talao culvert outfall.',
    explanationFactors: { elevationContribution: 32, drainageContribution: 29, imperviousContribution: 20, rainfallContribution: 19 },
    scenarios: {
      25: { probability: 19, depthM: 0.05, interval90: [0.01, 0.12], confidencePercent: 90, severity: 'SAFE', affectedStructures: 14, populationAtRisk: 620 },
      50: { probability: 56, depthM: 0.26, interval90: [0.16, 0.38], confidencePercent: 87, severity: 'WARNING', affectedStructures: 110, populationAtRisk: 4800 },
      100: { probability: 88, depthM: 0.54, interval90: [0.38, 0.70], confidencePercent: 85, severity: 'SEVERE', affectedStructures: 390, populationAtRisk: 16500 },
      150: { probability: 96, depthM: 0.98, interval90: [0.76, 1.22], confidencePercent: 82, severity: 'SEVERE', affectedStructures: 890, populationAtRisk: 37000 },
    },
  },
  {
    id: 'milan_subway',
    name: 'Milan Subway (H-West Ward)',
    subDistrict: 'Santacruz Railway Underpass',
    ward: 'H-West Ward',
    gridId: 24150,
    lng: 72.8398,
    lat: 19.0845,
    elevationM: 3.2,
    imperviousRatio: 0.95,
    drainDistanceM: 20,
    flowAccumulationPercentile: 91,
    description: 'Severely sunken arterial underpass connecting Santacruz East and West beneath Western Railway corridor. Rapid stormwater runoff fills the subway pit.',
    citizenAdvice: 'Subway closed to vehicular traffic. Use Milan Flyover as the primary alternate route.',
    authorityAction: 'Activate automatic gate barriers to barricade subway entry. Run all 6 sump pumps continuously.',
    explanationFactors: { elevationContribution: 42, drainageContribution: 26, imperviousContribution: 18, rainfallContribution: 14 },
    scenarios: {
      25: { probability: 35, depthM: 0.25, interval90: [0.12, 0.40], confidencePercent: 92, severity: 'ADVISORY', affectedStructures: 8, populationAtRisk: 450 },
      50: { probability: 82, depthM: 0.75, interval90: [0.55, 0.95], confidencePercent: 89, severity: 'WARNING', affectedStructures: 42, populationAtRisk: 1800 },
      100: { probability: 97, depthM: 1.45, interval90: [1.15, 1.75], confidencePercent: 86, severity: 'SEVERE', affectedStructures: 120, populationAtRisk: 5200 },
      150: { probability: 99, depthM: 2.10, interval90: [1.80, 2.45], confidencePercent: 84, severity: 'SEVERE', affectedStructures: 280, populationAtRisk: 11500 },
    },
  },
  {
    id: 'andheri_subway',
    name: 'Andheri Subway (K-West Ward)',
    subDistrict: 'SV Road / Railway Underpass',
    ward: 'K-West Ward',
    gridId: 28540,
    lng: 72.8465,
    lat: 19.1198,
    elevationM: 3.5,
    imperviousRatio: 0.97,
    drainDistanceM: 18,
    flowAccumulationPercentile: 93,
    description: 'Bottleneck vehicular subway connecting Andheri East & West. Heavy overland runoff from SV Road cascades into the low subway pit.',
    citizenAdvice: 'Avoid Andheri Subway during downpours. Divert via Gokhale Bridge or Captain Gore Flyover.',
    authorityAction: 'Deploy traffic police for early barricading. Engage high-capacity Mogra nullah discharge pumps.',
    explanationFactors: { elevationContribution: 40, drainageContribution: 27, imperviousContribution: 19, rainfallContribution: 14 },
    scenarios: {
      25: { probability: 30, depthM: 0.20, interval90: [0.08, 0.35], confidencePercent: 91, severity: 'ADVISORY', affectedStructures: 12, populationAtRisk: 600 },
      50: { probability: 78, depthM: 0.65, interval90: [0.45, 0.85], confidencePercent: 88, severity: 'WARNING', affectedStructures: 55, populationAtRisk: 2400 },
      100: { probability: 96, depthM: 1.30, interval90: [1.05, 1.60], confidencePercent: 85, severity: 'SEVERE', affectedStructures: 150, populationAtRisk: 6800 },
      150: { probability: 99, depthM: 1.95, interval90: [1.65, 2.30], confidencePercent: 83, severity: 'SEVERE', affectedStructures: 340, populationAtRisk: 14000 },
    },
  },
  {
    id: 'bkc',
    name: 'BKC (H-East Ward)',
    subDistrict: 'G-Block Financial District',
    ward: 'H-East Ward',
    gridId: 22686,
    lng: 72.8656,
    lat: 19.0652,
    elevationM: 6.8,
    imperviousRatio: 0.92,
    drainDistanceM: 40,
    flowAccumulationPercentile: 79,
    description: 'Engineered commercial hub built on reclaimed marshland. Vakola Nullah overflow during spring high tides restricts local arterial drainage.',
    citizenAdvice: 'Expect waterlogging on CST Road. Corporate offices should verify basement flood gates.',
    authorityAction: 'Inspect Vakola Nullah tidal flap gates. Station mobile pump units near MCA club.',
    explanationFactors: { elevationContribution: 25, drainageContribution: 35, imperviousContribution: 25, rainfallContribution: 15 },
    scenarios: {
      25: { probability: 12, depthM: 0.03, interval90: [0.00, 0.08], confidencePercent: 92, severity: 'SAFE', affectedStructures: 6, populationAtRisk: 300 },
      50: { probability: 38, depthM: 0.18, interval90: [0.10, 0.28], confidencePercent: 89, severity: 'ADVISORY', affectedStructures: 45, populationAtRisk: 2100 },
      100: { probability: 72, depthM: 0.42, interval90: [0.28, 0.58], confidencePercent: 86, severity: 'WARNING', affectedStructures: 180, populationAtRisk: 8400 },
      150: { probability: 90, depthM: 0.78, interval90: [0.58, 1.02], confidencePercent: 83, severity: 'SEVERE', affectedStructures: 420, populationAtRisk: 19000 },
    },
  },
  {
    id: 'malad_subway',
    name: 'Malad Subway (P-North Ward)',
    subDistrict: 'SV Road / Marve Road Junction',
    ward: 'P-North Ward',
    gridId: 34120,
    lng: 72.8480,
    lat: 19.1865,
    elevationM: 4.1,
    imperviousRatio: 0.91,
    drainDistanceM: 28,
    flowAccumulationPercentile: 86,
    description: 'Western suburb pinch point. Runoff from Malad hill slopes bottlenecks at the railway underpass into local storm drains.',
    citizenAdvice: 'Malad Subway closed when rain exceeds 40 mm/hr. Divert traffic to Mithowki Flyover.',
    authorityAction: 'Deploy 2 standby pumps at SV Road subway junction. Clear silt traps in surrounding feeder nullahs.',
    explanationFactors: { elevationContribution: 36, drainageContribution: 28, imperviousContribution: 20, rainfallContribution: 16 },
    scenarios: {
      25: { probability: 22, depthM: 0.10, interval90: [0.04, 0.18], confidencePercent: 90, severity: 'ADVISORY', affectedStructures: 18, populationAtRisk: 800 },
      50: { probability: 68, depthM: 0.38, interval90: [0.24, 0.52], confidencePercent: 87, severity: 'WARNING', affectedStructures: 95, populationAtRisk: 4200 },
      100: { probability: 92, depthM: 0.72, interval90: [0.52, 0.92], confidencePercent: 84, severity: 'SEVERE', affectedStructures: 320, populationAtRisk: 13800 },
      150: { probability: 98, depthM: 1.25, interval90: [0.98, 1.55], confidencePercent: 81, severity: 'SEVERE', affectedStructures: 780, populationAtRisk: 31000 },
    },
  },
  {
    id: 'dharavi',
    name: 'Dharavi (G-North Ward)',
    subDistrict: '90-Ft Road / Mahim Creek Basin',
    ward: 'G-North Ward',
    gridId: 21180,
    lng: 72.8550,
    lat: 19.0430,
    elevationM: 3.9,
    imperviousRatio: 0.96,
    drainDistanceM: 35,
    flowAccumulationPercentile: 90,
    description: 'High-density settlement adjacent to Mahim Creek mangrove wetlands. Micro-relief depressions and tidal ingress hinder gravity drainage.',
    citizenAdvice: 'Ground-floor workshops and homes should raise machinery. Avoid stepping near unbarricaded drain channels.',
    authorityAction: 'Station mobile evacuation boats on stand-by. Inspect Mahim Creek outfall flap gates.',
    explanationFactors: { elevationContribution: 30, drainageContribution: 32, imperviousContribution: 24, rainfallContribution: 14 },
    scenarios: {
      25: { probability: 26, depthM: 0.09, interval90: [0.04, 0.16], confidencePercent: 88, severity: 'ADVISORY', affectedStructures: 85, populationAtRisk: 3800 },
      50: { probability: 70, depthM: 0.35, interval90: [0.22, 0.48], confidencePercent: 85, severity: 'WARNING', affectedStructures: 340, populationAtRisk: 16500 },
      100: { probability: 93, depthM: 0.68, interval90: [0.50, 0.88], confidencePercent: 83, severity: 'SEVERE', affectedStructures: 980, populationAtRisk: 46000 },
      150: { probability: 99, depthM: 1.20, interval90: [0.95, 1.48], confidencePercent: 80, severity: 'SEVERE', affectedStructures: 2200, populationAtRisk: 95000 },
    },
  },
  {
    id: 'ghatkopar',
    name: 'Ghatkopar West (N Ward)',
    subDistrict: 'LBS Marg / Gandhi Nagar',
    ward: 'N Ward',
    gridId: 28400,
    lng: 72.9050,
    lat: 19.0880,
    elevationM: 5.6,
    imperviousRatio: 0.91,
    drainDistanceM: 45,
    flowAccumulationPercentile: 82,
    description: 'Foothill runoff from surrounding elevated ridges rapidly surges into the low-lying LBS Marg corridor and railway culverts.',
    citizenAdvice: 'Expect traffic crawling on LBS Marg. Railway commuter delays likely at Ghatkopar station.',
    authorityAction: 'Deploy 3 pumps at Gandhi Nagar junction. Clear stormwater silt screens on eastern nullahs.',
    explanationFactors: { elevationContribution: 33, drainageContribution: 28, imperviousContribution: 21, rainfallContribution: 18 },
    scenarios: {
      25: { probability: 16, depthM: 0.04, interval90: [0.01, 0.10], confidencePercent: 91, severity: 'SAFE', affectedStructures: 18, populationAtRisk: 750 },
      50: { probability: 52, depthM: 0.22, interval90: [0.12, 0.34], confidencePercent: 88, severity: 'WARNING', affectedStructures: 92, populationAtRisk: 3900 },
      100: { probability: 84, depthM: 0.48, interval90: [0.32, 0.65], confidencePercent: 85, severity: 'SEVERE', affectedStructures: 310, populationAtRisk: 13400 },
      150: { probability: 95, depthM: 0.88, interval90: [0.65, 1.12], confidencePercent: 82, severity: 'SEVERE', affectedStructures: 740, populationAtRisk: 31000 },
    },
  },
  {
    id: 'chembur',
    name: 'Chembur Amar Mahal (M-West Ward)',
    subDistrict: 'Eastern Express Highway / Shell Colony',
    ward: 'M-West Ward',
    gridId: 23900,
    lng: 72.8990,
    lat: 19.0620,
    elevationM: 4.8,
    imperviousRatio: 0.90,
    drainDistanceM: 38,
    flowAccumulationPercentile: 84,
    description: 'Major arterial traffic intersection in Eastern Suburbs. Low relief and railway line embankment obstruct gravity outflow.',
    citizenAdvice: 'Amar Mahal junction and Shell Colony experience slow traffic. Use elevated Santa Cruz–Chembur Link Road (SCLR).',
    authorityAction: 'Deploy traffic marshals at Amar Mahal roundabout. Run dewatering pumps at Shell Colony culvert.',
    explanationFactors: { elevationContribution: 31, drainageContribution: 30, imperviousContribution: 22, rainfallContribution: 17 },
    scenarios: {
      25: { probability: 18, depthM: 0.05, interval90: [0.01, 0.11], confidencePercent: 90, severity: 'SAFE', affectedStructures: 15, populationAtRisk: 650 },
      50: { probability: 54, depthM: 0.24, interval90: [0.14, 0.36], confidencePercent: 87, severity: 'WARNING', affectedStructures: 85, populationAtRisk: 3600 },
      100: { probability: 86, depthM: 0.50, interval90: [0.35, 0.68], confidencePercent: 84, severity: 'SEVERE', affectedStructures: 290, populationAtRisk: 12800 },
      150: { probability: 96, depthM: 0.92, interval90: [0.70, 1.18], confidencePercent: 81, severity: 'SEVERE', affectedStructures: 710, populationAtRisk: 30000 },
    },
  },
];

export const getTimelineImpactMetrics = (
  rainfallMmHr: number,
  stepIndex: number
): TimelineImpactMetrics => {
  const stages: TimelineImpactMetrics[] = [
    {
      stage: 'T00',
      stageName: 'T+00m: Pre-Storm Baseline',
      stageDescription: 'Drains flowing with dry-weather baseflow. All gravity outfalls open to sea.',
      alertLevel: 'NORMAL',
      rainfallMmHr: 0,
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
      infiltrationMm: 0,
      totalDrainageM3: 0,
      surfaceStorageM3: 0,
      waterBalanceErrorPercent: 0.02,
    },
    {
      stage: 'T01',
      stageName: 'T+15m: First Flush Inflow',
      stageDescription: 'Storm runoff saturates soil. Surface drains reach 30% hydraulic capacity.',
      alertLevel: 'ADVISORY',
      rainfallMmHr: Math.round(rainfallMmHr * 0.4),
      drainStressState: 'LOADING',
      stressedDrainsCount: 14,
      overloadedSegmentsCount: 2,
      overflowZonesCount: 3,
      floodedAreaKm2: 0.2,
      affectedStructures: 45,
      populationAtRisk: 1800,
      affectedRoadSegments: 4,
      criticalFacilitiesExposed: 0,
      mithiRiverStatus: 'NORMAL',
      runoffMm: Math.round(rainfallMmHr * 0.12),
      infiltrationMm: Math.round(rainfallMmHr * 0.15),
      totalDrainageM3: 42000,
      surfaceStorageM3: 12000,
      waterBalanceErrorPercent: 0.04,
    },
    {
      stage: 'T02',
      stageName: 'T+30m: Drain Capacity Saturation',
      stageDescription: 'Major trunk conduits reach 85% capacity. Low-lying roadside gutters begin backing up.',
      alertLevel: 'FLOOD WATCH',
      rainfallMmHr: Math.round(rainfallMmHr * 0.8),
      drainStressState: 'HIGH LOAD',
      stressedDrainsCount: 48,
      overloadedSegmentsCount: 12,
      overflowZonesCount: 18,
      floodedAreaKm2: 0.8,
      affectedStructures: 180,
      populationAtRisk: 7500,
      affectedRoadSegments: 14,
      criticalFacilitiesExposed: 1,
      mithiRiverStatus: 'ELEVATED',
      runoffMm: Math.round(rainfallMmHr * 0.38),
      infiltrationMm: Math.round(rainfallMmHr * 0.22),
      totalDrainageM3: 145000,
      surfaceStorageM3: 68000,
      waterBalanceErrorPercent: 0.05,
    },
    {
      stage: 'T03',
      stageName: 'T+45m: Pipe Surcharging Peak',
      stageDescription: 'Manholes pop into pressure flow. Water surcharges up from underpasses and railway culverts.',
      alertLevel: 'FLOOD WARNING',
      rainfallMmHr: rainfallMmHr,
      drainStressState: 'OVERLOADED',
      stressedDrainsCount: 88,
      overloadedSegmentsCount: 34,
      overflowZonesCount: 42,
      floodedAreaKm2: 1.9,
      affectedStructures: 420,
      populationAtRisk: 18500,
      affectedRoadSegments: 36,
      criticalFacilitiesExposed: 3,
      mithiRiverStatus: 'HIGH STRESS',
      runoffMm: Math.round(rainfallMmHr * 0.68),
      infiltrationMm: Math.round(rainfallMmHr * 0.25),
      totalDrainageM3: 285000,
      surfaceStorageM3: 195000,
      waterBalanceErrorPercent: 0.06,
    },
    {
      stage: 'T04',
      stageName: 'T+60m: Peak Inundation Extent',
      stageDescription: 'Maximum water depth reached across low basins. Overland flow pools into major depressions.',
      alertLevel: 'SEVERE FLOOD EMERGENCY',
      rainfallMmHr: Math.round(rainfallMmHr * 1.05),
      drainStressState: 'SURCHARGING OVERFLOW',
      stressedDrainsCount: 120,
      overloadedSegmentsCount: 52,
      overflowZonesCount: 65,
      floodedAreaKm2: 3.2,
      affectedStructures: 780,
      populationAtRisk: 34000,
      affectedRoadSegments: 58,
      criticalFacilitiesExposed: 5,
      mithiRiverStatus: 'BANKFULL / OVERFLOW',
      runoffMm: Math.round(rainfallMmHr * 0.85),
      infiltrationMm: Math.round(rainfallMmHr * 0.26),
      totalDrainageM3: 390000,
      surfaceStorageM3: 340000,
      waterBalanceErrorPercent: 0.08,
    },
    {
      stage: 'T05',
      stageName: 'T+90m: Slow Gravity Recession',
      stageDescription: 'Rainfall ceases. Gravity drainage slowly resumes as tide recedes.',
      alertLevel: 'FLOOD WATCH',
      rainfallMmHr: Math.round(rainfallMmHr * 0.2),
      drainStressState: 'HIGH LOAD',
      stressedDrainsCount: 65,
      overloadedSegmentsCount: 22,
      overflowZonesCount: 30,
      floodedAreaKm2: 1.8,
      affectedStructures: 390,
      populationAtRisk: 16500,
      affectedRoadSegments: 28,
      criticalFacilitiesExposed: 2,
      mithiRiverStatus: 'HIGH STRESS',
      runoffMm: Math.round(rainfallMmHr * 0.25),
      infiltrationMm: Math.round(rainfallMmHr * 0.28),
      totalDrainageM3: 470000,
      surfaceStorageM3: 180000,
      waterBalanceErrorPercent: 0.06,
    },
    {
      stage: 'T06',
      stageName: 'T+120m: Drainage Clearance',
      stageDescription: 'Major road arteries cleared. Residual ponding localized only in sunken basements.',
      alertLevel: 'ADVISORY',
      rainfallMmHr: 0,
      drainStressState: 'LOADING',
      stressedDrainsCount: 18,
      overloadedSegmentsCount: 4,
      overflowZonesCount: 8,
      floodedAreaKm2: 0.4,
      affectedStructures: 85,
      populationAtRisk: 3600,
      affectedRoadSegments: 8,
      criticalFacilitiesExposed: 0,
      mithiRiverStatus: 'ELEVATED',
      runoffMm: 0,
      infiltrationMm: Math.round(rainfallMmHr * 0.28),
      totalDrainageM3: 540000,
      surfaceStorageM3: 45000,
      waterBalanceErrorPercent: 0.03,
    },
  ];

  const clampedIndex = Math.max(0, Math.min(stepIndex, stages.length - 1));
  return stages[clampedIndex];
};

export function createLocationFromGridFeature(props: any, lng: number, lat: number): MumbaiLocation {
  const gridId = props.grid_id ?? 0;
  const ward = props.ward ? (props.ward + ' Ward') : 'Mumbai Ward';
  const elev = props.elevation_mean ?? 5.0;
  const builtUp = props.built_up_fraction ?? 0.85;
  const drainDist = props.distance_to_drain ?? 45.0;

  return {
    id: 'grid_' + gridId,
    name: 'Cell #' + gridId + ' (' + ward + ')',
    subDistrict: ward + ' Drainage Catchment',
    ward: ward,
    gridId: gridId,
    lng: lng,
    lat: lat,
    elevationM: Math.round(elev * 10) / 10,
    imperviousRatio: Math.round(builtUp * 100) / 100,
    drainDistanceM: Math.round(drainDist),
    flowAccumulationPercentile: Math.min(99, Math.max(20, Math.round(props.flow_accumulation_log ? props.flow_accumulation_log * 12 : 65))),
    description: '100m grid cell in ' + ward + '. Elevation: ' + (Math.round(elev*10)/10) + 'm MSL, Built-up Impervious: ' + Math.round(builtUp*100) + '%, Distance to drain: ' + Math.round(drainDist) + 'm.',
    citizenAdvice: builtUp > 0.8 ? 'High built-up area: Expect rapid road runoff accumulation.' : 'Low built-up area: Infiltration absorbs initial light rainfall.',
    authorityAction: drainDist > 50 ? 'Low local drain density: Ensure portable dewatering pumps are staged nearby.' : 'Drain nearby: Verify catchpit grates are free of debris.',
    explanationFactors: {
      elevationContribution: 35,
      drainageContribution: 28,
      imperviousContribution: 22,
      rainfallContribution: 15,
    },
    scenarios: {
      25: { probability: 15, depthM: 0.04, interval90: [0.01, 0.09], confidencePercent: 90, severity: 'SAFE', affectedStructures: 10, populationAtRisk: 400 },
      50: { probability: 48, depthM: 0.20, interval90: [0.10, 0.32], confidencePercent: 88, severity: 'WARNING', affectedStructures: 60, populationAtRisk: 2500 },
      100: { probability: 82, depthM: 0.45, interval90: [0.30, 0.62], confidencePercent: 85, severity: 'SEVERE', affectedStructures: 220, populationAtRisk: 9500 },
      150: { probability: 94, depthM: 0.82, interval90: [0.60, 1.05], confidencePercent: 82, severity: 'SEVERE', affectedStructures: 520, populationAtRisk: 22000 },
    },
  };
}
