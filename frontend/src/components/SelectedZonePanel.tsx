import React from 'react';
import { 
  X, 
  MapPin, 
  Droplets, 
  Compass, 
  ShieldAlert, 
  TrendingUp, 
  HelpCircle,
  Building,
  Users,
  AlertCircle
} from 'lucide-react';
import { RiskZone } from '../types';

interface SelectedZonePanelProps {
  zone: RiskZone;
  rainfall: number;
  onClose: () => void;
}

export const SelectedZonePanel: React.FC<SelectedZonePanelProps> = ({
  zone,
  rainfall,
  onClose,
}) => {
  const data = zone.scenarioData[rainfall] || zone.scenarioData[100];

  return (
    <div className="absolute bottom-32 left-6 z-20 w-96 bg-command-900/95 backdrop-blur-md border border-command-700/80 rounded-lg p-4 shadow-hud select-none">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-command-700/60 pb-3">
        <div>
          <div className="flex items-center space-x-2">
            <span
              className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded uppercase ${
                data.severity === 'SEVERE'
                  ? 'bg-rose-950 text-rose-300 border border-rose-500/50'
                  : data.severity === 'WARNING'
                  ? 'bg-amber-950 text-amber-300 border border-amber-500/50'
                  : 'bg-yellow-950 text-yellow-300 border border-yellow-500/50'
              }`}
            >
              {data.severity} RISK
            </span>
            <span className="text-[10px] font-mono text-cyan-400">{zone.ward}</span>
          </div>
          <h2 className="text-base font-tech font-bold text-white mt-1 tracking-wide">
            {zone.name}
          </h2>
          <div className="text-[10px] text-slate-400 font-mono flex items-center space-x-1 mt-0.5">
            <MapPin className="w-3 h-3 text-cyan-400" />
            <span>{zone.catchment}</span>
          </div>
        </div>

        <button
          onClick={onClose}
          className="text-slate-400 hover:text-white p-1 rounded hover:bg-command-800 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-2 gap-2 my-3">
        {/* Flood Probability */}
        <div className="p-2.5 rounded bg-command-850/80 border border-command-700">
          <div className="text-[10px] uppercase font-mono text-slate-400">Flood Probability</div>
          <div className="text-lg font-tech font-bold text-cyan-300 mt-0.5">
            {data.probability}%
          </div>
          <div className="w-full bg-command-950 h-1.5 rounded-full mt-1.5 overflow-hidden">
            <div
              className="bg-cyan-400 h-full rounded-full"
              style={{ width: `${data.probability}%` }}
            />
          </div>
        </div>

        {/* Expected Water Depth */}
        <div className="p-2.5 rounded bg-command-850/80 border border-command-700">
          <div className="text-[10px] uppercase font-mono text-slate-400">Expected Depth</div>
          <div className="text-lg font-tech font-bold text-amber-300 mt-0.5">
            {data.expectedDepthM.toFixed(2)} m
          </div>
          <div className="text-[9px] text-slate-400 font-mono mt-1">
            Plinth surcharge risk
          </div>
        </div>
      </div>

      {/* Uncertainty: 90% Prediction Interval */}
      <div className="p-2.5 rounded bg-command-850/80 border border-command-700 mb-3">
        <div className="flex items-center justify-between text-[10px] font-mono">
          <span className="text-slate-400">90% PREDICTION INTERVAL</span>
          <span className="text-purple-400 font-bold">
            {data.interval90[0].toFixed(2)}m — {data.interval90[1].toFixed(2)}m
          </span>
        </div>

        {/* Graphic Range Marker */}
        <div className="relative mt-2 h-4 bg-command-950 rounded flex items-center px-2">
          <div
            className="absolute h-2 bg-purple-500/40 border-l-2 border-r-2 border-purple-400 rounded-sm"
            style={{
              left: `${Math.min(80, Math.max(10, data.interval90[0] * 50))}%`,
              right: `${Math.max(5, 100 - data.interval90[1] * 65)}%`,
            }}
          />
          {/* Target marker point */}
          <div
            className="absolute w-2 h-3 bg-amber-400 rounded-xs shadow-glow-cyan"
            style={{ left: `${Math.min(90, Math.max(15, data.expectedDepthM * 60))}%` }}
          />
        </div>

        <div className="flex items-start space-x-1.5 text-[9px] text-slate-400 mt-2">
          <HelpCircle className="w-3 h-3 text-purple-400 shrink-0 mt-0.5" />
          <span>
            Uncertainty represents the expected range around the predicted flood depth. Final values will come from the calibrated prediction engine.
          </span>
        </div>
      </div>

      {/* Geospatial Feature Parameters */}
      <div className="grid grid-cols-3 gap-1.5 text-[10px] font-mono mb-3">
        <div className="p-1.5 rounded bg-command-900 border border-command-700/60">
          <div className="text-slate-400">Elevation</div>
          <div className="text-slate-200 font-bold">{zone.elevationMeters}m MSL</div>
        </div>
        <div className="p-1.5 rounded bg-command-900 border border-command-700/60">
          <div className="text-slate-400">Drain Dist</div>
          <div className="text-slate-200 font-bold">{zone.drainProximityMeters}m</div>
        </div>
        <div className="p-1.5 rounded bg-command-900 border border-command-700/60">
          <div className="text-slate-400">Impervious</div>
          <div className="text-slate-200 font-bold">{zone.imperviousPercent}%</div>
        </div>
      </div>

      {/* Impact Footprint */}
      <div className="flex items-center justify-between text-[10px] font-mono bg-command-800/60 p-2 rounded border border-command-700/60 mb-3">
        <div className="flex items-center space-x-1.5 text-slate-300">
          <Building className="w-3.5 h-3.5 text-cyan-400" />
          <span>{data.affectedStructures} Structures</span>
        </div>
        <div className="flex items-center space-x-1.5 text-slate-300">
          <Users className="w-3.5 h-3.5 text-amber-400" />
          <span>~{data.populationAtRisk.toLocaleString()} Residents</span>
        </div>
      </div>

      {/* Explainable AI Diagnostics Box */}
      <div className="p-2.5 rounded bg-cyan-950/40 border border-cyan-500/30 text-[10px] text-cyan-200/90 leading-relaxed font-sans">
        <div className="font-tech font-bold uppercase tracking-wider text-cyan-400 mb-1 flex items-center space-x-1">
          <AlertCircle className="w-3 h-3 text-cyan-400" />
          <span>MODEL EXPLAINABILITY INSIGHT</span>
        </div>
        <p>{zone.explanation}</p>
      </div>
    </div>
  );
};
