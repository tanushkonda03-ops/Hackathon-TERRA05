import React, { useState } from 'react';
import { 
  History, 
  Calendar, 
  CheckCircle2, 
  BarChart, 
  Info, 
  SplitSquareVertical, 
  Layers, 
  ArrowRight
} from 'lucide-react';
import { MOCK_HISTORICAL_VALIDATION } from '../data/mockData';

export const HistoricalValidationView: React.FC = () => {
  const [viewMode, setViewMode] = useState<'PREDICTED' | 'OBSERVED' | 'DIFFERENCE'>('PREDICTED');
  const data = MOCK_HISTORICAL_VALIDATION;

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 select-none">
      {/* View Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-command-700/80 pb-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950 text-emerald-400 border border-emerald-500/30 font-bold">
              HISTORICAL BENCHMARK
            </span>
            <span className="text-xs font-mono text-slate-400">EVENT RECONSTRUCTION</span>
          </div>
          <h1 className="text-xl font-tech font-bold text-white mt-1">
            Historical Event Reconstruction: {data.eventName}
          </h1>
          <div className="text-xs text-slate-400 flex items-center space-x-2 mt-1">
            <Calendar className="w-3.5 h-3.5 text-cyan-400" />
            <span>Recorded Date: {data.eventDate}</span>
            <span>•</span>
            <span>Peak 24h Rainfall: {data.peakRainfallMm} mm</span>
          </div>
        </div>

        {/* View Mode Switcher */}
        <div className="flex items-center bg-command-850 p-1 rounded-lg border border-command-700">
          <button
            onClick={() => setViewMode('PREDICTED')}
            className={`px-3 py-1.5 rounded text-xs font-tech font-bold transition-all ${
              viewMode === 'PREDICTED'
                ? 'bg-cyan-500 text-command-950 shadow-glow-cyan'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            TERRA05 Predicted
          </button>
          <button
            onClick={() => setViewMode('OBSERVED')}
            className={`px-3 py-1.5 rounded text-xs font-tech font-bold transition-all ${
              viewMode === 'OBSERVED'
                ? 'bg-cyan-500 text-command-950 shadow-glow-cyan'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Observed Ground Truth
          </button>
          <button
            onClick={() => setViewMode('DIFFERENCE')}
            className={`px-3 py-1.5 rounded text-xs font-tech font-bold transition-all ${
              viewMode === 'DIFFERENCE'
                ? 'bg-amber-500 text-command-950'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Difference / Residual
          </button>
        </div>
      </div>

      {/* Benchmark Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-lg bg-command-900 border border-command-700 shadow-hud">
          <div className="text-[10px] font-mono text-slate-400 uppercase">Intersection Over Union (IoU)</div>
          <div className="text-2xl font-tech font-bold text-cyan-300 mt-1">
            {data.metrics.iou}%
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-1">
            Spatial extent overlap
          </div>
        </div>

        <div className="p-4 rounded-lg bg-command-900 border border-command-700 shadow-hud">
          <div className="text-[10px] font-mono text-slate-400 uppercase">Spatial Precision</div>
          <div className="text-2xl font-tech font-bold text-emerald-400 mt-1">
            {data.metrics.precision}%
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-1">
            Low false-positive rate
          </div>
        </div>

        <div className="p-4 rounded-lg bg-command-900 border border-command-700 shadow-hud">
          <div className="text-[10px] font-mono text-slate-400 uppercase">Catchment Recall</div>
          <div className="text-2xl font-tech font-bold text-blue-400 mt-1">
            {data.metrics.recall}%
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-1">
            Observed zone coverage
          </div>
        </div>

        <div className="p-4 rounded-lg bg-command-900 border border-command-700 shadow-hud">
          <div className="text-[10px] font-mono text-slate-400 uppercase">F1 Accuracy Score</div>
          <div className="text-2xl font-tech font-bold text-purple-400 mt-1">
            {data.metrics.f1Score}%
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-1">
            Harmonic spatial mean
          </div>
        </div>
      </div>

      {/* Detailed Zone Reconstruction Table */}
      <div className="rounded-lg bg-command-900 border border-command-700 overflow-hidden shadow-hud">
        <div className="px-4 py-3 border-b border-command-700 bg-command-850/60 flex items-center justify-between">
          <h3 className="text-xs font-tech font-bold text-slate-200">
            MITHI BASIN LOCALITY VALIDATION TELEMETRY (26 JULY 2005)
          </h3>
          <span className="text-[10px] font-mono text-slate-400">
            Active Mode: <strong className="text-cyan-400">{viewMode}</strong>
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-command-950/80 text-slate-400 text-[10px] uppercase border-b border-command-800">
              <tr>
                <th className="py-2.5 px-4">Catchment Zone</th>
                <th className="py-2.5 px-4 text-right">Observed Depth</th>
                <th className="py-2.5 px-4 text-right">TERRA05 Model</th>
                <th className="py-2.5 px-4 text-right">Delta (Residual)</th>
                <th className="py-2.5 px-4 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-command-800/60">
              {data.zones.map((row, idx) => (
                <tr key={idx} className="hover:bg-command-800/40 transition-colors">
                  <td className="py-3 px-4 font-tech font-bold text-slate-200">
                    {row.name}
                  </td>
                  <td className="py-3 px-4 text-right text-slate-300">
                    {row.observedDepthM.toFixed(2)} m
                  </td>
                  <td className="py-3 px-4 text-right text-cyan-300 font-bold">
                    {row.predictedDepthM.toFixed(2)} m
                  </td>
                  <td className={`py-3 px-4 text-right ${row.differenceM > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                    {row.differenceM > 0 ? `+${row.differenceM.toFixed(2)}` : row.differenceM.toFixed(2)} m
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-[9px] font-bold ${
                        row.status === 'MATCH'
                          ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/40'
                          : 'bg-amber-950 text-amber-300 border border-amber-500/40'
                      }`}
                    >
                      {row.status === 'MATCH' ? 'CONGRUENT' : 'SLIGHT DELTA'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Mandatory Disclaimer Box */}
      <div className="p-4 rounded-lg bg-amber-950/30 border border-amber-500/40 text-amber-200/90 text-xs leading-relaxed">
        <div className="flex items-center space-x-2 font-tech font-bold text-amber-400 mb-1">
          <Info className="w-4 h-4 text-amber-400" />
          <span>PROTOTYPE / DEMONSTRATION NOTICE</span>
        </div>
        <p>{data.disclaimer}</p>
      </div>
    </div>
  );
};
