import React, { useState, useEffect, useCallback } from 'react';
import { MapboxMumbai } from './components/MapboxMumbai';
import { IntelligencePanel } from './components/IntelligencePanel';
import { LeftSidebar, NavTabId } from './components/LeftSidebar';
import { MapLayersControl } from './components/MapLayersControl';
import { DecisionSupportPanel } from './components/DecisionSupportPanel';
import { CitizenAdvisoryModal } from './components/CitizenAdvisoryModal';
import { ScenarioPanel } from './components/ScenarioPanel';
import { ScenarioRiskCell } from './services/api';
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
  MapPin, 
  ChevronLeft
} from 'lucide-react';

export const App: React.FC = () => {
  // Navigation active tab: 'map' (Flood Map) or 'plan' (Response Plan)
  const [activeTab, setActiveTab] = useState<NavTabId>('map');

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
  const [scenarioRiskMap, setScenarioRiskMap] = useState<ScenarioRiskCell[] | null>(null);
  const handleScenarioRiskMap = useCallback((map: ScenarioRiskCell[] | null) => {
    setScenarioRiskMap(map);
    if (map) setLayers((previous) => ({ ...previous, scenarioRisk: true }));
  }, []);
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
  const [showCitizenModal, setShowCitizenModal] = useState<boolean>(false);

  // Dual Persona Mode: EOC Authority Command vs Citizen Public Warning
  const [personaMode, setPersonaMode] = useState<'EOC' | 'CITIZEN'>('EOC');

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
    riskGrid: false, // Off by default: ensures clean flood visualization without wireframe grid lines
    scenarioRisk: false,
    evacuationRoutes: true, // Safe emergency corridors & high-ground shelters
  });

  // Calculate dynamic timeline metrics (truthful physics, no pump fudge factors)
  const timelineMetrics = getTimelineImpactMetrics(rainfall, timelineStep);

  // Selected Location Local Inundation Depth
  const locScenario = selectedLocation?.scenarios[rainfall] || selectedLocation?.scenarios[100];
  const effectiveLocDepthM = locScenario?.depthM ?? 0.45;

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
  const rawSimStepMetrics = simulationData?.timesteps?.[Math.min(timelineStep, (simulationData?.timesteps?.length || 1) - 1)];
  const currentSimStepMetrics = rawSimStepMetrics ? {
    ...rawSimStepMetrics,
    max_water_depth_m: Number(rawSimStepMetrics.max_water_depth_m.toFixed(2)),
    inundated_area_km2: Number(rawSimStepMetrics.inundated_area_km2.toFixed(2)),
  } : null;

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

          {/* Persona Switch: Authority EOC vs Citizen Public Advisory */}
          <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-300">
            <button
              onClick={() => setPersonaMode('EOC')}
              className={`px-2 py-1 rounded-md text-[10.5px] font-mono font-bold transition-all ${
                personaMode === 'EOC'
                  ? 'bg-slate-900 text-white shadow-gis-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
              title="Municipal Emergency Operations Centre (EOC) Command View"
            >
              🏛️ EOC COMMAND
            </button>
            <button
              onClick={() => {
                setPersonaMode('CITIZEN');
                setShowCitizenModal(true);
              }}
              className={`px-2 py-1 rounded-md text-[10.5px] font-mono font-bold transition-all ${
                personaMode === 'CITIZEN'
                  ? 'bg-amber-600 text-white shadow-gis-xs'
                  : 'text-amber-800 hover:text-amber-950 hover:bg-amber-100/50'
              }`}
              title="Citizen Public Safety Advisory & Safe Evacuation View"
            >
              👥 CITIZEN VIEW
            </button>
          </div>
        </div>
      </header>

      {/* Main Workspace Area */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Left Operational Navigation & Scenario Sidebar */}
        <LeftSidebar
          activeTab={activeTab}
          onSelectTab={(tab) => setActiveTab(tab)}
          rainfall={rainfall}
          selectedScenarioId={selectedScenarioId}
          onSelectScenario={(rain, scId) => {
            setRainfall(rain);
            setSelectedScenarioId(scId);
          }}
          tideLevel={tideLevel}
          onSelectTideLevel={(tide) => setTideLevel(tide)}
          customDurationHours={customDurationHours}
          onCustomDurationChange={(h) => setCustomDurationHours(h)}
          customTotalDepthMm={customTotalDepthMm}
          onCustomTotalDepthChange={(d) => setCustomTotalDepthMm(d)}
          simulationData={simulationData}
          selectedLocation={selectedLocation}
          isSimulationLoading={isSimulationLoading}
          timelineStep={timelineStep}
          maxSteps={maxSteps}
          isSimulating={isSimulating}
          onToggleSimulation={handleToggleSimulation}
          onResetSimulation={handleResetSimulation}
          onSelectStep={(step) => {
            setIsSimulating(false);
            setTimelineStep(step);
          }}
          timelinePhases={timelinePhases}
          currentPhase={currentPhase}
          currentSimStepMetrics={currentSimStepMetrics}
          timelineMetrics={timelineMetrics}
          effectiveLocDepthM={effectiveLocDepthM}
        />

        {/* Central Map / Viewport Workspace */}
        <main className="flex-1 relative h-full w-full overflow-hidden bg-slate-100">
          {activeTab === 'plan' ? (
            /* RESPONSE PLAN EMBEDDED IN MAIN WORKSPACE */
            <div className="h-full w-full bg-slate-100 overflow-y-auto">
              <DecisionSupportPanel
                embedded={true}
                rainfall={selectedScenarioId === 'CUSTOM' ? customTotalDepthMm : rainfall * 3}
                durationHours={selectedScenarioId === 'CUSTOM' ? customDurationHours : 3}
                tideLevel={tideLevel}
                simulationData={simulationData}
                timelineMetrics={timelineMetrics}
                selectedLocation={selectedLocation}
                timelineStep={timelineStep}
                onClose={() => setActiveTab('map')}
              />

            </div>
          ) : (
            /* REALISTIC MUMBAI URBAN FLOOD DIGITAL TWIN VIEWPORT */
            <div className="relative w-full h-full overflow-hidden">
              <MapboxMumbai
                rainfall={rainfall}
                timelineStep={timelineStep}
                timelineMetrics={timelineMetrics}
                selectedLocation={selectedLocation}
                onSelectLocation={(loc) => setSelectedLocation(loc)}
                layers={layers}
                cameraPreset={cameraPreset}
                simulationData={simulationData}
                scenarioRiskMap={scenarioRiskMap}
                simStepIndex={timelineStep}
                onStatusChange={(st) => setMapStatus(st)}
                onDiagnosticsUpdate={(d) => setDiagnostics((prev) => ({ ...prev, ...d }))}
              />

              <ScenarioPanel onRiskMapChange={handleScenarioRiskMap} />

              {/* Citizen Public Warning Banner when in Citizen Persona Mode */}
              {personaMode === 'CITIZEN' && (
                <div className="absolute top-3.5 left-1/2 -translate-x-1/2 z-30 max-w-xl w-[calc(100%-120px)] pointer-events-auto animate-in slide-in-from-top-2 duration-200">
                  <div className="bg-amber-500 text-slate-950 border-2 border-amber-600 rounded-xl shadow-float px-3 py-2 flex items-center justify-between gap-2.5">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-base shrink-0">⚠️</span>
                      <div className="min-w-0">
                        <div className="text-[11px] font-bold font-mono uppercase truncate">
                          PUBLIC ALERT: {selectedLocation?.name || 'Kurla West'} (~{effectiveLocDepthM.toFixed(2)}m WATER)
                        </div>
                        <div className="text-[10px] text-slate-900 truncate">
                          Avoid ground underpasses. Elevated flyovers & municipal dry shelters active.
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => setShowCitizenModal(true)}
                      className="px-2.5 py-1 bg-slate-950 text-white rounded-lg text-[10.5px] font-mono font-bold hover:bg-slate-800 transition-colors shrink-0 shadow-xs"
                    >
                      ADVISORY & ROUTES
                    </button>
                  </div>
                </div>
              )}

              {/* Map Layers & 2D/3D Controls */}
              <MapLayersControl
                layers={layers}
                onToggleLayer={handleToggleLayer}
                onCameraPreset={(preset) => setCameraPreset(preset)}
                className={`absolute top-3.5 ${isIntelligencePanelOpen ? 'right-4 sm:right-[356px]' : 'right-4'} z-20 select-none flex items-start space-x-2 transition-[right] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] motion-reduce:transition-none`}
              />



              {/* Collapsible Right Intelligence Sidebar Overlay */}
              {selectedLocation && (
                <aside
                  aria-label="Flood Intelligence Panel"
                  aria-hidden={!isIntelligencePanelOpen}
                  className={`absolute top-0 right-0 h-full w-80 sm:w-[340px] z-30 flex transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] motion-reduce:transition-none ${
                    isIntelligencePanelOpen ? 'translate-x-0' : 'translate-x-full'
                  }`}
                >
                  {/* Single Persistent Non-Jumping Toggle Tab attached to Sidebar Left Edge */}
                  <button
                    onClick={() => setIsIntelligencePanelOpen(!isIntelligencePanelOpen)}
                    aria-label={isIntelligencePanelOpen ? "Close Intelligence Sidebar" : "Open Intelligence Sidebar"}
                    aria-expanded={isIntelligencePanelOpen}
                    className="pointer-events-auto absolute -left-8 sm:-left-9 top-1/2 -translate-y-1/2 z-40 bg-white/95 hover:bg-white text-slate-700 hover:text-sky-700 border-l border-y border-gis-border rounded-l-xl shadow-float py-3 px-1.5 flex flex-col items-center gap-1.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 cursor-pointer select-none"
                    title={isIntelligencePanelOpen ? "Collapse Intelligence Sidebar" : "Open Flood Intelligence & Risk Advisory Panel"}
                  >
                    <ChevronLeft className={`w-4 h-4 text-slate-500 hover:text-sky-600 transition-transform duration-300 ${isIntelligencePanelOpen ? 'rotate-180' : ''}`} />
                    <span className="[writing-mode:vertical-rl] rotate-180 text-[10px] font-mono font-bold tracking-wider text-slate-500 hover:text-slate-900 uppercase">
                      {isIntelligencePanelOpen ? 'CLOSE' : 'INTELLIGENCE'}
                    </span>
                  </button>

                  {/* Panel Drawer Content */}
                  <div className={`w-full h-full bg-white border-l border-gis-border shadow-float flex flex-col overflow-hidden transition-opacity duration-300 ${
                    isIntelligencePanelOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
                  }`}>
                    <IntelligencePanel
                      location={selectedLocation}
                      rainfall={rainfall}
                      timelineMetrics={timelineMetrics}
                      simulationData={simulationData}
                      simStepIndex={timelineStep}
                      onClose={() => setIsIntelligencePanelOpen(false)}
                    />
                  </div>
                </aside>
              )}
            </div>
          )}
        </main>
      </div>

      {showCitizenModal && (
        <CitizenAdvisoryModal
          location={selectedLocation}
          rainfall={rainfall}
          timelineStep={timelineStep}
          peakDepthM={effectiveLocDepthM}
          onClose={() => setShowCitizenModal(false)}
          onSelectEvacuationLayer={() => {
            setLayers((prev) => ({ ...prev, evacuationRoutes: true }));
          }}
        />
      )}
    </div>
  );
};

export default App;
