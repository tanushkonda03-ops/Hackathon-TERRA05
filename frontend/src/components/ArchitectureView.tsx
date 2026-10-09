import React from 'react';
import { 
  CloudRain, 
  Map, 
  Cpu, 
  Waves, 
  BrainCircuit, 
  Scale, 
  ShieldAlert, 
  Box, 
  Monitor, 
  ArrowDown, 
  ArrowRight,
  Workflow
} from 'lucide-react';

export const ArchitectureView: React.FC = () => {
  const pipelineSteps = [
    {
      title: '1. PRECIPITATION & NOWCAST',
      sub: 'IMD Doppler Radar & Numerical Weather Prediction',
      icon: CloudRain,
      color: 'text-cyan-400',
      desc: '15-minute quantitative precipitation estimation (QPE) and ensemble rainfall scenarios (25–150 mm/hr).',
    },
    {
      title: '2. GEOSPATIAL VECTOR INGESTION',
      sub: 'BMC Cadastral & Infrastructure Spatial Layers',
      icon: Map,
      color: 'text-blue-400',
      desc: 'High-res DEM, building footprints, soil permeabilities, road cross-sections, and SWD culvert topologies.',
    },
    {
      title: '3. SPATIAL FEATURE ENGINE',
      sub: 'Topographic Wetness & Hydrodynamic Indexing',
      icon: Cpu,
      color: 'text-indigo-400',
      desc: 'Generates flow accumulation paths, slope gradients, drain proximity distances, and imperviousness ratios.',
    },
    {
      title: '4. HYDROLOGICAL SIMULATION',
      sub: 'SWMM / 2D Overland Shallow Water Flow',
      icon: Waves,
      color: 'text-teal-400',
      desc: 'Simulates catchment routing, pipe surcharge backwater, tidal gate head pressures, and gravity flow limits.',
    },
    {
      title: '5. ML SURROGATE INFERENCE',
      sub: 'Graph Neural Network (GNN) / Spatiotemporal Engine',
      icon: BrainCircuit,
      color: 'text-purple-400',
      desc: 'Accelerates real-time flood depth and inundation probability inference from hours to sub-second latency.',
    },
    {
      title: '6. UNCERTAINTY QUANTIFICATION',
      sub: 'Conformal Prediction & Bayesian Credible Intervals',
      icon: Scale,
      color: 'text-amber-400',
      desc: 'Computes statistically calibrated 90% prediction intervals around flood depths to guard against overconfidence.',
    },
    {
      title: '7. COMMAND & RISK ENGINE',
      sub: 'Municipal Disaster Decision Support',
      icon: ShieldAlert,
      color: 'text-rose-400',
      desc: 'Aggregates ward-level risk tiers, prioritizes pumping deployments, and dispatches automated response alerts.',
    },
    {
      title: '8. 3D DIGITAL TWIN & INTERACTION',
      sub: 'Three.js / WebGL Geospatial Spatial Mesh',
      icon: Box,
      color: 'text-emerald-400',
      desc: 'Renders GPU-accelerated volumetric water levels, building vulnerability tints, and drainage stress.',
    },
    {
      title: '9. AUTHORITY COMMAND DASHBOARD',
      sub: 'TERRA05 Authority Operations Console',
      icon: Monitor,
      color: 'text-cyan-300',
      desc: 'Actionable executive interface for BMC disaster management commissioners, ward officers, and traffic police.',
    },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 select-none">
      <div className="border-b border-command-700/80 pb-4">
        <div className="flex items-center space-x-2">
          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-950 text-purple-400 border border-purple-500/30 font-bold">
            SYSTEM ARCHITECTURE
          </span>
          <span className="text-xs font-mono text-slate-400">END-TO-END SPECIFICATION</span>
        </div>
        <h1 className="text-xl font-tech font-bold text-white mt-1">
          TERRA05 Technical Architecture & Pipeline
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Modular flow from raw radar ingestion through physics-informed ML surrogates to real-time 3D authority decision support.
        </p>
      </div>

      {/* Visual Pipeline Flow */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {pipelineSteps.map((step, idx) => {
          const Icon = step.icon;
          return (
            <div
              key={idx}
              className="p-4 rounded-lg bg-command-900 border border-command-700 hover:border-cyan-500/50 transition-all shadow-hud flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className={`p-2 rounded bg-command-800 ${step.color}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] font-mono text-slate-500 font-bold">
                    STEP 0{idx + 1}
                  </span>
                </div>
                <h3 className="text-xs font-tech font-bold text-slate-100">{step.title}</h3>
                <div className="text-[10px] font-mono text-cyan-400 mt-0.5">{step.sub}</div>
                <p className="text-xs text-slate-400 mt-2 leading-relaxed">{step.desc}</p>
              </div>

              {idx < pipelineSteps.length - 1 && (
                <div className="mt-4 pt-3 border-t border-command-800 flex items-center justify-end text-[10px] font-mono text-slate-500">
                  <span>Downstream Stream &rarr;</span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Technology Specifications */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 rounded-lg bg-command-900 border border-command-700 space-y-2">
          <h4 className="text-xs font-tech font-bold text-cyan-300">CORE COMPUTATIONAL STACK</h4>
          <ul className="text-xs font-mono text-slate-300 space-y-1.5 list-disc list-inside">
            <li><span className="text-slate-400">Hydrology Simulator:</span> EPA SWMM / PySWMM Python bindings</li>
            <li><span className="text-slate-400">ML Framework:</span> PyTorch Geometric (GNN on urban mesh)</li>
            <li><span className="text-slate-400">Uncertainty Calibration:</span> Non-parametric MAPIE Conformal Inference</li>
            <li><span className="text-slate-400">GIS Processing:</span> GDAL, rasterio, GeoPandas, Shapely</li>
          </ul>
        </div>

        <div className="p-4 rounded-lg bg-command-900 border border-command-700 space-y-2">
          <h4 className="text-xs font-tech font-bold text-cyan-300">COMMAND CLIENT ARCHITECTURE</h4>
          <ul className="text-xs font-mono text-slate-300 space-y-1.5 list-disc list-inside">
            <li><span className="text-slate-400">Geospatial Rendering:</span> Three.js WebGL / Deck.gl Ready</li>
            <li><span className="text-slate-400">Frontend Foundation:</span> React 19 + TypeScript + Tailwind CSS</li>
            <li><span className="text-slate-400">Data Contract:</span> Strictly typed schemas for direct API coupling</li>
            <li><span className="text-slate-400">Target Users:</span> BMC Disaster Cell, Ward Emergency Officers</li>
          </ul>
        </div>
      </div>
    </div>
  );
};
