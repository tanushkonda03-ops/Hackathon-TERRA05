import React from 'react';
import { 
  Map, 
  FileText, 
  CloudRain, 
  Waves, 
  Gauge, 
  ShieldAlert,
  Play,
  Pause,
  RotateCcw,
  Clock,
  Activity,
  Check
} from 'lucide-react';
import { SimulationResponse } from '../services/api';
import { MumbaiLocation } from '../data/locations';

export type NavTabId = 'map' | 'plan';

interface LeftSidebarProps {
  activeTab: NavTabId;
  onSelectTab: (tab: NavTabId) => void;
  rainfall: number;
  selectedScenarioId: string;
  onSelectScenario: (rain: number, scenarioId: string) => void;
  tideLevel: 'normal' | 'high' | 'extreme';
  onSelectTideLevel: (tide: 'normal' | 'high' | 'extreme') => void;
  customDurationHours: number;
  onCustomDurationChange: (hours: number) => void;
  customTotalDepthMm: number;
  onCustomTotalDepthChange: (depth: number) => void;
  simulationData: SimulationResponse | null;
  selectedLocation: MumbaiLocation | null;
  isSimulationLoading: boolean;
  // Simulation Timeline & Playback props
  timelineStep: number;
  maxSteps: number;
  isSimulating: boolean;
  onToggleSimulation: () => void;
  onResetSimulation: () => void;
  onSelectStep: (step: number) => void;
  timelinePhases: {
    step: number;
    code: string;
    name: string;
    intensity?: number;
    depth?: number;
    inundatedKm2?: number;
    storageM3?: number;
  }[];
  currentPhase: {
    step: number;
    code: string;
    name: string;
    intensity?: number;
    depth?: number;
    inundatedKm2?: number;
    storageM3?: number;
  };
  currentSimStepMetrics: any;
  timelineMetrics: any;
  effectiveLocDepthM?: number;
}

