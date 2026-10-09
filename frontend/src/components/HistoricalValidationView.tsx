import React, { useState } from 'react';
import { 
  History, 
  Calendar, 
  CheckCircle2, 
  BarChart2, 
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
    <div className="flex-1 overflow-y-auto p-6 space-y-6 select-none bg-slate-50/50 min-h-full">
      {/* View Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gis-border pb-4 bg-white p-5 rounded-xl shadow-gis-xs border">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold">
              HISTORICAL BENCHMARK
            </span>
            <span className="text-xs font-mono text-slate-500 uppercase tracking-wider">EVENT RECONSTRUCTION</span>
          </div>
          <h1 className="text-xl font-bold text-slate-900 mt-1 tracking-tight">
            Historical Event Reconstruction: {data.eventName}
          </h1>
          <div className="text-xs text-slate-500 flex items-center space-x-2 mt-1 font-mono">
            <Calendar className="w-3.5 h-3.5 text-sky-600" />
            <span>Recorded Date: <strong>{data.eventDate}</strong></span>
            <span>•</span>
            <span>Peak 24h Rainfall: <strong>{data.peakRainfallMm} mm</strong></span>
          </div>
        </div>

        {/* View Mode Switcher */}
        <div className="flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200 shadow-gis-xs">
          <button
            onClick={() => setViewMode('PREDICTED')}
            className={`px-3 py-1.5 rounded-md text-xs font-mono font-bold transition-all ${
              viewMode === 'PREDICTED'
                ? 'bg-white text-sky-800 shadow-gis-xs border border-slate-200/80'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            TERRA05 Predicted
          </button>
          <button
            onClick={() => setViewMode('OBSERVED')}
            className={`px-3 py-1.5 rounded-md text-xs font-mono font-bold transition-all ${
              viewMode === 'OBSERVED'
                ? 'bg-white text-emerald-800 shadow-gis-xs border border-slate-200/80'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Observed Ground Truth
          </button>
          <button
            onClick={() => setViewMode('DIFFERENCE')}
            className={`px-3 py-1.5 rounded-md text-xs font-mono font-bold transition-all ${
              viewMode === 'DIFFERENCE'
                ? 'bg-white text-amber-800 shadow-gis-xs border border-slate-200/80'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Difference / Residual
          </button>
        </div>
      </div>

      {/* Benchmark Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-white border border-gis-border shadow-gis-xs">
          <div className="text-[10px] font-mono text-slate-400 font-bold uppercase tracking-wider">
            Intersection Over Union (IoU)
          </div>
          <div className="text-2xl font-mono font-bold text-sky-800 mt-1">
            {data.metrics.iou}%
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-1">
            Spatial extent overlap
          </div>
        </div>

        <div className="p-4 rounded-xl bg-white border border-gis-border shadow-gis-xs">
          <div className="text-[10px] font-mono text-slate-400 font-bold uppercase tracking-wider">
            Spatial Precision
          </div>
          <div className="text-2xl font-mono font-bold text-emerald-700 mt-1">
            {data.metrics.precision}%
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-1">
            Low false-positive rate
          </div>
        </div>

        <div className="p-4 rounded-xl bg-white border border-gis-border shadow-gis-xs">
          <div className="text-[10px] font-mono text-slate-400 font-bold uppercase tracking-wider">
            Catchment Recall
          </div>
          <div className="text-2xl font-mono font-bold text-blue-700 mt-1">
            {data.metrics.recall}%
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-1">
            Observed zone coverage
          </div>
        </div>

        <div className="p-4 rounded-xl bg-white border border-gis-border shadow-gis-xs">
          <div className="text-[10px] font-mono text-slate-400 font-bold uppercase tracking-wider">
            F1 Accuracy Score
          </div>
          <div className="text-2xl font-mono font-bold text-indigo-700 mt-1">
            {data.metrics.f1Score}%
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-1">
            Harmonic spatial mean
          </div>
        </div>
      </div>

      {/* Detailed Zone Reconstruction Table */}
      <div className="rounded-xl bg-white border border-gis-border overflow-hidden shadow-gis-xs">
        <div className="px-5 py-3.5 border-b border-gis-border bg-slate-50/70 flex items-center justify-between">
          <h3 className="text-xs font-mono font-bold text-slate-800 uppercase tracking-wide">
            MITHI BASIN LOCALITY VALIDATION TELEMETRY (26 JULY 2005)
          </h3>
          <span className="text-[10px] font-mono text-slate-500">
            Active Mode: <strong className="text-sky-800">{viewMode}</strong>
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-50 text-slate-500 text-[10px] uppercase border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-4 font-bold">Catchment Zone</th>
                <th className="py-2.5 px-4 text-right font-bold">Observed Depth</th>
                <th className="py-2.5 px-4 text-right font-bold">TERRA05 Model</th>
                <th className="py-2.5 px-4 text-right font-bold">Delta (Residual)</th>
                <th className="py-2.5 px-4 text-center font-bold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.zones.map((row, idx) => (
                <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3 px-4 font-bold text-slate-800">
                    {row.name}
                  </td>
                  <td className="py-3 px-4 text-right text-slate-600">
                    {row.observedDepthM.toFixed(2)} m
                  </td>
                  <td className="py-3 px-4 text-right text-sky-800 font-bold">
                    {row.predictedDepthM.toFixed(2)} m
                  </td>
                  <td className={`py-3 px-4 text-right ${row.differenceM > 0 ? 'text-amber-700' : 'text-emerald-700'}`}>
                    {row.differenceM > 0 ? `+${row.differenceM.toFixed(2)}` : row.differenceM.toFixed(2)} m
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-[9.5px] font-bold ${
                        row.status === 'MATCH'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : 'bg-amber-50 text-amber-700 border border-amber-200'
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
      <div className="p-4 rounded-xl bg-amber-50/80 border border-amber-200 text-amber-900 text-xs leading-relaxed shadow-gis-xs">
        <div className="flex items-center space-x-2 font-bold text-amber-900 mb-1">
          <Info className="w-4 h-4 text-amber-700 shrink-0" />
          <span className="font-mono text-xs">PROTOTYPE / DEMONSTRATION NOTICE</span>
        </div>
        <p className="text-slate-700">{data.disclaimer}</p>
      </div>
    </div>
  );
};
