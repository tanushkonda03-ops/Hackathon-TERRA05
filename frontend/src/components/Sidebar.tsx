import React from 'react';
import { 
  Radar, 
  Cpu, 
  History, 
  Server, 
  Database, 
  HelpCircle,
  Activity,
  Layers,
  SlidersHorizontal,
  Compass,
  FileCode2,
  Workflow
} from 'lucide-react';

export type ActiveNavTab = 
  | 'overview' 
  | 'simulation' 
  | 'risk-zones' 
  | 'validation' 
  | 'uncertainty' 
  | 'infrastructure' 
  | 'data-layers' 
  | 'architecture';

interface SidebarProps {
  activeTab: ActiveNavTab;
  onSelectTab: (tab: ActiveNavTab) => void;
  activeZoneCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  activeZoneCount,
}) => {
  return (
    <aside className="w-56 bg-command-900 border-r border-command-700/80 flex flex-col justify-between select-none z-20 shrink-0">
      <div className="py-3 px-3 space-y-4">
        {/* Navigation Group 1: Command */}
        <div>
          <div className="text-[10px] uppercase font-code tracking-widest text-slate-400 px-2 py-1 flex items-center justify-between">
            <span>COMMAND</span>
            <span className="text-[9px] text-cyan-400 bg-cyan-950/60 px-1 rounded border border-cyan-500/20">LIVE</span>
          </div>
          <div className="space-y-1 mt-1">
            <button
              onClick={() => onSelectTab('overview')}
              className={`w-full flex items-center justify-between px-2.5 py-2 rounded text-xs transition-colors ${
                activeTab === 'overview'
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 font-medium'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-command-800/60'
              }`}
            >
              <div className="flex items-center space-x-2.5">
                <Radar className="w-4 h-4 text-cyan-400" />
                <span>Overview & 3D Twin</span>
              </div>
            </button>

            <button
              onClick={() => onSelectTab('simulation')}
              className={`w-full flex items-center justify-between px-2.5 py-2 rounded text-xs transition-colors ${
                activeTab === 'simulation'
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 font-medium'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-command-800/60'
              }`}
            >
              <div className="flex items-center space-x-2.5">
                <SlidersHorizontal className="w-4 h-4 text-blue-400" />
                <span>Flood Simulation</span>
              </div>
            </button>

            <button
              onClick={() => onSelectTab('risk-zones')}
              className={`w-full flex items-center justify-between px-2.5 py-2 rounded text-xs transition-colors ${
                activeTab === 'risk-zones'
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 font-medium'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-command-800/60'
              }`}
            >
              <div className="flex items-center space-x-2.5">
                <Activity className="w-4 h-4 text-amber-400" />
                <span>Risk Zones</span>
              </div>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-command-800 text-amber-400 border border-amber-500/20">
                {activeZoneCount}
              </span>
            </button>

            <button
              onClick={() => onSelectTab('validation')}
              className={`w-full flex items-center justify-between px-2.5 py-2 rounded text-xs transition-colors ${
                activeTab === 'validation'
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 font-medium'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-command-800/60'
              }`}
            >
              <div className="flex items-center space-x-2.5">
                <History className="w-4 h-4 text-emerald-400" />
                <span>Historical Validation</span>
              </div>
            </button>
          </div>
        </div>

        {/* Navigation Group 2: Intelligence */}
        <div>
          <div className="text-[10px] uppercase font-code tracking-widest text-slate-400 px-2 py-1">
            INTELLIGENCE
          </div>
          <div className="space-y-1 mt-1">
            <button
              onClick={() => onSelectTab('uncertainty')}
              className={`w-full flex items-center justify-between px-2.5 py-2 rounded text-xs transition-colors ${
                activeTab === 'uncertainty'
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 font-medium'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-command-800/60'
              }`}
            >
              <div className="flex items-center space-x-2.5">
                <Cpu className="w-4 h-4 text-purple-400" />
                <span>Uncertainty Bounds</span>
              </div>
            </button>

            <button
              onClick={() => onSelectTab('infrastructure')}
              className={`w-full flex items-center justify-between px-2.5 py-2 rounded text-xs transition-colors ${
                activeTab === 'infrastructure'
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 font-medium'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-command-800/60'
              }`}
            >
              <div className="flex items-center space-x-2.5">
                <Compass className="w-4 h-4 text-teal-400" />
                <span>Drainage Network</span>
              </div>
            </button>
          </div>
        </div>

        {/* Navigation Group 3: System Architecture */}
        <div>
          <div className="text-[10px] uppercase font-code tracking-widest text-slate-400 px-2 py-1">
            SYSTEM & DATA
          </div>
          <div className="space-y-1 mt-1">
            <button
              onClick={() => onSelectTab('data-layers')}
              className={`w-full flex items-center justify-between px-2.5 py-2 rounded text-xs transition-colors ${
                activeTab === 'data-layers'
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 font-medium'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-command-800/60'
              }`}
            >
              <div className="flex items-center space-x-2.5">
                <Database className="w-4 h-4 text-slate-400" />
                <span>Data Layers Status</span>
              </div>
            </button>

            <button
              onClick={() => onSelectTab('architecture')}
              className={`w-full flex items-center justify-between px-2.5 py-2 rounded text-xs transition-colors ${
                activeTab === 'architecture'
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 font-medium'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-command-800/60'
              }`}
            >
              <div className="flex items-center space-x-2.5">
                <Workflow className="w-4 h-4 text-sky-400" />
                <span>System Architecture</span>
              </div>
            </button>
          </div>
        </div>
      </div>

      {/* Model Status Card at Bottom */}
      <div className="p-3 border-t border-command-700/80 bg-command-950/70">
        <div className="rounded p-2.5 bg-command-850/80 border border-command-700 space-y-2">
          <div className="flex items-center justify-between text-[11px] font-mono">
            <span className="text-slate-400">ENGINE</span>
            <span className="text-cyan-400 font-semibold">TERRA05 v0.1</span>
          </div>
          <div className="flex items-center justify-between text-[11px] font-mono">
            <span className="text-slate-400">STATUS</span>
            <span className="text-emerald-400 flex items-center space-x-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block animate-pulse" />
              <span>Operational</span>
            </span>
          </div>
          <div className="text-[10px] text-slate-400 leading-tight border-t border-command-700/60 pt-1.5">
            Mithi River Catchment Hydrodynamic Mesh active
          </div>
        </div>
      </div>
    </aside>
  );
};
