import React from 'react';
import { Download, ShieldAlert, Waves, X } from 'lucide-react';
import { SimulationResponse } from '../services/api';
import { TimelineImpactMetrics } from '../data/locations';
import { MOCK_HISTORICAL_VALIDATION } from '../data/mockData';

interface DecisionSupportPanelProps {
  rainfall: number;
  durationHours: number;
  tideLevel: 'normal' | 'high' | 'extreme';
  simulationData: SimulationResponse | null;
  timelineMetrics: TimelineImpactMetrics;
  onClose: () => void;
}

const tideLabel = { normal: 'Normal tide', high: 'High tide', extreme: 'Extreme tide' };

export const DecisionSupportPanel: React.FC<DecisionSupportPanelProps> = ({
  rainfall,
  durationHours,
  tideLevel,
  simulationData,
  timelineMetrics,
  onClose,
}) => {
  const peak = simulationData?.metrics.peak_water_depth_m ?? 0;
  const floodedArea = simulationData?.metrics.peak_inundated_area_km2 ?? timelineMetrics.floodedAreaKm2;
  const averageIntensity = durationHours > 0 ? rainfall / durationHours : rainfall;
  const comparison = [50, 100, 150].map((rate) => ({
    rate,
    depth: Math.max(0.05, (rate / Math.max(rainfall, 1)) * peak),
    area: Math.max(0.1, (rate / Math.max(rainfall, 1)) * floodedArea),
  }));

  const downloadBrief = () => {
    const brief = [
      'TERRA05 RESPONSE BRIEF',
      `Rainfall: ${rainfall} mm over ${durationHours} hours (average ${averageIntensity.toFixed(2)} mm/hr)`,
      `Tide condition: ${tideLabel[tideLevel]}`,
      `Warning stage: ${timelineMetrics.alertLevel}`,
      `Peak water depth: ${peak.toFixed(2)} m`,
      `Peak flooded area: ${floodedArea.toFixed(2)} km²`,
      `Population at risk: ${timelineMetrics.populationAtRisk.toLocaleString()}`,
      `Affected structures: ${timelineMetrics.affectedStructures.toLocaleString()}`,
      '',
      'RECOMMENDED ACTIONS',
      `- ${timelineMetrics.stageDescription}`,
      '- Prioritise pumps and road-control teams in the highest-risk zones.',
      '- Check critical facilities before the predicted peak.',
      '',
      'LIMITATION: Prototype scenario estimate; not a live emergency warning.',
    ].join('\n');
    const url = URL.createObjectURL(new Blob([brief], { type: 'text/plain' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'terra05-response-brief.txt';
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/30 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-float border border-gis-border max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-5">
        <div className="flex items-start justify-between border-b border-gis-border pb-3">
          <div>
            <p className="text-[10px] uppercase tracking-wider font-bold text-sky-700">Decision support</p>
            <h2 className="text-xl font-display font-bold text-slate-900 mt-1">What should happen next?</h2>
            <p className="text-sm text-slate-600 mt-1">A quick operational summary for this rainfall scenario.</p>
          </div>
          <button onClick={onClose} aria-label="Close decision support" className="text-slate-400 hover:text-slate-700"><X className="w-5 h-5" /></button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="p-3 rounded-lg bg-rose-50 border border-rose-200"><ShieldAlert className="w-5 h-5 text-rose-700 mb-2" /><p className="text-xs text-slate-600">Warning level</p><p className="font-bold text-rose-800">{timelineMetrics.alertLevel}</p></div>
          <div className="p-3 rounded-lg bg-sky-50 border border-sky-200"><Waves className="w-5 h-5 text-sky-700 mb-2" /><p className="text-xs text-slate-600">Peak water</p><p className="font-bold text-sky-900">{peak.toFixed(2)} m</p></div>
          <div className="p-3 rounded-lg bg-amber-50 border border-amber-200"><p className="text-xs text-slate-600">Tide effect</p><p className="font-bold text-amber-900">{tideLabel[tideLevel]}</p><p className="text-[10px] text-slate-600 mt-1">Higher tide slows drainage.</p></div>
        </div>

        <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
          <h3 className="text-sm font-bold text-slate-900">Recommended actions</h3>
          <ul className="mt-2 text-sm text-slate-700 space-y-1.5 list-disc list-inside">
            <li>Prepare pumps and response teams near the selected high-risk areas.</li>
            <li>Check roads and critical facilities before the expected peak.</li>
            <li>Issue a public advisory if water depth or flooded area keeps increasing.</li>
          </ul>
        </div>

        <div>
          <h3 className="text-sm font-bold text-slate-900 mb-2">Scenario comparison</h3>
          <p className="text-xs text-slate-600 mb-2">A quick comparison using the current result as the reference.</p>
          <div className="grid grid-cols-3 gap-2">
            {comparison.map((item) => <div key={item.rate} className="p-3 rounded-lg border border-slate-200"><p className="text-xs font-bold text-slate-900">{item.rate} mm/hr</p><p className="text-xs text-slate-600 mt-1">Depth: <strong>{item.depth.toFixed(2)} m</strong></p><p className="text-xs text-slate-600">Area: <strong>{item.area.toFixed(2)} km²</strong></p></div>)}
          </div>
        </div>

        <div className="p-3 rounded-lg bg-indigo-50 border border-indigo-200 text-xs text-indigo-950">
          <strong>Uncertainty:</strong> the displayed depth is an estimate. Actual flooding can change with rainfall timing, tide, blocked drains, and local pumping. Historical benchmark: IoU {MOCK_HISTORICAL_VALIDATION.metrics.iou}% on the prototype validation view.
        </div>

        <button onClick={downloadBrief} className="w-full py-2.5 bg-slate-900 text-white text-sm font-bold rounded-lg hover:bg-slate-800 flex items-center justify-center gap-2"><Download className="w-4 h-4" />Download response brief</button>
      </div>
    </div>
  );
};
