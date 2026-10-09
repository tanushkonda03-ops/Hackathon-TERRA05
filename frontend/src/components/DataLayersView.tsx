import React from 'react';
import { Database, CheckCircle, Clock, Server, HardDrive, RefreshCw, Layers } from 'lucide-react';

export const DataLayersView: React.FC = () => {
  const sources = [
    {
      name: 'BMC Stormwater Drainage Network',
      type: 'Vector / GeoJSON',
      status: 'AVAILABLE (PROTOTYPE SLICE)',
      statusColor: 'emerald',
      resolution: 'Culvert & Trunk Line',
      lastUpdated: 'Monsoon Readiness 2024',
      provider: 'Brihanmumbai Municipal Corporation (SWD Dept)',
    },
    {
      name: 'BMC Identified Chronic Flooding Spots',
      type: 'Spatial Point Callout',
      status: 'AVAILABLE (PROTOTYPE SLICE)',
      statusColor: 'emerald',
      resolution: 'Exact coordinates',
      lastUpdated: 'Pre-monsoon Audit',
      provider: 'BMC Disaster Management Dept',
    },
    {
      name: 'High-Resolution 3D Building Footprints',
      type: '3D Polygonal Mesh',
      status: 'AVAILABLE (PROTOTYPE SLICE)',
      statusColor: 'emerald',
      resolution: 'LOD1 Extrusion',
      lastUpdated: 'Q3 2024',
      provider: 'OpenStreetMap / BMC Cadastral Survey',
    },
    {
      name: 'Digital Elevation Model (DEM / Terrain)',
      type: 'Raster DEM Grid',
      status: 'AVAILABLE (SYNTHETIC / 5M DEM)',
      statusColor: 'emerald',
      resolution: '5m Cell Size',
      lastUpdated: 'Cartosat-1 / SRTM Derived',
      provider: 'National Remote Sensing Centre (NRSC)',
    },
    {
      name: 'Land-Use & Impervious Surface Mapping',
      type: 'Classified Multispectral',
      status: 'AVAILABLE (PROTOTYPE SLICE)',
      statusColor: 'emerald',
      resolution: '10m Surface Imperviousness',
      lastUpdated: 'Sentinel-2 Land Cover 2024',
      provider: 'Copernicus Land Monitoring Service',
    },
    {
      name: 'Rainfall Observations & Radar Telemetry',
      type: 'Time Series Scenario Grid',
      status: 'SYNTHETIC SCENARIO INGESTION',
      statusColor: 'cyan',
      resolution: '15-min Intervals',
      lastUpdated: 'Real-time Scenario Engine',
      provider: 'IMD Mumbai Colaba / Santacruz Radar Interface',
    },
    {
      name: 'Historical Flood Telemetry (26 July 2005)',
      type: 'Event Benchmark Record',
      status: 'AVAILABLE (BENCHMARK ARCHIVE)',
      statusColor: 'emerald',
      resolution: 'Basin Gauge Stations',
      lastUpdated: 'Fact-finding Committee Report',
      provider: 'Government of Maharashtra / Chitale Committee',
    },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 select-none">
      <div className="flex items-center justify-between border-b border-command-700/80 pb-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950 text-cyan-400 border border-cyan-500/30 font-bold">
              DATA PIPELINE
            </span>
            <span className="text-xs font-mono text-slate-400">WHAT THE MAP USES</span>
          </div>
          <h1 className="text-xl font-tech font-bold text-white mt-1">
            Information used by the map
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            These are the sources that help the app estimate where flood water may collect.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono text-slate-400 bg-command-850 px-3 py-1.5 rounded-lg border border-command-700">
          <HardDrive className="w-4 h-4 text-cyan-400" />
          <span>7 / 7 CATALOGS READY</span>
        </div>
      </div>

      {/* Data Source Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sources.map((item, idx) => (
          <div
            key={idx}
            className="p-4 rounded-lg bg-command-900 border border-command-700 hover:border-cyan-500/40 transition-colors shadow-hud space-y-2.5"
          >
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-xs font-tech font-bold text-slate-100">{item.name}</h3>
                <span className="text-[10px] font-mono text-slate-400">{item.provider}</span>
              </div>
              <span className="text-[9px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-500/30">
                {item.status}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-[10px] font-mono bg-command-950/60 p-2 rounded">
              <div>
                <span className="text-slate-500">FORMAT:</span>{' '}
                <span className="text-slate-300">{item.type}</span>
              </div>
              <div>
                <span className="text-slate-500">GRANULARITY:</span>{' '}
                <span className="text-cyan-300">{item.resolution}</span>
              </div>
              <div className="col-span-2">
                <span className="text-slate-500">BENCHMARK CYCLE:</span>{' '}
                <span className="text-slate-300">{item.lastUpdated}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Architecture Disclaimer */}
      <div className="p-4 rounded-lg bg-command-850 border border-command-700 text-xs text-slate-400 leading-relaxed font-sans">
        <strong className="text-cyan-400 font-tech uppercase block mb-1">Architecture Integration Note:</strong>
        This prototype renders spatial slices locally. In production, these layers connect directly to BMC’s enterprise GIS, WMS/WFS map servers, and live IMD Doppler radar webhooks via an asynchronous spatial indexing engine.
      </div>
    </div>
  );
};
