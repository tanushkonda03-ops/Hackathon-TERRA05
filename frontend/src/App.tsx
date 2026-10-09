import React, { useState, useEffect } from 'react';
import { MapboxMumbai } from './components/MapboxMumbai';
import { IntelligencePanel } from './components/IntelligencePanel';
import { NavigationRail, NavTabId } from './components/NavigationRail';
import { MapLayersControl } from './components/MapLayersControl';
import { HistoricalValidationView } from './components/HistoricalValidationView';
import { DataLayersView } from './components/DataLayersView';
import { ArchitectureView } from './components/ArchitectureView';
import { HowItWorksModal } from './components/HowItWorksModal';
import { DecisionSupportPanel } from './components/DecisionSupportPanel';
import { MUMBAI_GEO_LOCATIONS, MumbaiLocation, getTimelineImpactMetrics } from './data/locations';
import { 
  getSystemStatus, 
  getScenarios, 
  runSimulation,
  SystemStatusResponse, 
  ScenarioResponse,
  SimulationResponse,
} from './services/api';
import { 
  Play, 
  Pause, 
  RotateCcw, 
  CloudRain, 
  Info, 
  MapPin, 
  Terminal,
  Activity,
  X,
  ChevronRight,
  ChevronLeft
} from 'lucide-react';

