import React from 'react';
import { Play, RotateCcw, CloudRain, Clock, Gauge, AlertTriangle, ShieldCheck } from 'lucide-react';
import { RainfallScenario } from '../types';

interface SimulationControlProps {
  currentRainfall: number;
  scenario: RainfallScenario;
  onSelectRainfall: (rainfall: number) => void;
  isSimulating: boolean;
  simulationProgress: number; // 0 to 1
  onRunSimulation: () => void;
  onResetSimulation: () => void;
}

export const SimulationControl: React.FC<SimulationControlProps> = ({
  currentRainfall,
  scenario,
  onSelectRainfall,
  isSimulating,
  simulationProgress,
  onRunSimulation,
  onResetSimulation,
}) => {
  const scenarioSteps = [25, 50, 100, 150];

  // Format timeline time (e.g., 00:00 to 03:00)
  const currentTotalMinutes = Math.floor(simulationProgress * 180);
  const hours = Math.floor(currentTotalMinutes / 60);
  const mins = currentTotalMinutes % 60;
  const timeString = `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}`;

  return (
    <div className="h-28 border-t border-command-700/80 bg-command-900/95 backdrop-blur-md px-6 py-2.5 flex items-center justify-between z-20 select-none">
      {/* Rainfall Scenario Selector */}
      <div className="flex flex-col space-y-1.5 w-72 shrink-0">
        <div className="flex items-center justify-between">
          <div className="text-[10px] uppercase font-code tracking-widest text-slate-400 flex items-center space-x-1.5">
            <CloudRain className="w-3.5 h-3.5 text-cyan-400" />
            <span>RAINFALL SCENARIOS</span>
          </div>
          <span className="text-xs font-tech font-bold text-cyan-300">
            {currentRainfall} mm/hr
          </span>
        </div>

        {/* Preset scenario toggle buttons */}
        <div className="grid grid-cols-4 gap-1.5">
          {scenarioSteps.map((rate) => {
            const isSelected = currentRainfall === rate;
            let tag = 'NORMAL';
            if (rate === 50) tag = 'HEAVY';
            if (rate === 100) tag = 'EXTREME';
            if (rate === 150) tag = 'EXTREME+';

            return (
              <button
                key={rate}
                disabled={isSimulating}
                onClick={() => onSelectRainfall(rate)}
                className={`py-1.5 px-1 rounded text-center transition-all ${
                  isSelected
                    ? 'bg-cyan-500/25 border border-cyan-400 text-cyan-200 font-bold shadow-glow-cyan'
                    : 'bg-command-800/80 hover:bg-command-700/80 border border-command-700 text-slate-400 hover:text-slate-200'
                } ${isSimulating ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <div className="text-[9px] font-mono leading-none">{tag}</div>
                <div className="text-xs font-tech mt-0.5">{rate} mm</div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Central Simulation Timeline & Progress */}
      <div className="flex-1 max-w-2xl px-8 flex flex-col space-y-2">
        <div className="flex items-center justify-between text-xs font-code">
          <div className="flex items-center space-x-2 text-slate-300">
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
            <span>SIMULATION TIMELINE: <span className="text-cyan-300 font-bold">{timeString}</span> / 03:00 hrs</span>
          </div>
          <div className="flex items-center space-x-2 text-[11px] text-slate-400">
            <span>Drain Stress:</span>
            <span className={`font-mono font-bold ${scenario.peakDrainStressPercent > 90 ? 'text-rose-400' : 'text-amber-400'}`}>
              {scenario.peakDrainStressPercent}%
            </span>
          </div>
        </div>

        {/* Timeline Bar with Markers */}
        <div className="relative w-full h-3 bg-command-950 rounded-full overflow-hidden border border-command-700">
          <div
            className="h-full bg-gradient-to-r from-cyan-500 via-blue-500 to-rose-500 transition-all duration-150"
            style={{ width: `${Math.max(5, simulationProgress * 100)}%` }}
          />
          {/* Milestone indicators */}
          <div className="absolute inset-0 flex justify-between px-4 pointer-events-none text-[8px] text-slate-500 font-mono items-center">
            <span>T+00 (Onset)</span>
            <span>T+01 (Runoff)</span>
            <span>T+02 (Peak Surcharge)</span>
            <span>T+03 (Inundation)</span>
          </div>
        </div>

        {/* Milestone captions */}
        <div className="flex justify-between text-[10px] text-slate-400 font-mono px-1">
          <span>00:00 • Infiltration</span>
          <span>01:00 • Overland Flow</span>
          <span>02:00 • Drain Backwater</span>
          <span>03:00 • High-Water Mark</span>
        </div>
      </div>

      {/* Action Buttons: Run & Reset */}
      <div className="flex items-center space-x-3 shrink-0">
        <button
          onClick={onRunSimulation}
          disabled={isSimulating}
          className={`flex items-center space-x-2 px-5 py-2.5 rounded font-tech font-bold tracking-wider text-xs uppercase transition-all ${
            isSimulating
              ? 'bg-cyan-900/60 text-cyan-300 border border-cyan-500/30 cursor-wait animate-pulse'
              : 'bg-cyan-500 hover:bg-cyan-400 text-command-950 shadow-glow-cyan active:scale-95'
          }`}
        >
          <Play className={`w-4 h-4 fill-current ${isSimulating ? 'animate-spin' : ''}`} />
          <span>{isSimulating ? 'SIMULATING...' : 'RUN SIMULATION'}</span>
        </button>

        <button
          onClick={onResetSimulation}
          disabled={isSimulating}
          className="flex items-center space-x-1.5 px-3.5 py-2.5 rounded bg-command-800 hover:bg-command-700 border border-command-700 text-slate-300 hover:text-white text-xs font-tech uppercase transition-all"
          title="Reset to Baseline City State"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">RESET</span>
        </button>
      </div>
    </div>
  );
};
