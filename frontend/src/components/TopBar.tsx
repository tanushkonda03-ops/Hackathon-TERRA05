import React from 'react';
import { 
  Activity, 
  MapPin, 
  Clock, 
  CloudRain, 
  ShieldAlert, 
  BarChart3, 
  Sliders,
  Layers,
  ChevronRight,
  Info
} from 'lucide-react';
import { RainfallScenario } from '../types';

interface TopBarProps {
  rainfall: number;
  scenario: RainfallScenario;
  severeCount: number;
  warningCount: number;
  maxDepth: number;
  isSimulating: boolean;
  onOpenDisclaimer: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  rainfall,
  scenario,
  severeCount,
  warningCount,
  maxDepth,
  isSimulating,
  onOpenDisclaimer,
}) => {
  return (
    <header className="h-14 border-b border-command-700/80 bg-command-900/95 backdrop-blur-md px-4 flex items-center justify-between z-30 select-none">
      {/* Brand & Identity */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-2">
          <div className="relative flex items-center justify-center w-8 h-8 rounded bg-gradient-to-br from-cyan-500 to-blue-700 font-tech font-bold text-white text-base shadow-glow-cyan">
            T05
            <div className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-400 ring-2 ring-command-900 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-tech text-base font-bold tracking-wider text-slate-100">TERRA05</span>
              <span className="text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-500/30 font-code">
                MUMBAI DIGITAL TWIN
              </span>
            </div>
            <div className="text-[10px] text-slate-400 font-sans tracking-wide">
              Urban Stormwater Flood Intelligence Platform
            </div>
          </div>
        </div>

        <div className="h-6 w-px bg-slate-800 hidden md:block mx-2" />

        {/* Operating status & Geo */}
        <div className="hidden lg:flex items-center space-x-3 text-xs font-code">
          <div className="flex items-center space-x-1.5 text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping inline-block" />
            <span className="font-semibold tracking-wider">SYSTEM OPERATIONAL</span>
          </div>
          <span className="text-slate-600">•</span>
          <div className="flex items-center space-x-1 text-slate-300">
            <MapPin className="w-3.5 h-3.5 text-cyan-400" />
            <span>MUMBAI, INDIA (MITHI BASIN)</span>
          </div>
        </div>
      </div>

      {/* KPI Stats Strip */}
      <div className="flex items-center space-x-2 md:space-x-4">
        {/* Rainfall KPI */}
        <div className="px-3 py-1 rounded bg-command-850/90 border border-command-700 flex items-center space-x-2">
          <CloudRain className={`w-4 h-4 ${isSimulating ? 'text-cyan-400 animate-bounce' : 'text-blue-400'}`} />
          <div>
            <div className="text-[9px] uppercase tracking-wider text-slate-400 font-mono">Current Rainfall</div>
            <div className="text-xs font-tech font-bold text-cyan-300 flex items-center space-x-1">
              <span>{rainfall} mm/hr</span>
              <span className="text-[10px] text-slate-400 font-normal">({scenario.label})</span>
            </div>
          </div>
        </div>

        {/* Severe Zones KPI */}
        <div className="px-3 py-1 rounded bg-command-850/90 border border-command-700 flex items-center space-x-2">
          <ShieldAlert className="w-4 h-4 text-rose-500" />
          <div>
            <div className="text-[9px] uppercase tracking-wider text-slate-400 font-mono">Severe Zones</div>
            <div className="text-xs font-tech font-bold text-rose-400">
              {severeCount} <span className="text-[10px] text-slate-400 font-normal">/ {severeCount + warningCount} Risk</span>
            </div>
          </div>
        </div>

        {/* Max Depth KPI */}
        <div className="hidden sm:flex px-3 py-1 rounded bg-command-850/90 border border-command-700 items-center space-x-2">
          <Activity className="w-4 h-4 text-amber-400" />
          <div>
            <div className="text-[9px] uppercase tracking-wider text-slate-400 font-mono">Max Peak Depth</div>
            <div className="text-xs font-tech font-bold text-amber-300">
              {maxDepth.toFixed(2)} m
            </div>
          </div>
        </div>

        {/* Model Coverage */}
        <div className="hidden xl:flex px-3 py-1 rounded bg-command-850/90 border border-command-700 items-center space-x-2">
          <BarChart3 className="w-4 h-4 text-emerald-400" />
          <div>
            <div className="text-[9px] uppercase tracking-wider text-slate-400 font-mono">Model Coverage</div>
            <div className="text-xs font-tech font-bold text-emerald-300">
              94.7% Catchment
            </div>
          </div>
        </div>

        {/* Prototype Disclaimer Badge */}
        <button
          onClick={onOpenDisclaimer}
          className="px-2.5 py-1 rounded bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-400 hover:text-amber-300 text-xs font-code flex items-center space-x-1 transition-colors"
          title="View Prototype Disclaimer"
        >
          <Info className="w-3.5 h-3.5" />
          <span className="hidden md:inline">PROTOTYPE MODE</span>
        </button>
      </div>
    </header>
  );
};
