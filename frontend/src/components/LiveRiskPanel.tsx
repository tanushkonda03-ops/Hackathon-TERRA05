import React, { useState } from 'react';
import { 
  ShieldAlert, 
  AlertTriangle, 
  CheckCircle2, 
  MapPin, 
  Maximize2, 
  TrendingUp, 
  Droplets, 
  Layers, 
  ArrowUpRight,
  Info
} from 'lucide-react';
import { RiskZone, SeverityLevel } from '../types';

interface LiveRiskPanelProps {
  zones: RiskZone[];
  rainfall: number;
  selectedZone: RiskZone | null;
  onSelectZone: (zone: RiskZone) => void;
  onFilterSeverity: (severity: SeverityLevel | null) => void;
  activeFilter: SeverityLevel | null;
}

export const LiveRiskPanel: React.FC<LiveRiskPanelProps> = ({
  zones,
  rainfall,
  selectedZone,
  onSelectZone,
  onFilterSeverity,
  activeFilter,
}) => {
  // Aggregate stats based on current rainfall
  const counts = zones.reduce(
    (acc, zone) => {
      const data = zone.scenarioData[rainfall] || zone.scenarioData[100];
      acc[data.severity] = (acc[data.severity] || 0) + 1;
      return acc;
    },
    { SEVERE: 0, WARNING: 0, ADVISORY: 0, SAFE: 0 } as Record<SeverityLevel, number>
  );

  // Filtered zones list
  const displayZones = activeFilter
    ? zones.filter((z) => {
        const data = z.scenarioData[rainfall] || z.scenarioData[100];
        return data.severity === activeFilter;
      })
    : zones;

  return (
    <aside className="w-80 bg-command-900 border-l border-command-700/80 flex flex-col justify-between select-none z-20 shrink-0">
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Panel Header */}
        <div className="p-3 border-b border-command-700/80 bg-command-950/40">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-1.5 text-xs font-tech font-bold text-slate-100">
              <ShieldAlert className="w-4 h-4 text-rose-500" />
              <span>LIVE RISK INTELLIGENCE</span>
            </div>
            <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/80 px-1.5 py-0.5 rounded border border-cyan-500/30">
              REAL-TIME
            </span>
          </div>
          <div className="text-[10px] text-slate-400 mt-1">
            Dynamic catchment vulnerability calculated for {rainfall} mm/hr
          </div>
        </div>

        {/* Severity Aggregate Distribution Bars */}
        <div className="p-3 border-b border-command-700/80 space-y-2 bg-command-850/50">
          {/* SEVERE */}
          <button
            onClick={() => onFilterSeverity(activeFilter === 'SEVERE' ? null : 'SEVERE')}
            className={`w-full text-left p-1.5 rounded transition-all ${
              activeFilter === 'SEVERE' ? 'bg-rose-950/70 border border-rose-500/50' : 'hover:bg-command-800'
            }`}
          >
            <div className="flex justify-between items-center text-xs font-tech font-bold text-rose-400">
              <span className="flex items-center space-x-1.5">
                <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                <span>CRITICAL SEVERE</span>
              </span>
              <span className="font-mono">{counts.SEVERE} zones</span>
            </div>
            <div className="w-full bg-command-950 h-1.5 rounded-full mt-1 overflow-hidden">
              <div
                className="bg-rose-500 h-full rounded-full transition-all duration-300"
                style={{ width: `${(counts.SEVERE / zones.length) * 100}%` }}
              />
            </div>
          </button>

          {/* WARNING */}
          <button
            onClick={() => onFilterSeverity(activeFilter === 'WARNING' ? null : 'WARNING')}
            className={`w-full text-left p-1.5 rounded transition-all ${
              activeFilter === 'WARNING' ? 'bg-amber-950/70 border border-amber-500/50' : 'hover:bg-command-800'
            }`}
          >
            <div className="flex justify-between items-center text-xs font-tech font-bold text-amber-400">
              <span className="flex items-center space-x-1.5">
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                <span>WARNING LEVEL</span>
              </span>
              <span className="font-mono">{counts.WARNING} zones</span>
            </div>
            <div className="w-full bg-command-950 h-1.5 rounded-full mt-1 overflow-hidden">
              <div
                className="bg-amber-500 h-full rounded-full transition-all duration-300"
                style={{ width: `${(counts.WARNING / zones.length) * 100}%` }}
              />
            </div>
          </button>

          {/* ADVISORY */}
          <button
            onClick={() => onFilterSeverity(activeFilter === 'ADVISORY' ? null : 'ADVISORY')}
            className={`w-full text-left p-1.5 rounded transition-all ${
              activeFilter === 'ADVISORY' ? 'bg-yellow-950/70 border border-yellow-500/50' : 'hover:bg-command-800'
            }`}
          >
            <div className="flex justify-between items-center text-xs font-tech font-bold text-yellow-400">
              <span className="flex items-center space-x-1.5">
                <span className="w-2 h-2 rounded-full bg-yellow-500" />
                <span>WATCH ADVISORY</span>
              </span>
              <span className="font-mono">{counts.ADVISORY} zones</span>
            </div>
            <div className="w-full bg-command-950 h-1.5 rounded-full mt-1 overflow-hidden">
              <div
                className="bg-yellow-500 h-full rounded-full transition-all duration-300"
                style={{ width: `${(counts.ADVISORY / zones.length) * 100}%` }}
              />
            </div>
          </button>
        </div>

        {/* Priority Response List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          <div className="flex items-center justify-between text-[10px] font-mono uppercase tracking-wider text-slate-400">
            <span>PRIORITY RESPONSE STAGING</span>
            <span>{displayZones.length} LOCATIONS</span>
          </div>

          {displayZones.map((zone, idx) => {
            const data = zone.scenarioData[rainfall] || zone.scenarioData[100];
            const isSelected = selectedZone?.id === zone.id;

            return (
              <div
                key={zone.id}
                onClick={() => onSelectZone(zone)}
                className={`p-2.5 rounded-lg border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-command-800 border-cyan-400/80 shadow-glow-cyan'
                    : 'bg-command-850/80 border-command-700/70 hover:border-slate-500 hover:bg-command-800/60'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] font-mono px-1 rounded bg-command-700 text-slate-300">
                      #{String(idx + 1).padStart(2, '0')}
                    </span>
                    <span className="text-xs font-tech font-bold text-slate-100">{zone.name}</span>
                  </div>
                  <span
                    className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded uppercase ${
                      data.severity === 'SEVERE'
                        ? 'bg-rose-950 text-rose-300 border border-rose-600/40'
                        : data.severity === 'WARNING'
                        ? 'bg-amber-950 text-amber-300 border border-amber-600/40'
                        : data.severity === 'ADVISORY'
                        ? 'bg-yellow-950 text-yellow-300 border border-yellow-600/40'
                        : 'bg-emerald-950 text-emerald-300 border border-emerald-600/40'
                    }`}
                  >
                    {data.severity}
                  </span>
                </div>

                <div className="mt-2 grid grid-cols-2 gap-2 text-[10px] font-mono bg-command-900/60 p-1.5 rounded">
                  <div>
                    <span className="text-slate-500">PROBABILITY:</span>{' '}
                    <span className="text-cyan-300 font-bold">{data.probability}%</span>
                  </div>
                  <div>
                    <span className="text-slate-500">EXP DEPTH:</span>{' '}
                    <span className="text-amber-300 font-bold">{data.expectedDepthM.toFixed(2)}m</span>
                  </div>
                </div>

                <div className="mt-2 flex items-center justify-between text-[10px] text-slate-400">
                  <span className="truncate">{zone.ward} • {zone.catchment}</span>
                  <span className="text-cyan-400 font-tech font-bold flex items-center space-x-0.5">
                    <span>VIEW</span>
                    <ArrowUpRight className="w-3 h-3" />
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </aside>
  );
};
