import React from 'react';
import { Layers, Eye, EyeOff } from 'lucide-react';
import { LayerState } from '../types';

interface LayerControlsProps {
  layers: LayerState;
  onToggleLayer: (layerKey: keyof LayerState) => void;
}

export const LayerControls: React.FC<LayerControlsProps> = ({
  layers,
  onToggleLayer,
}) => {
  const layerItems: { key: keyof LayerState; label: string; desc: string; badge?: string }[] = [
    { key: 'terrain', label: 'Terrain Mesh', desc: 'Digital Elevation Model (DEM)' },
    { key: 'buildings', label: 'Extruded Buildings', desc: 'BMC Building footprint polygons' },
    { key: 'roads', label: 'Arterial Roads', desc: 'Major transit corridors & highways' },
    { key: 'stormwaterDrains', label: 'Stormwater Drains', desc: 'Mithi River outfalls & trunk conduits', badge: 'NET' },
    { key: 'floodRisk', label: 'Flood Risk Hotspots', desc: 'Predicted spatial probability clusters' },
    { key: 'floodDepth', label: 'Flood Water Depth', desc: 'Dynamic hydrodynamic surface overlay' },
    { key: 'uncertainty', label: 'Prediction Interval (Uncertainty)', desc: '90% credible intervals envelope', badge: '90%' },
    { key: 'historicalFloodExtent', label: '26 July 2005 Baseline', desc: 'Historical ground-truth verification', badge: '2005' },
  ];

  return (
    <div className="absolute top-4 right-4 z-10 w-64 bg-command-900/90 backdrop-blur-md border border-command-700/80 rounded-lg p-3 shadow-hud select-none">
      <div className="flex items-center justify-between border-b border-command-700/60 pb-2 mb-2">
        <div className="flex items-center space-x-1.5 text-xs font-tech font-bold text-slate-200">
          <Layers className="w-3.5 h-3.5 text-cyan-400" />
          <span>GEOSPATIAL LAYERS</span>
        </div>
        <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/80 px-1.5 py-0.5 rounded border border-cyan-500/20">
          GIS ENGINE
        </span>
      </div>

      <div className="space-y-1.5 max-h-[380px] overflow-y-auto pr-1">
        {layerItems.map((item) => {
          const isActive = layers[item.key];
          return (
            <button
              key={item.key}
              onClick={() => onToggleLayer(item.key)}
              className={`w-full flex items-center justify-between p-2 rounded text-left transition-all ${
                isActive
                  ? 'bg-command-800/80 border border-cyan-500/30 text-slate-100'
                  : 'bg-command-950/50 border border-transparent text-slate-400 hover:text-slate-300 hover:bg-command-850/60'
              }`}
            >
              <div className="flex items-start space-x-2">
                <div className={`mt-0.5 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`}>
                  {isActive ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
                </div>
                <div>
                  <div className="text-xs font-medium flex items-center space-x-1.5">
                    <span>{item.label}</span>
                    {item.badge && (
                      <span className="text-[9px] font-mono px-1 rounded bg-command-700 text-cyan-300">
                        {item.badge}
                      </span>
                    )}
                  </div>
                  <div className="text-[10px] text-slate-400 leading-tight">
                    {item.desc}
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
