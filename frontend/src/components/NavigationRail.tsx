import React from 'react';
import { 
  Map, 
  History, 
  FileText, 
  Workflow
} from 'lucide-react';

export type NavTabId = 'overview' | 'validation' | 'data' | 'architecture';

interface NavigationRailProps {
  activeTab: NavTabId;
  onSelectTab: (tab: NavTabId) => void;
}

export const NavigationRail: React.FC<NavigationRailProps> = ({
  activeTab,
  onSelectTab,
}) => {
  const items: { id: NavTabId; label: string; icon: React.FC<{ className?: string }> }[] = [
    { id: 'overview', label: 'Flood Map', icon: Map },
    { id: 'validation', label: 'Past Floods', icon: History },
    { id: 'data', label: 'Data Used', icon: FileText },
    { id: 'architecture', label: 'Technical Flow', icon: Workflow },
  ];

  return (
    <nav 
      aria-label="Main Navigation" 
      className="w-16 h-full bg-white border-r border-gis-border flex flex-col items-center justify-between py-2 z-30 select-none shadow-gis-xs shrink-0"
    >
      {/* Brand Monogram */}
      <div className="flex flex-col items-center space-y-0.5 pt-0.5">
        <div 
          className="w-8 h-8 rounded-lg bg-gradient-to-b from-sky-600 to-sky-700 text-white font-mono font-bold flex items-center justify-center text-xs shadow-gis-xs tracking-wider"
          title="TERRA05 - Mumbai Urban Flood Digital Twin"
        >
          T05
        </div>
        <span className="text-[7.5px] font-mono font-bold tracking-wider text-slate-400 uppercase">
          MUMBAI
        </span>
      </div>

      {/* Nav Tool Icons Rail with Clear Labels */}
      <div className="flex flex-col space-y-1 w-full px-1.5 my-auto">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              title={item.label}
              aria-label={item.label}
              aria-current={isActive ? 'page' : undefined}
              className={`relative w-full py-1.5 px-0.5 rounded-lg flex flex-col items-center justify-center transition-all group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 ${
                isActive
                  ? 'bg-sky-50/90 text-sky-800 font-semibold shadow-gis-xs before:absolute before:left-0 before:top-1.5 before:bottom-1.5 before:w-1 before:bg-sky-600 before:rounded-r'
                  : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100/70'
              }`}
            >
              <Icon className={`w-4 h-4 mb-0.5 transition-transform duration-150 ${isActive ? 'text-sky-700 scale-105' : 'text-slate-400 group-hover:text-slate-700'}`} />
              <span className="text-[8.5px] text-center leading-tight tracking-tight">
                {item.label}
              </span>
            </button>
          );
        })}
      </div>

      {/* Operational Liveness Indicator */}
      <div className="flex flex-col items-center space-y-0.5 pb-1" title="System Operational & Telemetry Connected">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
        </span>
        <span className="text-[7px] font-mono text-slate-400 font-bold uppercase tracking-wider">
          LIVE
        </span>
      </div>
    </nav>
  );
};
