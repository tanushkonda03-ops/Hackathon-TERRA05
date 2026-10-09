import React from 'react';
import { 
  Map, 
  Activity, 
  Layers, 
  History, 
  Compass, 
  GitFork, 
  FileText, 
  Workflow
} from 'lucide-react';

export type NavTabId = 'overview' | 'simulation' | 'risk' | 'validation' | 'drainage' | 'uncertainty' | 'data' | 'architecture';

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
    { id: 'simulation', label: 'Simulate', icon: Activity },
    { id: 'risk', label: 'Risk Areas', icon: Layers },
    { id: 'validation', label: 'Past Floods', icon: History },
    { id: 'drainage', label: 'Drainage', icon: Compass },
    { id: 'uncertainty', label: 'Confidence', icon: GitFork },
    { id: 'data', label: 'Data Used', icon: FileText },
    { id: 'architecture', label: 'Technical Flow', icon: Workflow },
  ];

  return (
    <nav className="w-18 h-full bg-white border-r border-gis-border flex flex-col items-center justify-between py-2.5 z-30 select-none shadow-xs shrink-0">
      {/* Brand Icon */}
      <div className="flex flex-col items-center space-y-0.5">
        <div className="w-8 h-8 rounded-lg bg-sky-600 text-white font-display font-bold flex items-center justify-center text-xs shadow-xs">
          T05
        </div>
        <span className="text-[8px] font-mono font-bold tracking-tight text-slate-500">
          MUMBAI
        </span>
      </div>

      {/* Nav Tool Icons Rail with Clear Labels */}
      <div className="flex flex-col space-y-1.5 w-full px-1">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              title={item.label}
              className={`w-full py-1.5 px-0.5 rounded-lg flex flex-col items-center justify-center transition-all ${
                isActive
                  ? 'bg-sky-50 text-sky-700 border border-sky-200 shadow-xs'
                  : 'text-slate-500 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <Icon className="w-4 h-4 mb-0.5" />
              <span className="text-[9px] font-semibold text-center leading-tight tracking-tight">
                {item.label}
              </span>
            </button>
          );
        })}
      </div>

      {/* Operational Badge */}
      <div className="flex flex-col items-center space-y-0.5" title="System Operational">
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
        <span className="text-[7px] font-mono text-slate-400 font-bold">LIVE</span>
      </div>
    </nav>
  );
};
