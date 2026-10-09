import React from 'react';
import { CloudRain, MapPin, MousePointerClick, X } from 'lucide-react';

interface HowItWorksModalProps {
  onClose: () => void;
}

export const HowItWorksModal: React.FC<HowItWorksModalProps> = ({ onClose }) => {
  return (
    <div className="fixed inset-0 z-50 bg-slate-900/30 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-float border border-gis-border max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-5">
        <div className="flex items-start justify-between border-b border-gis-border pb-3">
          <div>
            <p className="text-[10px] uppercase tracking-wider font-bold text-sky-700">Quick guide</p>
            <h2 className="text-xl font-display font-bold text-slate-900 mt-1">How to use the flood map</h2>
            <p className="text-sm text-slate-600 mt-1">Pick a place and a rain scenario to see where water may collect.</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700" aria-label="Close guide">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div>
          <h3 className="text-sm font-bold text-slate-900 mb-2">What you can enter</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-3 rounded-lg bg-sky-50 border border-sky-200">
              <MapPin className="w-5 h-5 text-sky-700 mb-2" />
              <p className="text-xs font-bold text-slate-900">1. Area</p>
              <p className="text-xs text-slate-600 mt-1">Choose a Mumbai flood-prone area from the top menu.</p>
            </div>
            <div className="p-3 rounded-lg bg-cyan-50 border border-cyan-200">
              <CloudRain className="w-5 h-5 text-cyan-700 mb-2" />
              <p className="text-xs font-bold text-slate-900">2. Rain amount</p>
              <p className="text-xs text-slate-600 mt-1">Choose light, heavy, extreme, or cloudburst rain.</p>
            </div>
            <div className="p-3 rounded-lg bg-amber-50 border border-amber-200">
              <MousePointerClick className="w-5 h-5 text-amber-700 mb-2" />
              <p className="text-xs font-bold text-slate-900">3. Time in the storm</p>
              <p className="text-xs text-slate-600 mt-1">Press Run, then click the timeline to see the storm build and recede.</p>
            </div>
          </div>
        </div>

        <div>
          <h3 className="text-sm font-bold text-slate-900 mb-2">What appears on screen</h3>
          <div className="rounded-lg bg-slate-50 border border-slate-200 divide-y divide-slate-200 text-sm">
            <div className="p-3"><strong className="text-slate-900">Map:</strong> colours show likely water depth and hotspots. Click a hotspot to inspect it.</div>
            <div className="p-3"><strong className="text-slate-900">Right panel:</strong> shows the warning level, expected water depth, people/buildings that may be affected, and suggested actions.</div>
            <div className="p-3"><strong className="text-slate-900">Bottom timeline:</strong> moves from rain starting to runoff, peak flooding, and water going down.</div>
            <div className="p-3"><strong className="text-slate-900">Top summary:</strong> gives a quick count of serious hotspots and the current rain setting.</div>
          </div>
        </div>

        <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-950 leading-relaxed">
          <strong>In simple terms:</strong> the app combines rainfall, terrain, drains, roads, buildings, and past flood information. It estimates where water can collect, then turns that estimate into a map and clear response guidance.
        </div>

        <button onClick={onClose} className="w-full py-2.5 bg-slate-900 text-white text-sm font-bold rounded-lg hover:bg-slate-800 transition-colors">
          Got it
        </button>
      </div>
    </div>
  );
};
