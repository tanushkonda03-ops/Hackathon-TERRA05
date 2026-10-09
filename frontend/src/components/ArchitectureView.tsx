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
      color: 'text-sky-600',
      bgColor: 'bg-sky-50 border-sky-200',
      desc: '15-minute quantitative precipitation estimation (QPE) and ensemble rainfall scenarios (25–150 mm/hr).',
    },
    {
      title: '2. GEOSPATIAL VECTOR INGESTION',
      sub: 'BMC Cadastral & Infrastructure Spatial Layers',
      icon: Map,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50 border-blue-200',
      desc: 'High-res DEM, building footprints, soil permeabilities, road cross-sections, and SWD culvert topologies.',
    },
    {
      title: '3. SPATIAL FEATURE ENGINE',
      sub: 'Topographic Wetness & Hydrodynamic Indexing',
      icon: Cpu,
      color: 'text-indigo-600',
      bgColor: 'bg-indigo-50 border-indigo-200',
      desc: 'Generates flow accumulation paths, slope gradients, drain proximity distances, and imperviousness ratios.',
    },
    {
      title: '4. HYDROLOGICAL SIMULATION',
      sub: 'SWMM / 2D Overland Shallow Water Flow',
      icon: Waves,
      color: 'text-teal-600',
      bgColor: 'bg-teal-50 border-teal-200',
      desc: 'Simulates catchment routing, pipe surcharge backwater, tidal gate head pressures, and gravity flow limits.',
    },
    {
      title: '5. ML SURROGATE INFERENCE',
      sub: 'Graph Neural Network (GNN) / Spatiotemporal Engine',
      icon: BrainCircuit,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50 border-purple-200',
      desc: 'Accelerates real-time flood depth and inundation probability inference from hours to sub-second latency.',
    },
    {
      title: '6. UNCERTAINTY QUANTIFICATION',
      sub: 'Conformal Prediction & Bayesian Credible Intervals',
      icon: Scale,
      color: 'text-amber-600',
      bgColor: 'bg-amber-50 border-amber-200',
      desc: 'Computes statistically calibrated 90% prediction intervals around flood depths to guard against overconfidence.',
    },
    {
      title: '7. COMMAND & RISK ENGINE',
      sub: 'Municipal Disaster Decision Support',
      icon: ShieldAlert,
      color: 'text-rose-600',
      bgColor: 'bg-rose-50 border-rose-200',
      desc: 'Aggregates ward-level risk tiers, prioritizes pumping deployments, and dispatches automated response alerts.',
    },
    {
      title: '8. 3D DIGITAL TWIN & INTERACTION',
      sub: 'Three.js / WebGL Geospatial Spatial Mesh',
      icon: Box,
      color: 'text-emerald-600',
      bgColor: 'bg-emerald-50 border-emerald-200',
      desc: 'Renders GPU-accelerated volumetric water levels, building vulnerability tints, and drainage stress.',
    },
    {
      title: '9. AUTHORITY COMMAND DASHBOARD',
      sub: 'TERRA05 Authority Operations Console',
      icon: Monitor,
      color: 'text-cyan-700',
      bgColor: 'bg-cyan-50 border-cyan-200',
      desc: 'Actionable executive interface for BMC disaster management commissioners, ward officers, and traffic police.',
    },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 select-none bg-slate-50/50 min-h-full">
      <div className="border-b border-gis-border pb-4 bg-white p-5 rounded-xl shadow-gis-xs border">
        <div className="flex items-center space-x-2">
          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-50 text-purple-700 border border-purple-200 font-bold">
            SYSTEM ARCHITECTURE
          </span>
          <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">END-TO-END SPECIFICATION</span>
        </div>
        <h1 className="text-xl font-bold text-slate-900 mt-1 tracking-tight">
          TERRA05 Technical Architecture & Pipeline
        </h1>
        <p className="text-xs text-slate-500 mt-1">
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
              className="p-4 rounded-xl bg-white border border-gis-border hover:border-sky-300 transition-all shadow-gis-xs flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className={`p-2 rounded-lg border ${step.bgColor} ${step.color}`}>
                    <Icon className="w-4.5 h-4.5" />
                  </div>
                  <span className="text-[10px] font-mono text-slate-400 font-bold">
                    STEP 0{idx + 1}
                  </span>
                </div>
                <h3 className="text-xs font-bold text-slate-900 font-mono">{step.title}</h3>
                <div className="text-[10px] font-mono text-sky-800 font-medium mt-0.5">{step.sub}</div>
                <p className="text-xs text-slate-600 mt-2 leading-relaxed">{step.desc}</p>
              </div>

              {idx < pipelineSteps.length - 1 && (
                <div className="mt-4 pt-2.5 border-t border-slate-100 flex items-center justify-end text-[10px] font-mono text-slate-400 font-semibold">
                  <span>Downstream Stream &rarr;</span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Technology Specifications */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 rounded-xl bg-white border border-gis-border shadow-gis-xs space-y-2">
          <h4 className="text-xs font-bold text-sky-900 font-mono uppercase tracking-wider">
            CORE COMPUTATIONAL STACK
          </h4>
          <ul className="text-xs font-mono text-slate-600 space-y-1.5 list-disc list-inside">
            <li><span className="text-slate-400 font-semibold">Hydrology Simulator:</span> EPA SWMM / PySWMM Python bindings</li>
            <li><span className="text-slate-400 font-semibold">ML Framework:</span> PyTorch Geometric (GNN on urban mesh)</li>
            <li><span className="text-slate-400 font-semibold">Uncertainty Calibration:</span> Non-parametric MAPIE Conformal Inference</li>
            <li><span className="text-slate-400 font-semibold">GIS Processing:</span> GDAL, rasterio, GeoPandas, Shapely</li>
          </ul>
        </div>

        <div className="p-4 rounded-xl bg-white border border-gis-border shadow-gis-xs space-y-2">
          <h4 className="text-xs font-bold text-sky-900 font-mono uppercase tracking-wider">
            COMMAND CLIENT ARCHITECTURE
          </h4>
          <ul className="text-xs font-mono text-slate-600 space-y-1.5 list-disc list-inside">
            <li><span className="text-slate-400 font-semibold">Geospatial Rendering:</span> Three.js WebGL / Deck.gl Ready</li>
            <li><span className="text-slate-400 font-semibold">Frontend Foundation:</span> React 19 + TypeScript + Tailwind CSS</li>
            <li><span className="text-slate-400 font-semibold">Data Contract:</span> Strictly typed schemas for direct API coupling</li>
            <li><span className="text-slate-400 font-semibold">Target Users:</span> BMC Disaster Cell, Ward Emergency Officers</li>
          </ul>
        </div>
      </div>
    </div>
  );
};
