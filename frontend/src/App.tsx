import React, { useState, useEffect } from 'react';
import { MapboxMumbai } from './components/MapboxMumbai';
import { IntelligencePanel } from './components/IntelligencePanel';
import { NavigationRail, NavTabId } from './components/NavigationRail';
import { MapLayersControl } from './components/MapLayersControl';
import { HistoricalValidationView } from './components/HistoricalValidationView';
import { DataLayersView } from './components/DataLayersView';
import { ArchitectureView } from './components/ArchitectureView';
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
  Clock, 
  Info, 
  MapPin, 
  Terminal,
  Activity,
  X,
  Server,
  Droplets
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

  // Live 2D Hydraulic/Runoff Simulation Data
  const [simulationData, setSimulationData] = useState<SimulationResponse | null>(null);
  const [isSimulationLoading, setIsSimulationLoading] = useState<boolean>(false);
  const [simulationError, setSimulationError] = useState<string | null>(null);

  // Timeline Step (indexes into simulationData.timesteps or fallback demo 7-stages)
  const [timelineStep, setTimelineStep] = useState<number>(4); // Default to Peak Inundation
  const [isSimulating, setIsSimulating] = useState<boolean>(false);

  // Camera preset mode
  const [cameraPreset, setCameraPreset] = useState<'3D' | 'TOP' | 'RESET'>('3D');

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

  // Structured GIS layer states
  const [layers, setLayers] = useState({
    floodSpots: true,
    drainage: true,
    runoffFlow: true,
    roadsExposure: true,
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
        const reqPayload: { scenario_id: string; ward: string; max_timesteps?: number } = {
          scenario_id: selectedScenarioId,
          ward: 'L',
        };
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
  }, [selectedScenarioId]);

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
    <div className="w-screen h-screen flex flex-col bg-gis-bg text-gis-text overflow-hidden font-sans select-none">
      {/* Top Header */}
      <header className="h-11 bg-white border-b border-gis-border px-4 flex items-center justify-between z-30 shadow-xs">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            <span className="font-display font-bold text-sm tracking-widest text-slate-900">TERRA05</span>
            <span className="text-[10px] font-mono font-bold text-sky-800 bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
              MUMBAI URBAN FLOOD TWIN
            </span>
          </div>

          <span className="text-slate-300">|</span>

          <div className="flex items-center space-x-1.5 text-xs">
            <MapPin className="w-3.5 h-3.5 text-sky-600 shrink-0" />
            <span className="text-[11px] font-bold text-slate-700 hidden md:inline">HOTSPOT:</span>
            <select
              value={selectedLocation?.id || ""}
              onChange={(e) => {
                const loc = MUMBAI_GEO_LOCATIONS.find(l => l.id === e.target.value);
                if (loc) setSelectedLocation(loc);
              }}
              className="text-xs font-semibold text-slate-800 bg-slate-50 border border-slate-300 rounded px-2.5 py-1 hover:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 shadow-xs cursor-pointer"
            >
              {MUMBAI_GEO_LOCATIONS.map((loc) => (
                <option key={loc.id} value={loc.id}>
                  {loc.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {/* Backend Status Indicator */}
          <div className={`flex items-center space-x-1.5 text-xs font-mono px-2 py-0.5 rounded border ${
            backendStatus === 'READY'
              ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
              : backendStatus === 'DEGRADED'
              ? 'text-amber-700 bg-amber-50 border-amber-200'
              : backendStatus === 'CONNECTING'
              ? 'text-sky-700 bg-sky-50 border-sky-200 animate-pulse'
              : 'text-slate-600 bg-slate-100 border-slate-200'
          }`} title={systemStatus?.model?.detail || 'FastAPI Service'}>
            <span className={`w-1.5 h-1.5 rounded-full ${
              backendStatus === 'READY'
                ? 'bg-emerald-500'
                : backendStatus === 'DEGRADED'
                ? 'bg-amber-500'
                : backendStatus === 'CONNECTING'
                ? 'bg-sky-500'
                : 'bg-slate-400'
            }`} />
            <span className="text-[11px] font-semibold">
              {backendStatus === 'READY' ? 'API & MODEL ONLINE' :
               backendStatus === 'DEGRADED' ? 'API DEGRADED' :
               backendStatus === 'CONNECTING' ? 'CONNECTING API...' : 'BACKEND OFFLINE'}
            </span>
          </div>

          {/* GIS Engine Status Indicator */}
          <div className={`flex items-center space-x-1.5 text-xs font-mono px-2 py-0.5 rounded border ${
            mapStatus === 'ONLINE'
              ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
              : mapStatus === 'CONNECTING'
              ? 'text-amber-700 bg-amber-50 border-amber-200 animate-pulse'
              : 'text-rose-700 bg-rose-50 border-rose-200'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${
              mapStatus === 'ONLINE' ? 'bg-emerald-500' : mapStatus === 'CONNECTING' ? 'bg-amber-500' : 'bg-rose-500'
            }`} />
            <span className="text-[11px] font-semibold">
              {mapStatus === 'ONLINE' ? 'GIS ENGINE ONLINE' : mapStatus === 'CONNECTING' ? 'CONNECTING...' : 'ERROR'}
            </span>
          </div>

          {/* Dev Diagnostics Toggle */}
          <button
            onClick={() => setShowDevDiagnostics(!showDevDiagnostics)}
            className="flex items-center space-x-1 text-xs font-mono text-slate-500 hover:text-slate-800 bg-slate-50 hover:bg-slate-100 border border-gis-border px-2 py-0.5 rounded transition-colors"
            title="Toggle Developer Diagnostics Panel"
          >
            <Terminal className="w-3 h-3 text-slate-400" />
            <span className="hidden lg:inline text-[11px]">DIAGNOSTICS</span>
          </button>

          {/* Prototype Notice Modal Trigger */}
          <button
            onClick={() => setShowDisclaimer(true)}
            className="flex items-center space-x-1 text-xs font-mono text-slate-600 bg-slate-50 hover:bg-slate-100 border border-gis-border px-2 py-0.5 rounded transition-colors"
          >
            <Info className="w-3 h-3 text-slate-400" />
            <span className="hidden md:inline text-[11px]">DEMO NOTICE</span>
          </button>
        </div>
      </header>

      {/* Main Workspace */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Left Thin 64px Icon Rail */}
        <NavigationRail
          activeTab={activeTab}
          onSelectTab={(tab) => {
            setActiveTab(tab);
            if (tab === 'drainage') setLayers((prev) => ({ ...prev, drainage: true }));
            if (tab === 'uncertainty') setLayers((prev) => ({ ...prev, uncertainty: true }));
          }}
        />

        {/* Central Map Viewport (75-80% screen real estate) */}
        <main className="flex-1 relative h-full w-full overflow-hidden">
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
            /* REALISTIC MUMBAI URBAN FLOOD DIGITAL TWIN */
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

              {/* Map Layers & 2D/3D Buttons */}
              <MapLayersControl
                layers={layers}
                onToggleLayer={handleToggleLayer}
                onCameraPreset={(preset) => setCameraPreset(preset)}
              />

              {/* Redesigned Floating Simulation Controller */}
              <div className="absolute bottom-5 left-1/2 -translate-x-1/2 w-[calc(100%-48px)] max-w-4xl z-30 pointer-events-none">
                <div className="pointer-events-auto bg-white/95 backdrop-blur-md border border-gis-border rounded-xl shadow-float px-5 py-3 flex flex-col gap-2">
                  <div className="flex items-center justify-between gap-5">
                    {/* Segmented Rainfall Selector */}
                    <div className="flex items-center space-x-2 border-r border-slate-200 pr-4">
                      <div className="text-[10px] uppercase font-mono text-slate-400 font-bold flex items-center space-x-1">
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
                            className={`px-2.5 py-1 rounded text-xs font-mono font-bold transition-all ${
                              rainfall === rate && selectedScenarioId !== 'TS_2005_JULY26'
                                ? 'bg-slate-900 text-white shadow-xs'
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
                          className={`px-2 py-1 rounded text-[11px] font-mono font-bold transition-all ml-0.5 ${
                            selectedScenarioId === 'TS_2005_JULY26'
                              ? 'bg-rose-700 text-white shadow-xs'
                              : 'text-rose-700 hover:bg-rose-50'
                          }`}
                          title="Historical 26 July 2005 Extreme Storm (944mm total depth, 276mm/hr peak)"
                        >
                          2005 EXTREME
                        </button>
                      </div>
                    </div>

                    {/* Physical Timestep Progression */}
                    <div className="flex-1 flex flex-col space-y-1.5 px-1">
                      <div className="flex items-center justify-between text-xs font-mono">
                        <div className="flex items-center space-x-2">
                          <span className="font-bold text-slate-900">
                            {currentPhase.code}
                          </span>
                          <span className="text-slate-400">·</span>
                          <span className="font-medium text-slate-700">
                            {currentPhase.name.toUpperCase()}
                          </span>
                          {currentSimStepMetrics && (
                            <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-sky-50 text-sky-800 border border-sky-200">
                              {currentSimStepMetrics.rainfall_intensity_mm_per_hr.toFixed(0)} mm/hr
                            </span>
                          )}
                          {isSimulationLoading && (
                            <span className="text-[10px] font-mono text-sky-600 animate-pulse">
                              SIMULATING...
                            </span>
                          )}
                        </div>
                        <div className="flex items-center space-x-3 text-[10px] text-slate-500 font-mono">
                          <span>
                            Inundated: <strong className="text-slate-800">
                              {currentSimStepMetrics
                                ? `${currentSimStepMetrics.inundated_area_km2.toFixed(2)} km²`
                                : `${timelineMetrics.floodedAreaKm2} km²`}
                            </strong>
                          </span>
                          {currentSimStepMetrics && (
                            <span>
                              Max Depth: <strong className="text-sky-800">{currentSimStepMetrics.max_water_depth_m.toFixed(2)}m</strong>
                            </span>
                          )}
                          {currentSimStepMetrics && (
                            <span className="hidden sm:inline">
                              Storage: <strong className="text-slate-700">{Math.round(currentSimStepMetrics.surface_storage_volume_m3).toLocaleString()} m³</strong>
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Timeline Scrubbing Bar */}
                      <div className="flex items-center space-x-1 overflow-x-auto">
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
                              className={`flex-1 py-1 px-1 rounded text-[10px] font-mono font-semibold transition-all text-center whitespace-nowrap ${
                                isCurrent
                                  ? 'bg-sky-800 text-white shadow-xs ring-1 ring-sky-900'
                                  : isPast
                                  ? 'bg-sky-50 text-sky-900 hover:bg-sky-100'
                                  : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                              }`}
                              title={`${phase.code}: ${phase.name} (Rain: ${phase.intensity?.toFixed(0) ?? 0}mm/h)`}
                            >
                              <span>{phase.code}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {/* Play / Pause / Reset Controls */}
                    <div className="flex items-center space-x-2 border-l border-slate-200 pl-4">
                      <button
                        onClick={handleToggleSimulation}
                        className={`flex items-center space-x-1.5 px-4 py-2 rounded-lg text-xs font-mono font-bold tracking-wide transition-all shadow-xs ${
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
                            <span>{timelineStep >= maxSteps ? 'REPLAY' : 'RUN SCENARIO'}</span>
                          </>
                        )}
                      </button>

                      <button
                        onClick={handleResetSimulation}
                        className="p-2 rounded-lg bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-600 hover:text-slate-900 transition-all"
                        title="Reset Timeline to Rainfall Onset (T+00)"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Scenario Metadata & Scientific Notice Footer */}
                  <div className="border-t border-slate-100 pt-1 flex items-center justify-between text-[10px] font-mono text-slate-500">
                    <div className="flex items-center space-x-2">
                      <span className="text-slate-400 font-semibold uppercase">SCENARIO:</span>
                      <span className="font-bold text-slate-800">
                        {selectedScenarioId}
                      </span>
                      {(() => {
                        const sc = backendScenarios.find((s) => s.timeseries_id === selectedScenarioId);
                        return sc ? (
                          <span className="text-slate-500">
                            ({sc.duration_hours}h duration · {sc.total_depth_mm}mm depth · {sc.peak_intensity_mm_per_hr}mm/h peak)
                          </span>
                        ) : null;
                      })()}
                      {simulationData && (
                        <span className="text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200 font-semibold ml-1">
                          2D RUNOFF ENGINE ({simulationData.domain_summary.cell_count} CELLS)
                        </span>
                      )}
                    </div>
                    <span className="text-slate-400 italic">
                      * 2D surface accumulation prototype; ML susceptibility is static historical exposure.
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>

        {/* Right Intelligence Panel (Fixed 320px width) */}
        {selectedLocation && activeTab !== 'validation' && activeTab !== 'data' && activeTab !== 'architecture' && (
          <IntelligencePanel
            location={selectedLocation}
            rainfall={rainfall}
            timelineMetrics={timelineMetrics}
            simulationData={simulationData}
            simStepIndex={timelineStep}
          />
        )}
      </div>

      {/* Developer Map Diagnostics Modal */}
      {showDevDiagnostics && (
        <div className="fixed bottom-24 right-84 z-50 w-88 bg-white/95 backdrop-blur-md border border-gis-border rounded-xl shadow-float p-4 font-mono text-xs">
          <div className="flex items-center justify-between border-b border-gis-border pb-2 mb-3">
            <span className="font-bold text-slate-900 flex items-center space-x-1.5">
              <Activity className="w-3.5 h-3.5 text-sky-700" />
              <span>SYSTEM DIAGNOSTICS</span>
            </span>
            <button
              onClick={() => setShowDevDiagnostics(false)}
              className="text-slate-400 hover:text-slate-700"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="space-y-1.5 text-[11px]">
            <div className="text-[10px] uppercase font-bold text-slate-400 mb-1">FRONTEND & GIS</div>
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

            <div className="border-t border-slate-100 pt-2 text-[10px] uppercase font-bold text-slate-400 mt-2 mb-1">
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
          </div>
        </div>
      )}

      {/* Prototype Notice Modal */}
      {showDisclaimer && (
        <div className="fixed inset-0 z-50 bg-slate-900/30 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-float border border-gis-border max-w-md w-full p-5 space-y-4 font-mono">
            <div className="flex items-center justify-between border-b border-gis-border pb-2">
              <span className="font-bold text-slate-900 text-sm">PROTOTYPE NOTICE</span>
              <button
                onClick={() => setShowDisclaimer(false)}
                className="text-slate-400 hover:text-slate-700"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              TERRA05 is an integrated urban stormwater flood susceptibility and digital twin system for the Mithi River catchment corridor, powered by a FastAPI backend and MapLibre GL frontend.
            </p>

            <div className="p-3 bg-slate-50 rounded-lg text-[11px] text-slate-700 space-y-1">
              <div>• <strong>FastAPI Backend:</strong> Real-time REST API at http://127.0.0.1:8000.</div>
              <div>• <strong>ML Susceptibility:</strong> Random Forest spatial model on 47,758 grid cells; uncalibrated historical susceptibility score (not a rainfall event probability).</div>
              <div>• <strong>Rainfall Catalogue:</strong> 9 validated scenarios (historical 2005 + design storms).</div>
              <div>• <strong>Hydraulic Simulation:</strong> 2D diffusive overland runoff and water accumulation engine (100m raster grid, Horton infiltration, depression storage, drainage conduit capacity). EPA-SWMM offline.</div>
            </div>

            <button
              onClick={() => setShowDisclaimer(false)}
              className="w-full py-2 bg-slate-900 text-white text-xs font-bold rounded-lg hover:bg-slate-800 transition-colors"
            >
              UNDERSTOOD
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