export const LeftSidebar: React.FC<LeftSidebarProps> = ({
  activeTab,
  onSelectTab,
  rainfall,
  selectedScenarioId,
  onSelectScenario,
  tideLevel,
  onSelectTideLevel,
  customDurationHours,
  onCustomDurationChange,
  customTotalDepthMm,
  onCustomTotalDepthChange,
  simulationData,
  selectedLocation,
  isSimulationLoading,
  timelineStep,
  maxSteps,
  isSimulating,
  onToggleSimulation,
  onResetSimulation,
  onSelectStep,
  timelinePhases,
  currentPhase,
  currentSimStepMetrics,
  timelineMetrics,
  effectiveLocDepthM,
}) => {
  // Minimalist, sophisticated rainfall scenario chips
  const rainScenarios = [
    {
      id: 'DESIGN_YELLOW_25MM',
      rainfall: 25,
      label: '25mm',
      tag: 'Advisory',
      activeColor: 'bg-amber-50 text-amber-950 border-amber-300 ring-1 ring-amber-400/40 shadow-xs font-bold',
    },
    {
      id: 'DESIGN_ORANGE_50MM',
      rainfall: 50,
      label: '50mm',
      tag: 'Watch',
      activeColor: 'bg-orange-50 text-orange-950 border-orange-300 ring-1 ring-orange-400/40 shadow-xs font-bold',
    },
    {
      id: 'DESIGN_RED_100MM',
      rainfall: 100,
      label: '100mm',
      tag: 'Severe',
      activeColor: 'bg-rose-50 text-rose-950 border-rose-300 ring-1 ring-rose-400/40 shadow-xs font-bold',
    },
    {
      id: 'DESIGN_CLOUDBURST_150MM',
      rainfall: 150,
      label: '150mm',
      tag: 'Cloudburst',
      activeColor: 'bg-purple-50 text-purple-950 border-purple-300 ring-1 ring-purple-400/40 shadow-xs font-bold',
    },
    {
      id: 'TS_2005_JULY26',
      rainfall: 150,
      label: '2005',
      tag: 'Deluge',
      activeColor: 'bg-red-50 text-red-950 border-red-300 ring-1 ring-red-400/40 shadow-xs font-bold',
    },
    {
      id: 'CUSTOM',
      rainfall: customTotalDepthMm,
      label: 'Custom',
      tag: `${customDurationHours}h·${customTotalDepthMm}mm`,
      activeColor: 'bg-sky-50 text-sky-950 border-sky-300 ring-1 ring-sky-400/40 shadow-xs font-bold',
    },
  ];

  // Refined 3-way segmented tidal options
  const tideOptions: { id: 'normal' | 'high' | 'extreme'; label: string; height: string; desc: string }[] = [
    {
      id: 'normal',
      label: 'Normal',
      height: '1.2m',
      desc: 'Baseflow; gravity outfalls clear',
    },
    {
      id: 'high',
      label: 'High Tide',
      height: '4.2m',
      desc: 'Spring tide; outfalls throttled',
    },
    {
      id: 'extreme',
      label: 'Surge',
      height: '5.1m',
      desc: 'Storm surge; reverse backwater',
    },
  ];

  const cellCount = simulationData?.domain_summary?.cell_count ?? (selectedLocation?.ward === 'B' ? 263 : 750);

  return (
    <aside 
      aria-label="Navigation and Scenario Controls"
      className="w-80 h-full bg-white border-r border-slate-200/80 flex flex-col shrink-0 select-none shadow-xs z-20 overflow-hidden font-sans"
    >
      {/* 1. Brand Monogram & Live Status Header */}
      <div className="px-3.5 py-2.5 border-b border-slate-200/80 bg-white flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-2.5">
          <div 
            className="w-6 h-6 rounded-md bg-slate-900 text-white font-mono font-bold flex items-center justify-center text-[10.5px] shadow-xs tracking-wider shrink-0"
            title="TERRA05 - Mumbai Urban Flood Twin"
          >
            T05
          </div>
          <div>
            <div className="text-xs font-mono font-bold text-slate-900 leading-tight flex items-center gap-1.5">
              <span>TERRA05</span>
              <span className="text-[8.5px] font-mono font-semibold px-1 py-0.2 rounded bg-slate-100 text-slate-600 border border-slate-200">
                2D HYDRO
              </span>
            </div>
            <div className="text-[9.5px] text-slate-400 font-sans leading-none mt-0.5">
              Mumbai Flood Twin
            </div>
          </div>
        </div>

        {/* Telemetry Status Badge */}
        <div className="flex items-center space-x-1.5 px-2 py-0.5 rounded-full bg-emerald-50/80 border border-emerald-200/80 text-emerald-700">
          <span className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
          </span>
          <span className="text-[8.5px] font-mono font-bold uppercase tracking-wider">
            ONLINE
          </span>
        </div>
      </div>

      {/* 2. Primary Navigation Bar (Minimalist Segmented Switch) */}
      <div className="p-2 border-b border-slate-200/80 bg-slate-50/50 shrink-0">
        <div className="grid grid-cols-2 gap-1 bg-slate-100/80 p-0.5 rounded-lg border border-slate-200/60">
          <button
            onClick={() => onSelectTab('map')}
            className={`py-1.5 px-2 rounded-md flex items-center justify-center space-x-1.5 text-xs font-mono transition-all ${
              activeTab === 'map'
                ? 'bg-white text-slate-900 font-bold shadow-xs border border-slate-200/70'
                : 'text-slate-600 hover:text-slate-900 hover:bg-white/40 font-medium'
            }`}
          >
            <Map className="w-3.5 h-3.5 shrink-0 text-slate-700" />
            <span>FLOOD MAP</span>
          </button>

          <button
            onClick={() => onSelectTab('plan')}
            className={`py-1.5 px-2 rounded-md flex items-center justify-center space-x-1.5 text-xs font-mono transition-all ${
              activeTab === 'plan'
                ? 'bg-white text-slate-900 font-bold shadow-xs border border-slate-200/70'
                : 'text-slate-600 hover:text-slate-900 hover:bg-white/40 font-medium'
            }`}
          >
            <FileText className="w-3.5 h-3.5 shrink-0 text-slate-700" />
            <span>RESPONSE PLAN</span>
          </button>
        </div>
      </div>

      {/* 3. Main Content: Environmental & Simulation Controls */}
      <div className="flex-1 p-2.5 space-y-2.5 overflow-y-auto">
        {activeTab === 'plan' && (
          <div className="p-2 rounded-lg bg-sky-50/70 border border-sky-200/80 text-xs font-mono">
            <div className="flex items-center space-x-1.5 text-sky-950 font-bold text-[10.5px]">
              <ShieldAlert className="w-3.5 h-3.5 text-sky-700 shrink-0" />
              <span>INCIDENT RESPONSE MODE</span>
            </div>
            <p className="text-[9.5px] text-slate-600 mt-0.5 leading-tight font-sans">
              Test municipal response staging against storm & tidal boundary heads.
            </p>
          </div>
        )}

        {/* CRAZY LIGHT-THEME HERO CONTAINER: SIMULATION TIMELINE */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-sky-50/90 via-white to-blue-50/60 p-3 space-y-2.5 border-2 border-sky-300 shadow-[0_10px_30px_-5px_rgba(14,165,233,0.18),0_4px_12px_-2px_rgba(14,165,233,0.08)] ring-1 ring-sky-400/30 transition-all">
          {/* Top Decorative Luminous Water Accent Bar */}
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-sky-400 via-blue-500 to-indigo-500" />
          {/* Subtle Ambient Radial Flood Flare in Top Right */}
          <div className="absolute -top-10 -right-10 w-28 h-28 bg-sky-200/40 rounded-full blur-2xl pointer-events-none" />

          {/* Header Bar: Label + Live Solver Status */}
          <div className="flex items-center justify-between relative z-10">
            <div className="flex items-center space-x-1.5">
              <div className="w-5 h-5 rounded-md bg-sky-100 text-sky-700 flex items-center justify-center border border-sky-200 shadow-xs">
                <Clock className="w-3.5 h-3.5 shrink-0 text-sky-600" />
              </div>
              <span className="text-[10px] font-mono font-black text-sky-950 uppercase tracking-wider">
                SIMULATION TIMELINE
              </span>
            </div>
            {isSimulationLoading ? (
              <span className="text-[8.5px] font-mono font-bold text-amber-700 animate-pulse bg-amber-50 px-2 py-0.5 rounded-full border border-amber-300 shadow-xs flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-ping" />
                COMPUTING...
              </span>
            ) : (
              <span className="text-[8.5px] font-mono font-bold text-sky-900 bg-sky-100/90 px-2 py-0.5 rounded-full border border-sky-300 shadow-xs flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-sky-500" />
                {currentPhase.code} SOLVED
              </span>
            )}
          </div>

          {/* Time Code, Hydraulic Phase, Intensity & Play Actions */}
          <div className="flex items-center justify-between gap-2 pt-0.5 relative z-10">
            <div className="min-w-0 flex-1">
              <div className="flex items-center space-x-1.5 flex-wrap gap-y-0.5">
                <span className="font-mono font-black text-2xl tracking-tight bg-gradient-to-r from-sky-600 via-blue-700 to-indigo-700 bg-clip-text text-transparent drop-shadow-xs shrink-0">
                  {currentPhase.code}
                </span>
                <span className="px-2 py-0.5 rounded-md bg-sky-100/90 text-sky-900 border border-sky-300/80 text-[10px] font-mono font-bold tracking-tight uppercase shadow-xs truncate max-w-[140px]">
                  {currentPhase.name}
                </span>
              </div>
              {currentSimStepMetrics && (
                <div className="inline-flex items-center gap-1 mt-1 text-[9.5px] font-mono font-bold text-sky-900 bg-sky-100/70 px-2 py-0.5 rounded-md border border-sky-200/80">
                  <CloudRain className="w-3 h-3 text-sky-600 shrink-0" />
                  <span>Rain Rate: <strong className="text-blue-950 font-black">{currentSimStepMetrics.rainfall_intensity_mm_per_hr.toFixed(0)} mm/h</strong></span>
                </div>
              )}
            </div>

            {/* Play/Pause/Replay and Reset Controls */}
            <div className="flex items-center space-x-1.5 shrink-0">
              <button
                onClick={onToggleSimulation}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-mono font-black transition-all shadow-[0_4px_14px_rgba(37,99,235,0.35)] hover:shadow-[0_6px_20px_rgba(37,99,235,0.5)] hover:scale-105 active:scale-95 ${
                  isSimulating
                    ? 'bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 border border-amber-300 animate-pulse'
                    : 'bg-gradient-to-r from-sky-500 via-blue-600 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white border border-sky-300/40'
                }`}
                title={isSimulating ? "Pause Simulation" : "Run Timeline Progression"}
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
                onClick={onResetSimulation}
                className="p-1.5 rounded-xl bg-white hover:bg-sky-50 border-2 border-sky-200 hover:border-sky-400 text-sky-700 hover:text-sky-900 shadow-xs transition-all hover:rotate-[-45deg] active:scale-90"
                title="Reset to Rainfall Onset (T+00)"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Inundation Telemetry Micro-Cards (Luminous Floating Pods) */}
          <div className="grid grid-cols-2 gap-2 pt-1 border-t border-sky-100 relative z-10 font-mono">
            <div className="bg-white/95 backdrop-blur-xs p-2 rounded-xl border-2 border-sky-200/90 shadow-[0_4px_12px_rgba(14,165,233,0.1)] hover:border-sky-400 transition-all group">
              <div className="flex items-center justify-between text-[8.5px] font-extrabold uppercase tracking-wider text-sky-700">
                <span>FLOODED AREA</span>
                <span className="text-[7.5px] bg-sky-100 text-sky-800 px-1 py-0.2 rounded font-black">2D MESH</span>
              </div>
              <div className="mt-0.5 flex items-baseline">
                <span className="text-lg font-black text-slate-950 tracking-tight group-hover:text-sky-600 transition-colors">
                  {currentSimStepMetrics
                    ? currentSimStepMetrics.inundated_area_km2.toFixed(2)
                    : timelineMetrics.floodedAreaKm2}
                </span>
                <span className="text-xs font-bold text-sky-600 ml-1">km²</span>
              </div>
            </div>

            <div className="bg-white/95 backdrop-blur-xs p-2 rounded-xl border-2 border-indigo-200/90 shadow-[0_4px_12px_rgba(99,102,241,0.1)] hover:border-indigo-400 transition-all group">
              <div className="flex items-center justify-between text-[8.5px] font-extrabold uppercase tracking-wider text-indigo-700">
                <span>PEAK DEPTH</span>
                <span className="text-[7.5px] bg-indigo-100 text-indigo-800 px-1 py-0.2 rounded font-black">WATER HEAD</span>
              </div>
              <div className="mt-0.5 flex items-baseline">
                <span className="text-lg font-black text-slate-950 tracking-tight group-hover:text-indigo-600 transition-colors">
                  {currentSimStepMetrics
                    ? currentSimStepMetrics.max_water_depth_m.toFixed(2)
                    : (effectiveLocDepthM ?? 0.45).toFixed(2)}
                </span>
                <span className="text-xs font-bold text-indigo-600 ml-1">m</span>
              </div>
            </div>
          </div>

          {/* Timestep Scrub Pills (Vibrant Light Grid) */}
          <div className="pt-1 relative z-10">
            <div className="flex items-center justify-between text-[8.5px] font-mono font-extrabold text-slate-600 uppercase tracking-wider mb-1.5">
              <span className="flex items-center gap-1 text-sky-950 font-black">
                TIMESTEP SCRUB
              </span>
              <span className="px-1.5 py-0.2 rounded-full bg-sky-100 text-sky-800 font-black border border-sky-200 text-[8px]">
                {timelineStep + 1} / {timelinePhases.length}
              </span>
            </div>
            <div className="grid grid-cols-4 sm:grid-cols-6 gap-1">
              {timelinePhases.slice(0, 16).map((phase) => {
                const isCurrent = timelineStep === phase.step;
                const isPast = timelineStep > phase.step;
                return (
                  <button
                    key={phase.step}
                    onClick={() => onSelectStep(phase.step)}
                    className={`py-1 rounded-lg text-[9.5px] font-mono transition-all text-center ${
                      isCurrent
                        ? 'bg-gradient-to-r from-sky-500 via-blue-600 to-indigo-600 text-white font-black shadow-[0_4px_12px_rgba(14,165,233,0.45)] ring-2 ring-sky-300 scale-105'
                        : isPast
                        ? 'bg-sky-50 text-sky-800 border border-sky-200 hover:bg-sky-100 font-bold hover:scale-105'
                        : 'bg-white text-slate-600 hover:text-sky-900 border border-slate-200 hover:border-sky-300 hover:bg-sky-50/50 font-medium hover:scale-105'
                    }`}
                    title={`${phase.code}: ${phase.name} (${phase.intensity?.toFixed(0) ?? 0} mm/h)`}
                  >
                    {phase.code}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Section: Rainfall Scenario Configuration (Minimalist 3x2 Grid) */}
        <div>
          <div className="flex items-center justify-between mb-1.5 px-0.5">
            <div className="flex items-center space-x-1.5">
              <CloudRain className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              <span className="text-[10px] font-mono font-bold text-slate-600 uppercase tracking-wider">
                RAINFALL SCENARIO
              </span>
            </div>
            <span className="text-[9px] font-mono text-slate-400">
              Design Hyetograph
            </span>
          </div>

          <div className="grid grid-cols-3 gap-1">
            {rainScenarios.map((sc) => {
              const isSelected = selectedScenarioId === sc.id || 
                (selectedScenarioId !== 'TS_2005_JULY26' && selectedScenarioId !== 'CUSTOM' && rainfall === sc.rainfall && sc.id !== 'TS_2005_JULY26' && sc.id !== 'CUSTOM');
              return (
                <button
                  key={sc.id}
                  onClick={() => onSelectScenario(sc.rainfall, sc.id)}
                  className={`p-1.5 rounded-lg text-center transition-all border flex flex-col items-center justify-center ${
                    isSelected
                      ? sc.activeColor
                      : 'bg-white text-slate-700 border-slate-200/80 hover:bg-slate-50 hover:border-slate-300 shadow-xs'
                  }`}
                >
                  <span className="text-[11px] font-mono font-bold leading-tight">
                    {sc.label}
                  </span>
                  <span className={`text-[8.5px] mt-0.5 font-medium leading-none truncate max-w-[80px] ${isSelected ? 'opacity-90' : 'text-slate-400'}`}>
                    {sc.tag}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Custom Scenario Numerical Inputs */}
          {selectedScenarioId === 'CUSTOM' && (
            <div className="mt-1.5 p-2 rounded-lg bg-slate-50 border border-slate-200 text-xs font-mono space-y-1.5 shadow-xs">
              <div className="text-[9.5px] font-bold text-slate-700 uppercase">
                CUSTOM RUNOFF PARAMETERS
              </div>
              <div className="grid grid-cols-2 gap-1.5">
                <label className="flex flex-col text-[9.5px] text-slate-600 font-semibold">
                  <span>Duration (hrs):</span>
                  <input
                    type="number"
                    min="0.25"
                    max="168"
                    step="0.25"
                    value={customDurationHours}
                    onChange={(e) => onCustomDurationChange(Number(e.target.value))}
                    className="mt-0.5 rounded border border-slate-300 bg-white px-1.5 py-0.5 text-xs text-slate-900 font-bold focus:outline-none focus:ring-1 focus:ring-sky-500"
                  />
                </label>
                <label className="flex flex-col text-[9.5px] text-slate-600 font-semibold">
                  <span>Depth (mm):</span>
                  <input
                    type="number"
                    min="5"
                    max="2000"
                    step="5"
                    value={customTotalDepthMm}
                    onChange={(e) => onCustomTotalDepthChange(Number(e.target.value))}
                    className="mt-0.5 rounded border border-slate-300 bg-white px-1.5 py-0.5 text-xs text-slate-900 font-bold focus:outline-none focus:ring-1 focus:ring-sky-500"
                  />
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Section: Coastal & Tidal Level (Minimal 3-way Segmented Control) */}
        <div>
          <div className="flex items-center justify-between mb-1.5 px-0.5">
            <div className="flex items-center space-x-1.5">
              <Waves className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              <span className="text-[10px] font-mono font-bold text-slate-600 uppercase tracking-wider">
                COASTAL & TIDAL LEVEL
              </span>
            </div>
            <span className="text-[9px] font-mono text-slate-400">
              Boundary Head
            </span>
          </div>

          <div className="grid grid-cols-3 gap-1 bg-slate-100/80 p-0.5 rounded-lg border border-slate-200/60">
            {tideOptions.map((tide) => {
              const isSelected = tideLevel === tide.id;
              return (
                <button
                  key={tide.id}
                  onClick={() => onSelectTideLevel(tide.id)}
                  className={`py-1.5 px-1 rounded-md text-center transition-all flex flex-col items-center justify-center ${
                    isSelected
                      ? 'bg-white text-slate-900 shadow-xs font-bold border border-slate-200/80 ring-1 ring-sky-500/20'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-white/40'
                  }`}
                  title={`${tide.label} (${tide.height}): ${tide.desc}`}
                >
                  <span className="text-[10px] font-mono font-bold leading-tight">
                    {tide.label}
                  </span>
                  <span className={`text-[8.5px] font-mono leading-none mt-0.5 ${isSelected ? 'text-sky-800 font-semibold' : 'text-slate-400'}`}>
                    {tide.height}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Section: Hydrodynamic Solver Telemetry (Clean Minimal Grid) */}
        <div className="pt-1.5 border-t border-slate-200/80">
          <div className="flex items-center space-x-1.5 mb-1 px-0.5">
            <Gauge className="w-3.5 h-3.5 text-slate-500 shrink-0" />
            <span className="text-[10px] font-mono font-bold text-slate-600 uppercase tracking-wider">
              HYDRODYNAMIC SOLVER
            </span>
          </div>

          <div className="bg-slate-50/70 rounded-xl p-2.5 border border-slate-200/80 grid grid-cols-2 gap-2 font-mono text-[10px]">
            <div>
              <span className="text-slate-400 block text-[8.5px] uppercase font-bold tracking-wider">Focus Basin</span>
              <strong className="text-slate-800 truncate block mt-0.5 font-bold">
                {selectedLocation?.name || 'Kurla West'}
              </strong>
            </div>
            <div>
              <span className="text-slate-400 block text-[8.5px] uppercase font-bold tracking-wider">Ward Domain</span>
              <strong className="text-slate-800 truncate block mt-0.5 font-bold">
                Ward {selectedLocation?.ward || 'L'}
              </strong>
            </div>
            <div>
              <span className="text-slate-400 block text-[8.5px] uppercase font-bold tracking-wider">Computational Mesh</span>
              <strong className="text-sky-800 truncate block mt-0.5 font-bold">
                {cellCount} Cells (100m)
              </strong>
            </div>
            <div>
              <span className="text-slate-400 block text-[8.5px] uppercase font-bold tracking-wider">Engine Physics</span>
              <strong className={`truncate block mt-0.5 flex items-center gap-1 font-bold ${isSimulationLoading ? 'text-amber-600 animate-pulse' : 'text-emerald-700'}`}>
                <Activity className="w-2.5 h-2.5 shrink-0" />
                {isSimulationLoading ? 'Computing 2D...' : '2D Solved'}
              </strong>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};
