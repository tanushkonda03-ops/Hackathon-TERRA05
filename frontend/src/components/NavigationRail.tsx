import React from 'react';
import { 
  Radar, 
  Activity, 
  History, 
  GitFork, 
  HelpCircle, 
  Layers, 
  Workflow, 
  Compass,
  FileText
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
    { id: 'overview', label: 'Overview', icon: Radar },
    { id: 'simulation', label: 'Simulation', icon: Activity },
    { id: 'risk', label: 'Risk Zones', icon: Layers },
    { id: 'validation', label: '2005 Event', icon: History },
    { id: 'drainage', label: 'Drainage', icon: Compass },
    { id: 'uncertainty', label: 'Uncertainty', icon: GitFork },
    { id: 'data', label: 'Data Layers', icon: FileText },
    { id: 'architecture', label: 'Architecture', icon: Workflow },
  ];

  return (
    <nav className="w-16 h-full bg-white border-r border-gis-border flex flex-col items-center justify-between py-3 z-30 select-none shadow-sm">
      {/* Brand Icon */}
      <div className="flex flex-col items-center space-y-1">
        <div className="w-9 h-9 rounded-lg bg-brand-600 text-white font-display font-bold flex items-center justify-center text-sm shadow-md">
          T05
        </div>
        <span className="text-[9px] font-mono font-bold tracking-tight text-gis-muted">
          MUMBAI
        </span>
      </div>

      {/* Nav Tool Icons Rail */}
      <div className="flex flex-col space-y-2">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              title={item.label}
              className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all ${
                isActive
                  ? 'bg-brand-50 text-brand-600 border border-brand-200 shadow-sm'
                  : 'text-gis-muted hover:text-gis-text hover:bg-gis-hover'
              }`}
            >
              <Icon className="w-5 h-5" />
            </button>
          );
        })}
      </div>

      {/* Operational Badge */}
      <div className="flex flex-col items-center space-y-1" title="System Operational">
        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
        <span className="text-[8px] font-mono text-gis-muted font-bold">ONLINE</span>
      </div>
    </nav>
  );
};