export const App: React.FC = () => {
  // Navigation active tab
  const [activeTab, setActiveTab] = useState<NavTabId>('overview');

  // Selected Location (Defaults to Kurla West)
  const [selectedLocation, setSelectedLocation] = useState<MumbaiLocation | null>(MUMBAI_GEO_LOCATIONS[0]);

  // Rainfall Scenarios (25, 50, 100, 150 mm/hr)
  const [rainfall, setRainfall] = useState<number>(100);

  // Backend System Status & Dynamic Scenarios
  const [systemStatus, setSystemStatus] = useState<SystemStatusResponse | null>(null);
  const [backendScenarios, setBackendScenarios] = useState<ScenarioResponse[]>([]);
  const [backendStatus, setBackendStatus] = useState<'CONNECTING' | 'READY' | 'DEGRADED' | 'OFFLINE'>('CONNECTING');
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('DESIGN_RED_100MM');
  const [customDurationHours, setCustomDurationHours] = useState<number>(24);
  const [customTotalDepthMm, setCustomTotalDepthMm] = useState<number>(100);
  const [tideLevel, setTideLevel] = useState<'normal' | 'high' | 'extreme'>('normal');

  // Live 2D Hydraulic/Runoff Simulation Data
  const [simulationData, setSimulationData] = useState<SimulationResponse | null>(null);
  const [isSimulationLoading, setIsSimulationLoading] = useState<boolean>(false);
  const [simulationError, setSimulationError] = useState<string | null>(null);

  // Timeline Step (indexes into simulationData.timesteps or fallback demo 7-stages)
  const [timelineStep, setTimelineStep] = useState<number>(4); // Default to Peak Inundation
  const [isSimulating, setIsSimulating] = useState<boolean>(false);

  // Camera preset mode
  const [cameraPreset, setCameraPreset] = useState<'3D' | 'TOP' | 'RESET'>('3D');

  // Panel collapse toggle for wide map exploration (Default collapsed on Flood Map)
  const [isIntelligencePanelOpen, setIsIntelligencePanelOpen] = useState<boolean>(false);

  // Dynamic Mapbox status
  const [mapStatus, setMapStatus] = useState<'CONNECTING' | 'ONLINE' | 'ERROR'>('CONNECTING');
  const [diagnostics, setDiagnostics] = useState<Record<string, any>>({
    tokenPresent: false,
    webgl2: true,
    mapboxSupported: true,
    containerWidth: 0,
    containerHeight: 0,
    styleLoaded: false,
    mapLoaded: false,
    buildings3D: true,
  });
  const [showDevDiagnostics, setShowDevDiagnostics] = useState<boolean>(false);
  const [showDisclaimer, setShowDisclaimer] = useState<boolean>(false);
  const [showHowItWorks, setShowHowItWorks] = useState<boolean>(false);
  const [showDecisionSupport, setShowDecisionSupport] = useState<boolean>(false);

  // Structured GIS layer states
  const [layers, setLayers] = useState({
    floodSpots: true,
    drainage: true,
    runoffFlow: true,
    roadsExposure: false, // Off by default so schematic lines don't slice across terrain
    criticalInfra: true,
    floodDepth: true,
    uncertainty: false,
    historical2019: false,
    terrain3D: true,
    riskGrid: true,
  });

  // Calculate current dynamic timeline metrics
  const timelineMetrics = getTimelineImpactMetrics(rainfall, timelineStep);

  // Backend Initialization: check readiness and fetch verified scenarios
  useEffect(() => {
    let isMounted = true;
    const initBackend = async () => {
      try {
        const [statusRes, scenariosRes] = await Promise.all([
          getSystemStatus(),
          getScenarios(),
        ]);
        if (isMounted) {
          setSystemStatus(statusRes);
          setBackendScenarios(scenariosRes);
          setBackendStatus(statusRes.model?.ready ? 'READY' : 'DEGRADED');
        }
      } catch (err) {
        if (isMounted) {
          console.warn('[TERRA05] Backend API unreachable, operating in standalone demo mode:', err);
          setBackendStatus('OFFLINE');
        }
      }
    };
    initBackend();
    return () => {
      isMounted = false;
    };
  }, []);

  // Live 2D Hydrodynamic Surface-Runoff Simulation Query
  useEffect(() => {
    let isMounted = true;
    const fetchSim = async () => {
      setIsSimulationLoading(true);
      setSimulationError(null);
      try {
        const rawWard = selectedLocation?.ward || 'L';
        const cleanWard = rawWard.replace(' Ward', '').trim();
        const reqPayload: {
          scenario_id: string;
          ward: string;
          max_timesteps?: number;
          custom_duration_hours?: number;
          custom_total_depth_mm?: number;
          tide_level?: 'normal' | 'high' | 'extreme';
        } = {
          scenario_id: selectedScenarioId,
          ward: cleanWard,
          tide_level: tideLevel,
        };
        if (selectedScenarioId === 'CUSTOM') {
          reqPayload.custom_duration_hours = customDurationHours;
          reqPayload.custom_total_depth_mm = customTotalDepthMm;
        }
        // For long multi-day storm (TS_2005_JULY26), request 48 intervals (12h) to capture peak downpour
        if (selectedScenarioId === 'TS_2005_JULY26') {
          reqPayload.max_timesteps = 48;
        }
        const data = await runSimulation(reqPayload);
        if (isMounted) {
          setSimulationData(data);
          setIsSimulationLoading(false);
          // Default to peak inundation timestep
          if (data.timesteps && data.timesteps.length > 0) {
            let peakIdx = 0;
            let maxDepth = -1;
            data.timesteps.forEach((ts, idx) => {
              if (ts.max_water_depth_m > maxDepth) {
                maxDepth = ts.max_water_depth_m;
                peakIdx = idx;
              }
            });
            setTimelineStep(peakIdx);
          }
        }
      } catch (err: any) {
        if (isMounted) {
          console.warn('[TERRA05] Simulation fetch warning:', err);
          setSimulationError(err.message || 'Simulation unavailable');
          setIsSimulationLoading(false);
        }
      }
    };

    fetchSim();
    return () => {
      isMounted = false;
    };
  }, [selectedScenarioId, selectedLocation?.id, selectedLocation?.ward, customDurationHours, customTotalDepthMm, tideLevel]);

  const maxSteps = simulationData?.timesteps?.length ? simulationData.timesteps.length - 1 : 6;

  // Physical Event Progression with natural stage timing:
  useEffect(() => {
    let timeoutId: ReturnType<typeof setTimeout>;
    if (isSimulating) {
      timeoutId = setTimeout(() => {
        setTimelineStep((prev) => {
          if (prev >= maxSteps) {
            setIsSimulating(false);
            return maxSteps;
          }
          return prev + 1;
        });
      }, 1800);
    }
    return () => clearTimeout(timeoutId);
  }, [isSimulating, timelineStep, maxSteps]);

  const handleToggleSimulation = () => {
    if (isSimulating) {
      setIsSimulating(false); // Clean PAUSE
    } else {
      if (timelineStep >= maxSteps) {
        setTimelineStep(0); // If at end, restart from beginning
      }
      setIsSimulating(true);
    }
  };

  const handleResetSimulation = () => {
    setIsSimulating(false);
    setTimelineStep(0);
  };

  const handleToggleLayer = (key: keyof typeof layers) => {
    setLayers((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // Dynamic Timestep Phases (Derived from simulation data or fallback demo)
  const timelinePhases = simulationData?.timesteps?.map((ts, idx) => ({
    step: idx,
    code: `+${ts.elapsed_minutes}m`,
    name: ts.rainfall_intensity_mm_per_hr === 0
      ? (ts.surface_storage_volume_m3 > 50000 ? 'Water Recession' : 'Drainage Recovery')
      : ts.step_index < 2
      ? 'Rainfall Onset'
      : (ts.step_index === 5 || ts.step_index === 6)
      ? 'Peak Inundation'
      : 'Overland Runoff',
    intensity: ts.rainfall_intensity_mm_per_hr,
    depth: ts.max_water_depth_m,
    inundatedKm2: ts.inundated_area_km2,
    storageM3: ts.surface_storage_volume_m3,
  })) || [
    { step: 0, code: 'T+00', name: 'Rainfall Onset', intensity: rainfall * 0.2, depth: 0.05, inundatedKm2: 0.2, storageM3: 15000 },
    { step: 1, code: 'T+01', name: 'Surface Runoff', intensity: rainfall * 0.5, depth: 0.15, inundatedKm2: 0.8, storageM3: 65000 },
    { step: 2, code: 'T+02', name: 'Drainage Stress', intensity: rainfall * 0.8, depth: 0.28, inundatedKm2: 1.4, storageM3: 185000 },
    { step: 3, code: 'T+03', name: 'Overland Ponding', intensity: rainfall, depth: 0.42, inundatedKm2: 2.1, storageM3: 350000 },
    { step: 4, code: 'T+04', name: 'Peak Inundation', intensity: rainfall, depth: 0.61, inundatedKm2: 2.35, storageM3: 680000 },
    { step: 5, code: 'T+05', name: 'Water Recession', intensity: rainfall * 0.3, depth: 0.35, inundatedKm2: 1.6, storageM3: 420000 },
    { step: 6, code: 'T+06', name: 'Drainage Clearance', intensity: 0, depth: 0.12, inundatedKm2: 0.5, storageM3: 95000 },
  ];

  const clampedStep = Math.min(timelineStep, timelinePhases.length - 1);
  const currentPhase = timelinePhases[clampedStep] || timelinePhases[0];
  const currentSimStepMetrics = simulationData?.timesteps?.[Math.min(timelineStep, (simulationData?.timesteps?.length || 1) - 1)];

  return (
    <div className="w-screen h-screen flex flex-col bg-gis-bg text-slate-900 overflow-hidden font-sans select-none">
      {/* Top Application Header */}
      <header className="h-12 bg-white border-b border-gis-border px-4 flex items-center justify-between z-30 shadow-gis-xs shrink-0">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            <span className="font-mono font-bold text-sm tracking-wider text-slate-950">TERRA05</span>
            <span className="text-[10px] font-mono font-bold text-sky-800 bg-sky-50 px-2 py-0.5 rounded border border-sky-200 shadow-gis-xs">
              MUMBAI URBAN FLOOD TWIN
            </span>
          </div>

          <span className="text-slate-300">|</span>

          {/* Location Area Selector */}
          <div className="flex items-center space-x-1.5 text-xs">
            <MapPin className="w-3.5 h-3.5 text-sky-600 shrink-0" />
            <span className="text-[10.5px] font-mono font-bold text-slate-500 uppercase tracking-wider hidden md:inline">
              AREA TO CHECK:
            </span>
            <select
              value={selectedLocation?.id || ""}
              onChange={(e) => {
                const loc = MUMBAI_GEO_LOCATIONS.find(l => l.id === e.target.value);
                if (loc) setSelectedLocation(loc);
              }}
              aria-label="Select Mumbai locality or ward to inspect"
              className="text-xs font-semibold text-slate-800 bg-slate-50 border border-slate-300 rounded-lg px-2.5 py-1 hover:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/20 shadow-gis-xs cursor-pointer transition-colors"
            >
              {MUMBAI_GEO_LOCATIONS.map((loc) => (
                <option key={loc.id} value={loc.id}>
                  {loc.name} ({loc.ward})
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center space-x-2.5">
          {/* Mithi River Hydraulic Status (Header Placement) */}
          <div 
            className="flex items-center space-x-2 text-xs font-mono px-2.5 py-1 rounded-lg border border-sky-200 bg-sky-50 shadow-gis-xs"
            title="Mithi River Basin Hydraulic Status"
          >
            <span className={`w-1.5 h-1.5 rounded-full ${
              timelineMetrics.mithiRiverStatus === 'BANKFULL / OVERFLOW' ? 'bg-rose-500 animate-pulse' : 'bg-sky-500'
            }`} />
            <span className="font-bold text-slate-900 tracking-wide text-[10.5px]">MITHI RIVER</span>
            <span className="text-slate-300">|</span>
            <span className="text-slate-600 text-[10.5px]">
              Status: <strong className={timelineMetrics.mithiRiverStatus === 'BANKFULL / OVERFLOW' ? 'text-rose-700' : 'text-sky-800'}>
                {timelineMetrics.mithiRiverStatus}
              </strong>
            </span>
          </div>

          {/* Utility Dialog Buttons */}
          <button
            onClick={() => setShowHowItWorks(true)}
            className="flex items-center space-x-1 text-xs font-mono font-bold text-sky-800 hover:text-sky-900 bg-sky-50 hover:bg-sky-100/80 border border-sky-200 px-2.5 py-1 rounded-lg shadow-gis-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
          >
            <Info className="w-3.5 h-3.5" />
            <span className="hidden md:inline text-[11px]">HOW TO USE</span>
          </button>

          <button
            onClick={() => setShowDecisionSupport(true)}
            className="flex items-center space-x-1 text-xs font-mono font-bold text-rose-800 hover:text-rose-900 bg-rose-50 hover:bg-rose-100/80 border border-rose-200 px-2.5 py-1 rounded-lg shadow-gis-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500"
          >
            <Activity className="w-3.5 h-3.5 text-rose-700" />
            <span className="hidden md:inline text-[11px]">RESPONSE PLAN</span>
          </button>

          {/* Dev Diagnostics Toggle */}
          <button
            onClick={() => setShowDevDiagnostics(!showDevDiagnostics)}
            className={`flex items-center space-x-1 text-xs font-mono px-2 py-1 rounded-lg border shadow-gis-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 ${
              showDevDiagnostics ? 'bg-slate-900 text-white border-slate-900' : 'text-slate-600 bg-slate-50 hover:bg-slate-100 border-gis-border'
            }`}
            title="Toggle System Diagnostics Telemetry"
          >
            <Terminal className="w-3.5 h-3.5" />
            <span className="hidden lg:inline text-[11px] font-semibold">TECH DETAILS</span>
          </button>
        </div>
      </header>

      {/* Main Workspace Area */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Left Operational Navigation Rail */}
        <NavigationRail
          activeTab={activeTab}
          onSelectTab={(tab) => setActiveTab(tab)}
        />

        {/* Central Map / Viewport Workspace */}
        <main className="flex-1 relative h-full w-full overflow-hidden bg-slate-100">
          {activeTab === 'validation' ? (
            <div className="h-full bg-gis-bg overflow-y-auto">
              <HistoricalValidationView />
            </div>
          ) : activeTab === 'data' ? (
            <div className="h-full bg-gis-bg overflow-y-auto">
              <DataLayersView />
            </div>
          ) : activeTab === 'architecture' ? (
            <div className="h-full bg-gis-bg overflow-y-auto">
              <ArchitectureView />
            </div>
          ) : (
            /* REALISTIC MUMBAI URBAN FLOOD DIGITAL TWIN VIEWPORT */
            <div className="relative w-full h-full">
              <MapboxMumbai
                rainfall={rainfall}
                timelineStep={timelineStep}
                timelineMetrics={timelineMetrics}
                selectedLocation={selectedLocation}
                onSelectLocation={(loc) => setSelectedLocation(loc)}
                layers={layers}
                cameraPreset={cameraPreset}
                simulationData={simulationData}
                simStepIndex={timelineStep}
                onStatusChange={(st) => setMapStatus(st)}
                onDiagnosticsUpdate={(d) => setDiagnostics((prev) => ({ ...prev, ...d }))}
              />

              {/* Map Layers & 2D/3D Controls */}
              <MapLayersControl
                layers={layers}
                onToggleLayer={handleToggleLayer}
                onCameraPreset={(preset) => setCameraPreset(preset)}
              />

              {/* Streamlined Floating Simulation Controller */}
              <div className="absolute bottom-3 sm:bottom-4 left-1/2 -translate-x-1/2 w-[calc(100%-24px)] max-w-3xl xl:max-w-4xl z-30 pointer-events-none">
                <div className="pointer-events-auto bg-white/95 backdrop-blur-md border border-gis-border rounded-2xl shadow-float px-4 py-2 sm:py-2.5 flex flex-col gap-1.5">
                  {/* Row 1: Rain Scenario Selector + Event Phase + Primary Actions */}
                  <div className="flex items-center justify-between gap-2.5">
                    {/* Segmented Rainfall Selector */}
                    <div className="flex items-center space-x-1.5 shrink-0">
                      <div className="text-[10px] uppercase font-mono text-slate-400 font-bold flex items-center space-x-1 hidden sm:flex">
                        <CloudRain className="w-3.5 h-3.5 text-sky-600" />
                        <span>RAIN</span>
                      </div>

                      <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200">
                        {[25, 50, 100, 150].map((rate) => (
                          <button
                            key={rate}
                            onClick={() => {
                              setRainfall(rate);
                              const matchId = rate === 25 ? 'DESIGN_YELLOW_25MM' :
                                              rate === 50 ? 'DESIGN_ORANGE_50MM' :
                                              rate === 100 ? 'DESIGN_RED_100MM' : 'DESIGN_CLOUDBURST_150MM';
                              setSelectedScenarioId(matchId);
                            }}
                            className={`px-2 py-0.5 rounded-md text-[11px] font-mono font-bold transition-all ${
                              rainfall === rate && selectedScenarioId !== 'TS_2005_JULY26' && selectedScenarioId !== 'CUSTOM'
                                ? 'bg-slate-900 text-white shadow-gis-xs'
                                : 'text-slate-600 hover:text-slate-900'
                            }`}
                          >
                            {rate}mm
                          </button>
                        ))}

                        {/* Historical 2005 Scenario Button */}
                        <button
                          onClick={() => {
                            setRainfall(150);
                            setSelectedScenarioId('TS_2005_JULY26');
                          }}
                          className={`px-1.5 py-0.5 rounded-md text-[10px] font-mono font-bold transition-all ml-0.5 ${
                            selectedScenarioId === 'TS_2005_JULY26'
                              ? 'bg-rose-700 text-white shadow-gis-xs'
                              : 'text-rose-700 hover:bg-rose-50'
                          }`}
                          title="Historical 26 July 2005 Extreme Storm (944mm total depth, 276mm/hr peak)"
                        >
                          2005 EXTREME
                        </button>
                      </div>
                    </div>

                    {/* Center Event Phase Indicator */}
                    <div className="flex-1 flex items-center justify-center space-x-2 text-xs font-mono min-w-0 px-1 truncate">
                      <span className="font-bold text-slate-950">
                        {currentPhase.code}
                      </span>
                      <span className="text-slate-300">·</span>
                      <span className="font-semibold text-slate-700 uppercase text-[11px] truncate">
                        {currentPhase.name}
                      </span>
                      {currentSimStepMetrics && (
                        <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-sky-50 text-sky-800 border border-sky-200 shrink-0">
                          {currentSimStepMetrics.rainfall_intensity_mm_per_hr.toFixed(0)} mm/hr
                        </span>
                      )}
                      {isSimulationLoading && (
                        <span className="text-[10px] font-mono text-sky-600 animate-pulse shrink-0">
                          SIMULATING...
                        </span>
                      )}
                    </div>

                    {/* Play / Pause / Reset Controls */}
                    <div className="flex items-center space-x-1.5 shrink-0">
                      <button
                        onClick={handleToggleSimulation}
                        className={`flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-mono font-bold tracking-wide transition-all shadow-gis-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 ${
                          isSimulating
                            ? 'bg-amber-600 hover:bg-amber-700 text-white'
                            : 'bg-slate-900 hover:bg-slate-800 text-white'
                        }`}
                      >
                        {isSimulating ? (
                          <>
                            <Pause className="w-3.5 h-3.5 fill-current" />
                            <span>PAUSE</span>
                          </>
                        ) : (
                          <>
                            <Play className="w-3.5 h-3.5 fill-current" />
                            <span>{timelineStep >= maxSteps ? 'REPLAY' : 'RUN'}</span>
                          </>
                        )}
                      </button>

                      <button
                        onClick={handleResetSimulation}
                        className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-600 hover:text-slate-900 transition-all shadow-gis-xs"
                        title="Reset Timeline to Rainfall Onset (T+00)"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Row 2: Timeline Scrubbing Bar + Real-Time Metrics */}
                  <div className="flex items-center justify-between gap-3 pt-0.5">
                    {/* Timeline Scrubbing Buttons */}
                    <div className="flex-1 flex items-center space-x-1 overflow-x-auto py-0.5 min-w-0">
                      {timelinePhases.slice(0, 16).map((phase) => {
                        const isCurrent = timelineStep === phase.step;
                        const isPast = timelineStep > phase.step;
                        return (
                          <button
                            key={phase.step}
                            onClick={() => {
                              setIsSimulating(false);
                              setTimelineStep(phase.step);
                            }}
                            className={`flex-1 min-w-[28px] py-1 px-1 rounded text-[10px] font-mono font-semibold transition-all text-center whitespace-nowrap ${
                              isCurrent
                                ? 'bg-sky-800 text-white shadow-gis-xs ring-1 ring-sky-900 font-bold'
                                : isPast
                                ? 'bg-sky-50 text-sky-900 hover:bg-sky-100 border border-sky-100'
                                : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                            }`}
                            title={`${phase.code}: ${phase.name} (Rain: ${phase.intensity?.toFixed(0) ?? 0}mm/h)`}
                          >
                            <span>{phase.code}</span>
                          </button>
                        );
                      })}
                      <button
                        onClick={() => setSelectedScenarioId('CUSTOM')}
                        className={`px-1.5 py-0.5 rounded text-[10.5px] font-mono font-bold transition-all shrink-0 ${
                          selectedScenarioId === 'CUSTOM'
                            ? 'bg-sky-700 text-white shadow-gis-xs'
                            : 'text-sky-700 hover:bg-sky-50 border border-sky-200/50'
                        }`}
                      >
                        CUSTOM
                      </button>
                    </div>

                    {/* Inundation Metrics & Tide Selector */}
                    <div className="flex items-center space-x-2.5 text-[10.5px] text-slate-600 font-mono shrink-0">
                      <span>
                        Flooded: <strong className="text-slate-900">
                          {currentSimStepMetrics
                            ? `${currentSimStepMetrics.inundated_area_km2.toFixed(2)} km²`
                            : `${timelineMetrics.floodedAreaKm2} km²`}
                        </strong>
                      </span>
                      {currentSimStepMetrics && (
                        <span>
                          Deepest: <strong className="text-sky-800">{currentSimStepMetrics.max_water_depth_m.toFixed(2)}m</strong>
                        </span>
                      )}
                      <label className="flex items-center gap-1 text-[10.5px] text-slate-500 font-mono">
                        <span className="uppercase text-[9.5px] text-slate-400 font-semibold hidden md:inline">Tide:</span>
                        <select
                          value={tideLevel}
                          onChange={(event) => setTideLevel(event.target.value as 'normal' | 'high' | 'extreme')}
                          className="rounded border border-slate-200 px-1.5 py-0.5 text-[10.5px] text-slate-800 bg-white"
                        >
                          <option value="normal">Normal</option>
                          <option value="high">High</option>
                          <option value="extreme">Extreme</option>
                        </select>
                      </label>
                    </div>
                  </div>

                  {/* Custom inputs when CUSTOM is chosen */}
                  {selectedScenarioId === 'CUSTOM' && (
                    <div className="flex items-center gap-2 text-[11px] text-slate-600 font-mono border-t border-slate-100 pt-1">
                      <label className="flex items-center gap-1">
                        Duration:
                        <input
                          type="number"
                          min="0.25"
                          max="168"
                          step="0.25"
                          value={customDurationHours}
                          onChange={(event) => setCustomDurationHours(Number(event.target.value))}
                          className="w-14 rounded border border-slate-300 px-1 py-0.5 text-xs text-slate-900"
                        />
                        h
                      </label>
                      <label className="flex items-center gap-1">
                        Total rain:
                        <input
                          type="number"
                          min="0.1"
                          max="5000"
                          step="0.1"
                          value={customTotalDepthMm}
                          onChange={(event) => setCustomTotalDepthMm(Number(event.target.value))}
                          className="w-16 rounded border border-slate-300 px-1 py-0.5 text-xs text-slate-900"
                        />
                        mm
                      </label>
                      <span className="text-slate-400 text-[10px]">
                        ({(customTotalDepthMm / customDurationHours).toFixed(1)} mm/hr avg)
                      </span>
                    </div>
                  )}

                  {/* Scenario Metadata & Footnote */}
                  <div className="border-t border-slate-100 pt-1 flex items-center justify-between text-[9.5px] font-mono text-slate-500">
                    <div className="flex items-center space-x-1.5 truncate">
                      <span className="text-slate-400 font-semibold uppercase">SCENARIO:</span>
                      <span className="font-bold text-slate-800 truncate">
                        {selectedScenarioId}
                      </span>
                      {(() => {
                        const sc = backendScenarios.find((s) => s.timeseries_id === selectedScenarioId);
                        return sc ? (
                          <span className="text-slate-500 hidden sm:inline">
                            ({sc.duration_hours}h duration · {sc.total_depth_mm}mm depth · {sc.peak_intensity_mm_per_hr}mm/h peak)
                          </span>
                        ) : null;
                      })()}
                      {simulationData && (
                        <span className="text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200 font-semibold ml-1 shrink-0">
                          2D ENGINE ({simulationData.domain_summary.cell_count} CELLS)
                        </span>
                      )}
                    </div>
                    <span className="text-slate-400 italic hidden md:inline shrink-0">
                      Water estimate for this demo; click a map area for details.
                    </span>
                  </div>
                </div>
              </div>

              {/* Unobtrusive Edge Tab attached to right edge of map workspace to open Intelligence Sidebar */}
              {!isIntelligencePanelOpen && (
                <button
                  onClick={() => setIsIntelligencePanelOpen(true)}
                  aria-label="Open Intelligence Sidebar"
                  aria-expanded={isIntelligencePanelOpen}
                  className="absolute right-0 top-1/2 -translate-y-1/2 z-30 bg-white/95 hover:bg-white text-slate-700 hover:text-sky-700 border-l border-y border-gis-border rounded-l-xl shadow-float py-3 px-1.5 flex flex-col items-center gap-1.5 transition-all group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 cursor-pointer"
                  title="Open Flood Intelligence & Risk Advisory Panel"
                >
                  <ChevronLeft className="w-4 h-4 text-slate-400 group-hover:text-sky-600 transition-transform group-hover:-translate-x-0.5" />
                  <span className="[writing-mode:vertical-rl] rotate-180 text-[10px] font-mono font-bold tracking-wider text-slate-500 group-hover:text-slate-900 uppercase select-none">
                    INTELLIGENCE
                  </span>
                </button>
              )}
            </div>
          )}
        </main>

        {/* Right Intelligence Panel with Smooth CSS Slide Transform */}
        {selectedLocation && activeTab === 'overview' && (
          <div 
            className={`transition-all duration-300 ease-in-out h-full flex shrink-0 relative bg-white ${
              isIntelligencePanelOpen
                ? 'w-80 md:w-[340px] opacity-100 translate-x-0 border-l border-gis-border'
                : 'w-0 opacity-0 translate-x-full pointer-events-none overflow-hidden border-l-0'
            }`}
          >
            {/* Collapse button on left edge */}
            <button
              onClick={() => setIsIntelligencePanelOpen(false)}
              className="absolute -left-3.5 top-1/2 -translate-y-1/2 z-30 bg-white border border-gis-border shadow-gis-xs rounded-full p-1 text-slate-400 hover:text-slate-800 hover:bg-slate-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 cursor-pointer"
              title="Collapse Sidebar (Maximize Map)"
              aria-label="Collapse Intelligence Sidebar"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>

            <IntelligencePanel
              location={selectedLocation}
              rainfall={rainfall}
              timelineMetrics={timelineMetrics}
              simulationData={simulationData}
              simStepIndex={timelineStep}
              onClose={() => setIsIntelligencePanelOpen(false)}
            />
          </div>
        )}
      </div>

      {/* Developer Map Diagnostics Modal */}
      {showDevDiagnostics && (
        <div className="fixed bottom-20 right-6 z-50 w-84 bg-white/95 backdrop-blur-md border border-gis-border rounded-2xl shadow-float p-4 font-mono text-xs">
          <div className="flex items-center justify-between border-b border-gis-border pb-2.5 mb-3">
            <span className="font-bold text-slate-900 flex items-center space-x-1.5">
              <Activity className="w-3.5 h-3.5 text-sky-700" />
              <span>SYSTEM DIAGNOSTICS</span>
            </span>
            <button
              onClick={() => setShowDevDiagnostics(false)}
              className="text-slate-400 hover:text-slate-700 p-0.5 rounded"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="space-y-1.5 text-[11px]">
            <div className="text-[9.5px] uppercase font-bold text-slate-400 mb-1">FRONTEND & GIS</div>
            <div className="flex justify-between">
              <span className="text-slate-500">Map Engine:</span>
              <span className="font-bold text-emerald-600">MapLibre GL v4+</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Vector Style:</span>
              <span className="font-bold text-sky-700">OpenFreeMap Liberty</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Hydrodynamic Timestep:</span>
              <span className="font-bold text-slate-900">T+0{timelineStep}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Simulation Status:</span>
              <span className="font-bold text-slate-900">
                {isSimulating ? 'PROPAGATING' : 'IDLE / PAUSED'}
              </span>
            </div>

            <div className="border-t border-slate-100 pt-2 text-[9.5px] uppercase font-bold text-slate-400 mt-2 mb-1">
              FASTAPI BACKEND & ML
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">FastAPI Service:</span>
              <span className={`font-bold ${backendStatus === 'READY' ? 'text-emerald-600' : backendStatus === 'DEGRADED' ? 'text-amber-600' : 'text-slate-500'}`}>
                {backendStatus === 'READY' ? 'READY (127.0.0.1:8000)' : backendStatus}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">ML Model:</span>
              <span className={`font-bold ${systemStatus?.model?.ready ? 'text-emerald-600' : 'text-amber-600'}`}>
                {systemStatus?.model?.ready ? 'RandomForest (Ready)' : 'Unavailable'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Rainfall Catalogue:</span>
              <span className={`font-bold ${systemStatus?.rainfall_catalogue?.ready ? 'text-emerald-600' : 'text-amber-600'}`}>
                {systemStatus?.rainfall_catalogue?.ready ? `Validated (${backendScenarios.length} Scenarios)` : 'Missing'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">100m Flood Grid:</span>
              <span className={`font-bold ${systemStatus?.geospatial_data?.ready ? 'text-emerald-600' : 'text-amber-600'}`}>
                {systemStatus?.geospatial_data?.ready ? 'Loaded (EPSG:32643)' : 'Missing'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">2D Runoff Engine:</span>
              <span className={`font-bold ${simulationData ? 'text-emerald-600' : 'text-slate-500'}`}>
                {simulationData ? `Online (${simulationData.domain_summary.cell_count} cells)` : 'Initializing...'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Mass Balance:</span>
              <span className={`font-bold ${simulationData ? 'text-emerald-600' : 'text-slate-500'}`}>
                {simulationData ? `100.0% conserved (Error: ${simulationData.water_balance.mass_balance_error_percent.toFixed(4)}%)` : '—'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">EPA-SWMM Engine:</span>
              <span className="font-bold text-slate-500">
                Offline (Using 2D Hydrodynamic Surface Runoff Prototype)
              </span>
            </div>
            {simulationError && (
              <div className="flex justify-between text-rose-600">
                <span>Simulation Diagnostic:</span>
                <span className="font-bold">{simulationError}</span>
              </div>
            )}
            <div className="flex justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-100">
              <span>GIS Canvas:</span>
              <span>{diagnostics.mapLoaded ? 'Rendered' : 'Initializing'} · {diagnostics.containerWidth > 0 ? `${diagnostics.containerWidth}x${diagnostics.containerHeight}` : 'Active'}</span>
            </div>
          </div>
        </div>
      )}

      {/* Prototype Notice Modal */}
      {showDisclaimer && (
        <div 
          className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowDisclaimer(false);
          }}
          role="dialog"
          aria-modal="true"
        >
          <div className="bg-white rounded-2xl shadow-float border border-gis-border max-w-md w-full p-5 space-y-4 font-mono">
            <div className="flex items-center justify-between border-b border-gis-border pb-2.5">
              <span className="font-bold text-slate-900 text-sm">PROTOTYPE NOTICE</span>
              <button
                onClick={() => setShowDisclaimer(false)}
                className="text-slate-400 hover:text-slate-700 p-0.5 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed font-sans">
              TERRA05 is an integrated urban stormwater flood susceptibility and digital twin system for the Mithi River catchment corridor, powered by a FastAPI backend and MapLibre GL frontend.
            </p>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80 text-[11px] text-slate-700 space-y-1.5 font-mono">
              <div>• <strong>FastAPI Backend:</strong> Real-time REST API at http://127.0.0.1:8000.</div>
              <div>• <strong>ML Susceptibility:</strong> Random Forest spatial model on 47,758 grid cells; uncalibrated historical susceptibility score (not a rainfall event probability).</div>
              <div>• <strong>Rainfall Catalogue:</strong> 9 validated scenarios (historical 2005 + design storms).</div>
              <div>• <strong>Hydraulic Simulation:</strong> 2D diffusive overland runoff and water accumulation engine (100m raster grid, Horton infiltration, depression storage, drainage conduit capacity). EPA-SWMM offline.</div>
            </div>

            <button
              onClick={() => setShowDisclaimer(false)}
              className="w-full py-2.5 bg-slate-900 text-white text-xs font-mono font-bold rounded-xl hover:bg-slate-800 transition-colors shadow-gis-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
            >
              UNDERSTOOD
            </button>
          </div>
        </div>
      )}

      {showHowItWorks && <HowItWorksModal onClose={() => setShowHowItWorks(false)} />}
      {showDecisionSupport && (
        <DecisionSupportPanel
          rainfall={selectedScenarioId === 'CUSTOM' ? customTotalDepthMm : rainfall * 3}
          durationHours={selectedScenarioId === 'CUSTOM' ? customDurationHours : 3}
          tideLevel={tideLevel}
          simulationData={simulationData}
          timelineMetrics={timelineMetrics}
          onClose={() => setShowDecisionSupport(false)}
        />
      )}
    </div>
  );
};

export default App;
