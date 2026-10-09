import React, { useState, useRef, useEffect } from 'react';
import { Layers, ChevronDown, Check, Eye, EyeOff } from 'lucide-react';

interface MapLayersControlProps {
  layers: {
    floodSpots: boolean;
    drainage: boolean;
    runoffFlow: boolean;
    roadsExposure: boolean;
    criticalInfra: boolean;
    floodDepth: boolean;
    uncertainty: boolean;
    historical2019: boolean;
    terrain3D: boolean;
    riskGrid: boolean;
    evacuationRoutes: boolean;
  };
  onToggleLayer: (layerKey: keyof MapLayersControlProps['layers']) => void;
  onCameraPreset: (preset: '3D' | 'TOP' | 'RESET') => void;
  className?: string;
}

export const MapLayersControl: React.FC<MapLayersControlProps> = ({
  layers,
  onToggleLayer,
  onCameraPreset,
  className,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [activePreset, setActivePreset] = useState<'3D' | 'TOP' | 'RESET'>('3D');
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Click outside and escape key handling
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false);
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const handlePreset = (preset: '3D' | 'TOP' | 'RESET') => {
    setActivePreset(preset);
    onCameraPreset(preset);
  };

  const renderToggle = (
    label: string, 
    active: boolean, 
    onClick: () => void, 
    activeColorClass: string = 'text-sky-700 font-bold'
  ) => (
    <button
      onClick={onClick}
      className="w-full flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-slate-50 transition-colors group text-left"
    >
      <span className="text-slate-700 text-xs group-hover:text-slate-900">{label}</span>
      <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold border ${
        active 
          ? 'bg-sky-50 text-sky-800 border-sky-200 shadow-gis-xs' 
          : 'bg-slate-100 text-slate-400 border-slate-200'
      }`}>
        {active ? 'ON' : 'OFF'}
      </span>
    </button>
  );

  return (
    <div ref={dropdownRef} className={className || "absolute top-3.5 right-4 z-20 select-none flex items-start space-x-2"}>
      {/* 2D / 3D / Reset Camera Control Stack */}
      <div className="bg-white/95 backdrop-blur-md border border-gis-border rounded-xl shadow-gis p-1 flex items-center space-x-0.5">
        <button
          onClick={() => handlePreset('3D')}
          className={`px-2.5 py-1 rounded-lg text-xs font-mono font-bold transition-all ${
            activePreset === '3D'
              ? 'bg-slate-900 text-white shadow-gis-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
          title="3D Perspective View (Pitch 42°)"
        >
          3D
        </button>
        <button
          onClick={() => handlePreset('TOP')}
          className={`px-2.5 py-1 rounded-lg text-xs font-mono font-bold transition-all ${
            activePreset === 'TOP'
              ? 'bg-slate-900 text-white shadow-gis-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
          title="2D Top-down Nadir View (Pitch 0°)"
        >
          2D
        </button>
        <button
          onClick={() => handlePreset('RESET')}
          className="px-2 py-1 rounded-lg text-xs font-mono text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          title="Reset Camera Center"
        >
          RESET
        </button>
      </div>

      {/* Layer Control Menu */}
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          aria-expanded={isOpen}
          aria-label="Toggle map layers menu"
          className={`bg-white/95 backdrop-blur-md border border-gis-border px-3 py-1.5 rounded-xl shadow-gis text-xs font-mono font-bold flex items-center space-x-1.5 transition-all ${
            isOpen ? 'border-sky-500 ring-1 ring-sky-500 text-sky-800' : 'text-slate-800 hover:border-slate-300 hover:bg-white'
          }`}
        >
          <Layers className="w-3.5 h-3.5 text-sky-700" />
          <span>LAYERS</span>
          <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {isOpen && (
          <div className="absolute right-0 mt-1.5 w-72 bg-white border border-gis-border rounded-xl shadow-float p-3.5 space-y-3 z-30 font-mono text-xs max-h-[80vh] overflow-y-auto">
            {/* GROUP 1: BASE GEOGRAPHY */}
            <div>
              <span className="text-[9.5px] text-slate-400 font-bold uppercase tracking-wider block mb-1.5">
                BASE GEOGRAPHY
              </span>
              <div className="text-[11px] text-slate-600 space-y-1">
                <div className="flex items-center space-x-2 py-1 px-2 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="text-emerald-600 font-bold">✓</span>
                  <span className="text-slate-700">3D Building Extrusions</span>
                </div>
                <div className="flex items-center space-x-2 py-1 px-2 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="text-sky-600 font-bold">✓</span>
                  <span className="text-slate-700">Mithi River Natural Channel</span>
                </div>
              </div>
            </div>

            {/* MAP LEGEND SNIPPET */}
            <div className="border-t border-slate-100 pt-2.5">
              <span className="text-[9.5px] text-slate-400 font-bold uppercase tracking-wider block mb-1.5">
                MAP LEGEND
              </span>
              <div className="space-y-1.5 text-[11px] text-slate-600 bg-slate-50/70 p-2.5 rounded-lg border border-slate-100 font-sans">
                <div className="flex items-center gap-2">
                  <span className="w-4 border-t-2 border-cyan-600" />
                  <span>Drainage network</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-4 border-t-2 border-amber-600" />
                  <span>High drainage load</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-4 border-t-2 border-rose-600" />
                  <span>Overloaded / overflow</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-4 border-t-2 border-emerald-600" />
                  <span>Elevated Evac Corridor</span>
                </div>
              </div>
            </div>

            {/* GROUP 2: HYDROLOGY & DRAINAGE */}
            <div className="border-t border-slate-100 pt-2.5 space-y-1">
              <span className="text-[9.5px] text-slate-400 font-bold uppercase tracking-wider block mb-1">
                HYDROLOGY
              </span>
              {renderToggle('Stormwater Drains (SWD)', layers.drainage, () => onToggleLayer('drainage'))}
              {renderToggle('Runoff Flow Vectors', layers.runoffFlow, () => onToggleLayer('runoffFlow'))}
            </div>

            {/* GROUP 3: FLOOD MODEL */}
            <div className="border-t border-slate-100 pt-2.5 space-y-1">
              <span className="text-[9.5px] text-slate-400 font-bold uppercase tracking-wider block mb-1">
                FLOOD MODEL
              </span>
              {renderToggle('Simulated Inundation', layers.floodDepth, () => onToggleLayer('floodDepth'))}
              {renderToggle('100m ML Risk Grid', layers.riskGrid, () => onToggleLayer('riskGrid'))}
              {renderToggle('Uncertainty Boundary (90%)', layers.uncertainty, () => onToggleLayer('uncertainty'), 'text-indigo-600')}
              {renderToggle('Historical Replay (July 2019)', layers.historical2019, () => onToggleLayer('historical2019'), 'text-emerald-600')}
            </div>

            {/* GROUP 4: URBAN IMPACT */}
            <div className="border-t border-slate-100 pt-2.5 space-y-1">
              <span className="text-[9.5px] text-slate-400 font-bold uppercase tracking-wider block mb-1">
                URBAN IMPACT & EVACUATION
              </span>
              {renderToggle('🚑 Evac Corridors & Shelters', layers.evacuationRoutes, () => onToggleLayer('evacuationRoutes'), 'text-emerald-700 font-bold')}
              {renderToggle('Arterial Road Submergence', layers.roadsExposure, () => onToggleLayer('roadsExposure'), 'text-amber-700')}
              {renderToggle('Critical Infrastructure', layers.criticalInfra, () => onToggleLayer('criticalInfra'))}
              {renderToggle('BMC Chronic Flood Spots', layers.floodSpots, () => onToggleLayer('floodSpots'), 'text-rose-600')}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
