import React from 'react';
import { AlertTriangle, ShieldCheck, X } from 'lucide-react';

interface DisclaimerModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DisclaimerModal: React.FC<DisclaimerModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm select-none">
      <div className="w-full max-w-xl bg-command-900 border border-amber-500/50 rounded-xl shadow-2xl p-6 space-y-4">
        <div className="flex items-start justify-between border-b border-command-700/80 pb-3">
          <div className="flex items-center space-x-2.5 text-amber-400">
            <AlertTriangle className="w-6 h-6 shrink-0" />
            <div>
              <h3 className="font-tech text-base font-bold text-white tracking-wide">
                PROTOTYPE / DEMONSTRATION NOTICE
              </h3>
              <div className="text-[10px] font-mono text-amber-400/90">
                TERRA05 v0.1 • HACKATHON RESEARCH SPECIFICATION
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded hover:bg-command-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="text-xs text-slate-300 space-y-3 font-sans leading-relaxed">
          <p>
            The map uses the BMC drainage inventory (existing conduits only) and cleaned BMC flood-prone locations. The 100 m grid shows historical flood labels, not a forecast. IMD station rainfall is periodic and may be stale; it is shown for context and does not feed the simulation automatically.
          </p>
          <p>
            Risk values for the selected localities and the illustrative response layers are not authoritative. Drainage geometry, terrain, and model inputs still require source and engineering validation. Do not use this prototype for real-world flood warnings, emergency response, evacuation decisions, or municipal planning.
          </p>
          <p>
            Simulated inundation is displayed only when backend simulation output is available. The hydraulic model and its thresholds have not been validated for operational use.
          </p>
        </div>

        <div className="pt-2 border-t border-command-700/80 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded bg-amber-500 hover:bg-amber-400 text-command-950 font-tech font-bold text-xs uppercase transition-colors"
          >
            I Understand • Proceed to Command Center
          </button>
        </div>
      </div>
    </div>
  );
};
