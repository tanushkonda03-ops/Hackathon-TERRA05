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
    <div className="absolute top-4 right-4 z-10 w-68 bg-white/95 backdrop-blur-md border border-gis-border rounded-xl p-3.5 shadow-float select-none">
      <div className="flex items-center justify-between border-b border-gis-border pb-2.5 mb-2.5">
        <div className="flex items-center space-x-1.5 text-xs font-bold text-slate-800">
          <Layers className="w-3.5 h-3.5 text-sky-700" />
          <span>GEOSPATIAL LAYERS</span>
        </div>
        <span className="text-[10px] font-mono text-sky-700 bg-sky-50 px-2 py-0.5 rounded border border-sky-200 font-bold">
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
              className={`w-full flex items-center justify-between p-2 rounded-lg text-left transition-all ${
                isActive
                  ? 'bg-sky-50/80 border border-sky-200 text-sky-950 shadow-gis-xs'
                  : 'bg-slate-50 border border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <div className="flex items-start space-x-2">
                <div className={`mt-0.5 ${isActive ? 'text-sky-700' : 'text-slate-400'}`}>
                  {isActive ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
                </div>
                <div>
                  <div className="text-xs font-semibold flex items-center space-x-1.5">
                    <span>{item.label}</span>
                    {item.badge && (
                      <span className="text-[9px] font-mono px-1 rounded bg-slate-200 text-slate-700">
                        {item.badge}
                      </span>
                    )}
                  </div>
                  <div className="text-[10px] text-slate-500 leading-tight mt-0.5">
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
