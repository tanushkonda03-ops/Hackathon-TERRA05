import React, { useState, useEffect, useCallback } from 'react';
import { 
  Building2, 
  MapPin, 
  Droplets, 
  Compass, 
  AlertTriangle,
  ShieldAlert,
  HelpCircle,
  Clock,
  ArrowRight,
  Cpu,
  RefreshCw,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Info,
  X
} from 'lucide-react';
import { MumbaiLocation, TimelineImpactMetrics } from '../data/locations';
import { getPrediction, PredictionResponse, SimulationResponse } from '../services/api';

interface IntelligencePanelProps {
  location: MumbaiLocation;
  rainfall: number;
  timelineMetrics?: TimelineImpactMetrics;
  simulationData?: SimulationResponse | null;
  simStepIndex?: number;
  onClose?: () => void;
}

export const IntelligencePanel: React.FC<IntelligencePanelProps> = ({
  location,
  rainfall,
  timelineMetrics: propTimelineMetrics,
  simulationData,
  simStepIndex = 0,
  onClose,
}) => {
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [predictionLoading, setPredictionLoading] = useState<boolean>(false);
  const [predictionError, setPredictionError] = useState<string | null>(null);
  const [showLimitations, setShowLimitations] = useState<boolean>(false);

  const fetchPrediction = useCallback(async (signal?: AbortSignal) => {
    if (!location?.gridId) {
      setPrediction(null);
      return;
    }
    setPredictionLoading(true);
    setPredictionError(null);
    try {
      const res = await getPrediction({ grid_id: location.gridId }, signal);
      setPrediction(res);
      setPredictionLoading(false);
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        console.warn('[TERRA05] Prediction fetch warning:', err);
        setPredictionError(err.message || 'Model service unavailable');
        setPredictionLoading(false);
      }
    }
  }, [location?.gridId]);

  useEffect(() => {
    const controller = new AbortController();
    fetchPrediction(controller.signal);
    return () => {
      controller.abort();
    };
  }, [fetchPrediction]);

  if (!location) return null;

  const timelineMetrics: TimelineImpactMetrics = propTimelineMetrics || {
    stage: 'T04',
    stageName: 'Peak Inundation Event',
    stageDescription: 'Catchment reaches maximum water accumulation.',
    alertLevel: 'FLOOD WARNING',
    rainfallMmHr: rainfall || 100,
    drainStressState: 'OVERLOADED',
    stressedDrainsCount: 11,
    overloadedSegmentsCount: 4,
    overflowZonesCount: 3,
    floodedAreaKm2: 2.35,
    affectedStructures: 580,
    populationAtRisk: 24600,
    affectedRoadSegments: 6,
    criticalFacilitiesExposed: 2,
    mithiRiverStatus: 'HIGH STRESS',
  };

  const scenarioData = location.scenarios?.[rainfall] || location.scenarios?.[100] || {
    probability: 91,
    depthM: 0.61,
    interval90: [0.44, 0.78],
    confidencePercent: 86,
    severity: 'SEVERE',
    affectedStructures: 580,
    populationAtRisk: 24600,
  };

  const xai = location.explanationFactors || {
    elevationContribution: 34,
    drainageContribution: 27,
    imperviousContribution: 21,
    rainfallContribution: 18,
  };

  // Match simulation cell for the selected location (by exact gridId or proximity)
  const simCell = simulationData?.cells?.find((c) => c.grid_id === location.gridId) ||
    simulationData?.cells?.find((c) => {
      const dLat = c.centroid_lat - location.lat;
      const dLng = c.centroid_lng - location.lng;
      return (dLat * dLat + dLng * dLng) < 0.0004;
    });

  const step = Math.min(
    Math.max(0, simStepIndex),
    (simulationData?.timesteps?.length || 1) - 1
  );
  const currentSimStepMetrics = simulationData?.timesteps?.[step];
  const simDepth = simCell ? (simCell.depth_by_timestep[step] ?? 0) : undefined;
  const simMaxDepth = simCell?.max_depth_m;

  // Determine current timeline alert color styling
  let alertBadgeClass = 'bg-slate-50 text-slate-700 border-slate-200';
  let alertIconColor = 'text-slate-600';
  if (timelineMetrics.alertLevel === 'SEVERE FLOOD EMERGENCY') {
    alertBadgeClass = 'bg-rose-50 text-rose-800 border-rose-300';
    alertIconColor = 'text-rose-600';
  } else if (timelineMetrics.alertLevel === 'FLOOD WARNING') {
    alertBadgeClass = 'bg-amber-50 text-amber-800 border-amber-300';
    alertIconColor = 'text-amber-600';
  } else if (timelineMetrics.alertLevel === 'FLOOD WATCH') {
    alertBadgeClass = 'bg-amber-50/70 text-amber-700 border-amber-200';
    alertIconColor = 'text-amber-500';
  } else if (timelineMetrics.alertLevel === 'ADVISORY') {
    alertBadgeClass = 'bg-sky-50 text-sky-800 border-sky-200';
    alertIconColor = 'text-sky-600';
  }

  return (
    <div 
      className="w-full h-full bg-white flex flex-col justify-between overflow-y-auto select-none"
    >
      <div className="p-3.5 space-y-3.5">
        {/* Compact Operational Alert Banner */}
        <div className={`px-3 py-2 rounded-lg border text-xs font-mono font-bold flex items-center justify-between shadow-gis-xs transition-colors ${alertBadgeClass}`}>
          <div className="flex items-center space-x-1.5">
            <ShieldAlert className={`w-4 h-4 shrink-0 ${alertIconColor}`} />
            <span className="tracking-wide text-[11px]">{timelineMetrics.alertLevel}</span>
          </div>
          <span className="text-[10px] font-semibold text-slate-600 bg-white/80 border border-slate-200/80 px-1.5 py-0.5 rounded shadow-gis-xs">
            {timelineMetrics.stage}
          </span>
        </div>

        {/* Location Title & Subtitle */}
        <div className="border-b border-slate-100 pb-2.5">
          <div className="flex items-center justify-between">
            <span className="text-[9.5px] font-mono uppercase tracking-wider text-slate-400 font-bold">
              SELECTED AREA
            </span>
            <div className="flex items-center space-x-1.5">
              <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                {prediction?.ward ? `Ward ${prediction.ward}` : location.ward}
              </span>
              {onClose && (
                <button
                  onClick={onClose}
                  aria-label="Close Intelligence Panel"
                  className="p-0.5 rounded text-slate-400 hover:text-slate-800 hover:bg-slate-100 transition-colors"
                  title="Close Panel"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
          <h2 className="text-base font-bold text-slate-900 mt-0.5 tracking-tight">
            {location.name}
          </h2>
          <div className="text-xs text-slate-500 flex items-center space-x-1 mt-0.5">
            <MapPin className="w-3.5 h-3.5 text-sky-600 shrink-0" />
            <span className="truncate">{location.subDistrict}</span>
          </div>
        </div>

        {/* Layman Action & Guidance Cards */}
        {location.citizenAdvice && (
          <div className="p-2.5 rounded-lg bg-sky-50/70 border border-sky-200/80 text-xs space-y-1 shadow-gis-xs">
            <div className="flex items-center space-x-1.5 text-sky-900 font-bold text-[11px]">
              <Info className="w-3 h-3 text-sky-700 shrink-0" />
              <span>Citizen Advisory</span>
            </div>
            <p className="text-[11px] text-slate-700 leading-relaxed">
              {location.citizenAdvice}
            </p>
          </div>
        )}

        {location.authorityAction && (
          <div className="p-2.5 rounded-lg bg-amber-50/70 border border-amber-200/80 text-xs space-y-1 shadow-gis-xs">
            <div className="flex items-center space-x-1.5 text-amber-900 font-bold text-[11px]">
              <AlertTriangle className="w-3 h-3 text-amber-700 shrink-0" />
              <span>Municipal (BMC) Deployment</span>
            </div>
            <p className="text-[11px] text-slate-700 leading-relaxed">
              {location.authorityAction}
            </p>
          </div>
        )}

        {/* ML Flood Susceptibility Card (FastAPI Backend Model) */}
        <div className="p-3 rounded-lg bg-slate-50/80 border border-slate-200 shadow-gis-xs space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-1.5">
              <Cpu className="w-3.5 h-3.5 text-sky-700" />
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-700">
                FLOOD RISK ESTIMATE
              </span>
            </div>
            {predictionLoading ? (
              <span className="flex items-center space-x-1 text-[9px] font-mono text-sky-600 animate-pulse">
                <RefreshCw className="w-3 h-3 animate-spin" />
                <span>QUERYING...</span>
              </span>
            ) : prediction ? (
              <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                ESTIMATE READY
              </span>
            ) : predictionError ? (
              <button
                onClick={() => fetchPrediction()}
                className="flex items-center space-x-0.5 text-[9px] font-mono text-rose-600 hover:text-rose-800 underline"
                title="Retry fetching prediction"
              >
                <RefreshCw className="w-2.5 h-2.5" />
                <span>RETRY</span>
              </button>
            ) : (
              <span className="text-[9px] font-mono text-slate-400">STANDALONE</span>
            )}
          </div>

          {predictionLoading ? (
            <div className="py-2 space-y-1.5 animate-pulse">
              <div className="h-6 bg-slate-200 rounded w-1/2" />
              <div className="h-3 bg-slate-200 rounded w-3/4" />
            </div>
          ) : prediction ? (
            <div>
              <div className="flex items-baseline justify-between">
                <div>
                  <div className="text-2xl font-mono font-bold text-slate-900 tracking-tight">
                    {prediction.susceptibility_score.toFixed(4)}
                  </div>
                  <div className="text-[10px] font-semibold text-slate-700 mt-0.5">
                    Historical Susceptibility Score
                  </div>
                  <div className="text-[9px] font-mono text-slate-500">
                    Spatial Index · Grid #{prediction.grid_id}
                  </div>
                </div>
                <div className="text-right">
                  <span className={`text-[9.5px] font-mono font-bold px-2 py-0.5 rounded border inline-block ${
                    prediction.susceptibility_score >= 0.15
                      ? 'bg-rose-50 text-rose-700 border-rose-200'
                      : prediction.susceptibility_score >= 0.05
                      ? 'bg-amber-50 text-amber-700 border-amber-200'
                      : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  }`}>
                    {prediction.susceptibility_score >= 0.15 ? 'HIGH SUSCEPTIBILITY' : prediction.susceptibility_score >= 0.05 ? 'MODERATE' : 'LOW SUSCEPTIBILITY'}
                  </span>
                  <div className="text-[9px] font-mono text-slate-500 mt-1">
                    Ward {prediction.ward || location.ward}
                  </div>
                </div>
              </div>

              {/* Explicit scientific disclosure banner */}
              <div className="text-[9px] font-mono text-amber-800 bg-amber-50/90 border border-amber-200/90 px-2 py-1 rounded mt-2">
                <strong>Notice:</strong> Historical flood susceptibility score — not a flood probability.
              </div>

              {/* Model Artifact Tag */}
              <div className="text-[9px] font-mono text-slate-500 mt-2 pt-1.5 border-t border-slate-200/70 flex items-center justify-between">
                <span className="truncate max-w-[190px]" title={prediction.model_version}>
                  Pipeline: {prediction.model_version.replace('.joblib', '')}
                </span>
                <button
                  onClick={() => setShowLimitations(!showLimitations)}
                  className="text-sky-700 hover:text-sky-900 font-semibold flex items-center space-x-0.5 ml-1"
                >
                  <span>{showLimitations ? 'Hide' : 'Info'}</span>
                  {showLimitations ? <ChevronUp className="w-2.5 h-2.5" /> : <ChevronDown className="w-2.5 h-2.5" />}
                </button>
              </div>

              {/* Collapsible Scientific Limitations & Disclaimers */}
              {showLimitations && (
                <div className="mt-2 p-2 bg-white rounded border border-slate-200 text-[9px] font-mono text-slate-600 space-y-1">
                  <div className="font-bold text-slate-700 text-[10px]">Model Semantics & Bounds:</div>
                  <div>• {prediction.score_semantics}</div>
                  {prediction.limitations.map((lim, idx) => (
                    <div key={idx}>• {lim}</div>
                  ))}
                  <div className="text-sky-800 pt-0.5 font-medium border-t border-slate-100">
                    ℹ️ Hydraulic Engine: 2D diffusive overland runoff & cell accumulation prototype (100m grid, Horton infiltration, depression storage, drainage capacity). Independent from EPA-SWMM.
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-[11px] font-mono text-slate-500 py-1">
              {predictionError ? (
                <div className="text-rose-600 flex items-center space-x-1">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  <span className="text-[10px]">{predictionError}</span>
                </div>
              ) : (
                'Select a location or grid cell to fetch susceptibility prediction.'
              )}
            </div>
          )}
        </div>

        {/* Primary Metrics: Water Depth & Inundated Domain Extent */}
        <div className="grid grid-cols-2 gap-2.5">
          <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 shadow-gis-xs">
            <span className="text-[9.5px] uppercase font-mono text-slate-400 font-bold block">
              {simDepth !== undefined ? 'SIMULATED DEPTH' : 'EXPECTED DEPTH'}
            </span>
            <div className="text-xl font-mono font-bold text-sky-800 mt-0.5">
              {simDepth !== undefined ? simDepth.toFixed(2) : scenarioData.depthM.toFixed(2)}{' '}
              <span className="text-xs font-normal text-slate-500 font-sans">m</span>
            </div>
            <div className="text-[9px] text-slate-500 font-mono mt-0.5">
              {simMaxDepth !== undefined ? (
                <>Peak: <strong>{simMaxDepth.toFixed(2)}m</strong></>
              ) : (
                <>Peak: <strong>T+04</strong></>
              )}
            </div>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 shadow-gis-xs">
            <span className="text-[9.5px] uppercase font-mono text-slate-400 font-bold block">
              {currentSimStepMetrics ? 'INUNDATED AREA' : 'SIMULATION EXTENT'}
            </span>
            <div className="text-xl font-mono font-bold text-slate-900 mt-0.5">
              {currentSimStepMetrics ? (
                <>
                  {currentSimStepMetrics.inundated_area_km2.toFixed(2)}{' '}
                  <span className="text-xs font-normal text-slate-500 font-mono">km²</span>
                </>
              ) : (
                <>{scenarioData.probability}%</>
              )}
            </div>
            <div className="text-[9px] text-slate-500 font-mono mt-0.5">
              {currentSimStepMetrics ? (
                <span>{currentSimStepMetrics.inundated_cells_count} active cells</span>
              ) : (
                <div className="w-full bg-slate-200 h-1.5 rounded-full mt-1 overflow-hidden">
                  <div
                    className="bg-sky-600 h-full rounded-full"
                    style={{ width: `${scenarioData.probability}%` }}
                  />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Dynamic Impact Summary */}
        <div className="space-y-1.5 pt-1 border-t border-slate-100">
          <div className="flex items-center justify-between text-[9.5px] font-mono text-slate-400 uppercase font-bold">
            <span>URBAN IMPACT ESTIMATE</span>
            <span className="text-sky-700 font-semibold">{timelineMetrics.stageName}</span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs font-mono">
            <div className="p-2 rounded bg-slate-50/90 border border-slate-200">
              <span className="text-[8.5px] text-slate-400 block uppercase font-bold">STRUCTURES</span>
              <span className="font-bold text-slate-800">{timelineMetrics.affectedStructures} units</span>
            </div>
            <div className="p-2 rounded bg-slate-50/90 border border-slate-200">
              <span className="text-[8.5px] text-slate-400 block uppercase font-bold">POPULATION</span>
              <span className="font-bold text-slate-800">~{timelineMetrics.populationAtRisk.toLocaleString()}</span>
            </div>
            <div className="p-2 rounded bg-slate-50/90 border border-slate-200">
              <span className="text-[8.5px] text-slate-400 block uppercase font-bold">ROADS AT RISK</span>
              <span className="font-bold text-slate-800">{timelineMetrics.affectedRoadSegments} segments</span>
            </div>
            <div className="p-2 rounded bg-slate-50/90 border border-slate-200">
              <span className="text-[8.5px] text-slate-400 block uppercase font-bold">CRITICAL ASSETS</span>
              <span className="font-bold text-slate-800">{timelineMetrics.criticalFacilitiesExposed} facilities</span>
            </div>
          </div>
        </div>

        {/* Stormwater Conduit Capacity */}
        <div className="space-y-1.5 pt-1 border-t border-slate-100">
          <div className="flex items-center justify-between text-[9.5px] font-mono text-slate-400 uppercase font-bold">
            <span>STORMWATER NETWORK</span>
            <span className={`text-[10px] font-bold ${
              timelineMetrics.drainStressState === 'SURCHARGING OVERFLOW' ? 'text-rose-600' :
              timelineMetrics.drainStressState === 'OVERLOADED' ? 'text-amber-600' : 'text-sky-700'
            }`}>
              {timelineMetrics.drainStressState}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-1.5 text-center text-[10px] font-mono">
            <div className="p-1.5 rounded bg-slate-50 border border-slate-200">
              <span className="text-slate-400 block text-[8px] uppercase font-bold">STRESSED</span>
              <span className="font-bold text-slate-800">{timelineMetrics.stressedDrainsCount}</span>
            </div>
            <div className="p-1.5 rounded bg-slate-50 border border-slate-200">
              <span className="text-slate-400 block text-[8px] uppercase font-bold">OVERLOADED</span>
              <span className="font-bold text-slate-800">{timelineMetrics.overloadedSegmentsCount}</span>
            </div>
            <div className="p-1.5 rounded bg-slate-50 border border-slate-200">
              <span className="text-slate-400 block text-[8px] uppercase font-bold">OVERFLOW</span>
              <span className="font-bold text-slate-800">{timelineMetrics.overflowZonesCount}</span>
            </div>
          </div>
        </div>

        {/* Hydrology & Water Balance Section */}
        <div className="space-y-1.5 pt-1 border-t border-slate-100">
          <div className="flex items-center justify-between text-[9.5px] font-mono text-slate-400 uppercase font-bold">
            <span>HYDROLOGY & WATER BALANCE</span>
            <span className="text-[9.5px] font-bold text-sky-800 bg-sky-50 px-1.5 py-0.5 rounded border border-sky-200">
              {currentSimStepMetrics ? '2D SIMULATION' : 'SCENARIO ESTIMATE'}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-1.5 text-xs font-mono">
            <div className="p-2 rounded bg-slate-50 border border-slate-200">
              <span className="text-[8.5px] text-slate-400 block uppercase font-bold">RUNOFF EXCESS</span>
              <span className="font-bold text-slate-800">
                {currentSimStepMetrics
                  ? `${currentSimStepMetrics.rainfall_excess_mm.toFixed(1)} mm`
                  : `${timelineMetrics.runoffMm ?? 18.4} mm`}
              </span>
            </div>
            <div className="p-2 rounded bg-slate-50 border border-slate-200">
              <span className="text-[8.5px] text-slate-400 block uppercase font-bold">INFILTRATION</span>
              <span className="font-bold text-slate-800">
                {currentSimStepMetrics
                  ? `${currentSimStepMetrics.infiltrated_depth_mm.toFixed(1)} mm`
                  : `${timelineMetrics.infiltrationMm ?? 2.8} mm`}
              </span>
            </div>
            <div className="p-2 rounded bg-slate-50 border border-slate-200">
              <span className="text-[8.5px] text-slate-400 block uppercase font-bold">DRAIN REMOVAL</span>
              <span className="font-bold text-slate-800">
                {currentSimStepMetrics
                  ? `${Math.round(currentSimStepMetrics.drainage_removed_volume_m3).toLocaleString()} m³`
                  : `${(timelineMetrics.totalDrainageM3 ?? 185000).toLocaleString()} m³`}
              </span>
            </div>
            <div className="p-2 rounded bg-slate-50 border border-slate-200">
              <span className="text-[8.5px] text-slate-400 block uppercase font-bold">SURFACE STORAGE</span>
              <span className="font-bold text-sky-800">
                {currentSimStepMetrics
                  ? `${Math.round(currentSimStepMetrics.surface_storage_volume_m3).toLocaleString()} m³`
                  : `${(timelineMetrics.surfaceStorageM3 ?? 680000).toLocaleString()} m³`}
              </span>
            </div>
          </div>
          {simulationData?.water_balance && (
            <div className="text-[9px] font-mono text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-1 rounded flex items-center justify-between mt-1">
              <span>MASS CONSERVATION:</span>
              <span className="font-bold">100.0% (Error: {simulationData.water_balance.mass_balance_error_percent.toFixed(4)}%)</span>
            </div>
          )}
        </div>

        {/* Model Explanation: WHY THIS AREA? */}
        <div className="space-y-1.5 pt-1 border-t border-slate-100">
          <div className="flex items-center justify-between text-[9.5px] font-mono text-slate-400 uppercase font-bold">
            <span className="flex items-center space-x-1">
              <HelpCircle className="w-3 h-3 text-slate-400" />
              <span>WHY THIS AREA?</span>
            </span>
            <span className="text-slate-500 font-normal">Conf: {scenarioData.confidencePercent}%</span>
          </div>

          <div className="space-y-1.5 text-[10px] font-mono text-slate-700">
            <div>
              <div className="flex justify-between">
                <span>Elevation ({location.elevationM}m MSL)</span>
                <span className="font-bold text-slate-900">{xai.elevationContribution}%</span>
              </div>
              <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden mt-0.5">
                <div className="bg-sky-700 h-full rounded-full transition-all duration-300" style={{ width: `${xai.elevationContribution}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between">
                <span>Drain Distance ({location.drainDistanceM}m)</span>
                <span className="font-bold text-slate-900">{xai.drainageContribution}%</span>
              </div>
              <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden mt-0.5">
                <div className="bg-sky-600 h-full rounded-full transition-all duration-300" style={{ width: `${xai.drainageContribution}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between">
                <span>Impervious ({Math.round(location.imperviousRatio * 100)}%)</span>
                <span className="font-bold text-slate-900">{xai.imperviousContribution}%</span>
              </div>
              <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden mt-0.5">
                <div className="bg-sky-500 h-full rounded-full transition-all duration-300" style={{ width: `${xai.imperviousContribution}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between">
                <span>Rainfall ({rainfall} mm/hr)</span>
                <span className="font-bold text-slate-900">{xai.rainfallContribution}%</span>
              </div>
              <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden mt-0.5">
                <div className="bg-sky-400 h-full rounded-full transition-all duration-300" style={{ width: `${xai.rainfallContribution}%` }} />
              </div>
            </div>
          </div>
        </div>

        {/* 90% Prediction Interval */}
        <div className="space-y-1.5 pt-1 border-t border-slate-100">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-[9.5px] text-slate-400 uppercase font-bold">PREDICTION INTERVAL (90%)</span>
            <span className="text-xs font-bold text-slate-800">
              {scenarioData.interval90[0].toFixed(2)}m — {scenarioData.interval90[1].toFixed(2)}m
            </span>
          </div>

          <div className="relative h-2.5 bg-slate-100 rounded border border-slate-200 flex items-center px-1">
            <div
              className="absolute h-1.5 bg-sky-200 border-l-2 border-r-2 border-sky-600 rounded-xs"
              style={{
                left: `${Math.min(75, Math.max(10, scenarioData.interval90[0] * 50))}%`,
                right: `${Math.max(5, 100 - scenarioData.interval90[1] * 65)}%`,
              }}
            />
            <div
              className="absolute w-2 h-2.5 bg-sky-800 rounded-xs shadow-gis-xs -translate-x-1"
              style={{ left: `${Math.min(85, Math.max(15, scenarioData.depthM * 60))}%` }}
            />
          </div>
        </div>
      </div>

      {/* Flood Depth Scale Footnote */}
      <div className="p-3 bg-slate-50 border-t border-slate-200 text-xs">
        <div className="text-[9px] font-mono text-slate-400 font-bold uppercase mb-1.5 flex justify-between">
          <span>WATER DEPTH SURFACE COLOR</span>
          <span>0m — 1m+</span>
        </div>
        <div className="flex items-center space-x-1 text-[9px] font-mono">
          <span className="flex-1 text-center py-0.5 rounded bg-sky-100 text-sky-900 font-medium border border-sky-200/50">&lt;5cm</span>
          <span className="flex-1 text-center py-0.5 rounded bg-sky-300 text-sky-950 font-medium">15cm</span>
          <span className="flex-1 text-center py-0.5 rounded bg-sky-500 text-white font-medium">30cm</span>
          <span className="flex-1 text-center py-0.5 rounded bg-sky-700 text-white font-medium">60cm</span>
          <span className="flex-1 text-center py-0.5 rounded bg-sky-900 text-white font-medium">&gt;1m</span>
        </div>
      </div>
    </div>
  );
};
