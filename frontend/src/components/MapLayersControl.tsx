import React, { useState } from 'react';
import { Layers, ChevronDown } from 'lucide-react';

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
  };
  onToggleLayer: (layerKey: keyof MapLayersControlProps['layers']) => void;
  onCameraPreset: (preset: '3D' | 'TOP' | 'RESET') => void;
}

export const MapLayersControl: React.FC<MapLayersControlProps> = ({
  layers,
  onToggleLayer,
  onCameraPreset,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="absolute top-3 right-4 z-20 select-none flex items-start space-x-2">
      {/* 2D / 3D / Reset Camera Control Stack */}
      <div className="bg-white/95 backdrop-blur-md border border-gis-border rounded-lg shadow-gis p-1 flex items-center space-x-1">
        <button
          onClick={() => onCameraPreset('3D')}
          className="px-2.5 py-1 rounded text-xs font-mono font-bold text-slate-700 hover:bg-slate-100 hover:text-slate-900 transition-colors"
          title="3D Perspective View (Pitch 58°)"
        >
          3D
        </button>
        <button
          onClick={() => onCameraPreset('TOP')}
          className="px-2.5 py-1 rounded text-xs font-mono font-bold text-slate-700 hover:bg-slate-100 hover:text-slate-900 transition-colors"
          title="2D Top-down Nadir View"
        >
          2D
        </button>
        <button
          onClick={() => onCameraPreset('RESET')}
          className="px-2 py-1 rounded text-xs font-mono text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          title="Reset Camera Center"
        >
          RESET
        </button>
      </div>

      {/* Layer Control Menu */}
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="bg-white/95 backdrop-blur-md border border-gis-border px-3 py-1.5 rounded-lg shadow-gis text-xs font-mono font-bold text-slate-800 flex items-center space-x-1.5 hover:bg-white transition-all"
        >
          <Layers className="w-3.5 h-3.5 text-slate-500" />
          <span>LAYERS</span>
          <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
        </button>

        {isOpen && (
          <div className="absolute right-0 mt-1.5 w-68 bg-white border border-gis-border rounded-lg shadow-float p-3 space-y-3 z-30 font-mono text-xs">
            {/* GROUP 1: BASE GEOGRAPHY */}
            <div>
              <span className="text-[10px] text-slate-400 font-bold uppercase block mb-1">
                BASE GEOGRAPHY
              </span>
              <div className="text-[11px] text-slate-600 space-y-0.5">
                <div className="flex items-center space-x-1.5">
                  <span className="text-emerald-600">✓</span>
                  <span>3D Building Extrusions</span>
                </div>

                <div className="border-t border-slate-100 pt-2">
                  <span className="text-[10px] text-slate-400 font-bold uppercase block mb-1">MAP LEGEND</span>
                  <div className="space-y-1 text-[11px] text-slate-600">
                    <div className="flex items-center gap-2"><span className="w-5 border-t-2 border-cyan-600 border-dashed" /> Drainage network</div>
                    <div className="flex items-center gap-2"><span className="w-5 border-t-2 border-amber-600" /> High drainage load</div>
                    <div className="flex items-center gap-2"><span className="w-5 border-t-2 border-red-600" /> Overloaded / overflow</div>
                  </div>
                </div>
                <div className="flex items-center space-x-1.5">
                  <span className="text-emerald-600">✓</span>
                  <span>Mithi River Natural Channel</span>
                </div>
              </div>
            </div>

            {/* GROUP 2: HYDROLOGY & DRAINAGE */}
            <div className="border-t border-slate-100 pt-2 space-y-1">
              <span className="text-[10px] text-slate-400 font-bold uppercase block mb-1">
                HYDROLOGY
              </span>

              <button
                onClick={() => onToggleLayer('drainage')}
                className="w-full flex items-center justify-between py-1 px-1 rounded hover:bg-slate-50"
              >
                <span>Stormwater Drains (SWD)</span>
                <span className={layers.drainage ? 'text-sky-700 font-bold' : 'text-slate-400'}>
                  {layers.drainage ? 'ON' : 'OFF'}
                </span>
              </button>

              <button
                onClick={() => onToggleLayer('runoffFlow')}
                className="w-full flex items-center justify-between py-1 px-1 rounded hover:bg-slate-50"
              >
                <span>Runoff Flow Vectors</span>
                <span className={layers.runoffFlow ? 'text-sky-700 font-bold' : 'text-slate-400'}>
                  {layers.runoffFlow ? 'ON' : 'OFF'}
                </span>
              </button>
            </div>

            {/* GROUP 3: FLOOD MODEL */}
            <div className="border-t border-slate-100 pt-2 space-y-1">
              <span className="text-[10px] text-slate-400 font-bold uppercase block mb-1">
                FLOOD MODEL
              </span>

              <button
                onClick={() => onToggleLayer('floodDepth')}
                className="w-full flex items-center justify-between py-1 px-1 rounded hover:bg-slate-50"
              >
                <span>Simulated Inundation</span>
                <span className={layers.floodDepth ? 'text-sky-700 font-bold' : 'text-slate-400'}>
                  {layers.floodDepth ? 'ON' : 'OFF'}
                </span>
              </button>

              <button
                onClick={() => onToggleLayer('riskGrid')}
                className="w-full flex items-center justify-between py-1 px-1 rounded hover:bg-slate-50"
              >
                <span>100m ML Risk Grid</span>
                <span className={layers.riskGrid ? 'text-sky-700 font-bold' : 'text-slate-400'}>
                  {layers.riskGrid ? 'ON' : 'OFF'}
                </span>
              </button>

              <button
                onClick={() => onToggleLayer('uncertainty')}
                className="w-full flex items-center justify-between py-1 px-1 rounded hover:bg-slate-50"
              >
                <span>Uncertainty Boundary (90%)</span>
                <span className={layers.uncertainty ? 'text-indigo-600 font-bold' : 'text-slate-400'}>
                  {layers.uncertainty ? 'ON' : 'OFF'}
                </span>
              </button>

              <button
                onClick={() => onToggleLayer('historical2019')}
                className="w-full flex items-center justify-between py-1 px-1 rounded hover:bg-slate-50"
              >
                <span>Historical Replay (July 2019)</span>
                <span className={layers.historical2019 ? 'text-emerald-600 font-bold' : 'text-slate-400'}>
                  {layers.historical2019 ? 'ON' : 'OFF'}
                </span>
              </button>
            </div>

            {/* GROUP 4: URBAN IMPACT */}
            <div className="border-t border-slate-100 pt-2 space-y-1">
              <span className="text-[10px] text-slate-400 font-bold uppercase block mb-1">
                URBAN IMPACT
              </span>

              <button
                onClick={() => onToggleLayer('roadsExposure')}
                className="w-full flex items-center justify-between py-1 px-1 rounded hover:bg-slate-50"
              >
                <span>Arterial Road Submergence</span>
                <span className={layers.roadsExposure ? 'text-amber-700 font-bold' : 'text-slate-400'}>
                  {layers.roadsExposure ? 'ON' : 'OFF'}
                </span>
              </button>

              <button
                onClick={() => onToggleLayer('criticalInfra')}
                className="w-full flex items-center justify-between py-1 px-1 rounded hover:bg-slate-50"
              >
                <span>Critical Infrastructure</span>
                <span className={layers.criticalInfra ? 'text-slate-900 font-bold' : 'text-slate-400'}>
                  {layers.criticalInfra ? 'ON' : 'OFF'}
                </span>
              </button>

              <button
                onClick={() => onToggleLayer('floodSpots')}
                className="w-full flex items-center justify-between py-1 px-1 rounded hover:bg-slate-50"
              >
                <span>BMC Chronic Flood Spots</span>
                <span className={layers.floodSpots ? 'text-rose-600 font-bold' : 'text-slate-400'}>
                  {layers.floodSpots ? 'ON' : 'OFF'}
                </span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
