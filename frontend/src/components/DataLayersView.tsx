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
      statusColor: 'sky',
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
    <div className="flex-1 overflow-y-auto p-6 space-y-6 select-none bg-slate-50/50 min-h-full">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gis-border pb-4 bg-white p-5 rounded-xl shadow-gis-xs border">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-sky-50 text-sky-700 border border-sky-200 font-bold">
              DATA PIPELINE
            </span>
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">WHAT THE MAP USES</span>
          </div>
          <h1 className="text-xl font-bold text-slate-900 mt-1 tracking-tight">
            Information used by the map
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            These are the sources that help the app estimate where flood water may collect.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono text-slate-600 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200 shadow-gis-xs">
          <HardDrive className="w-4 h-4 text-sky-700" />
          <span className="font-bold">7 / 7 CATALOGS READY</span>
        </div>
      </div>

      {/* Data Source Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sources.map((item, idx) => (
          <div
            key={idx}
            className="p-4 rounded-xl bg-white border border-gis-border hover:border-sky-300 transition-colors shadow-gis-xs space-y-3"
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="text-xs font-bold text-slate-900">{item.name}</h3>
                <span className="text-[10px] font-mono text-slate-500">{item.provider}</span>
              </div>
              <span className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded shrink-0 border ${
                item.statusColor === 'emerald'
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-sky-50 text-sky-700 border-sky-200'
              }`}>
                {item.status}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-[10px] font-mono bg-slate-50 p-2.5 rounded-lg border border-slate-100">
              <div>
                <span className="text-slate-400 font-bold">FORMAT:</span>{' '}
                <span className="text-slate-700">{item.type}</span>
              </div>
              <div>
                <span className="text-slate-400 font-bold">GRANULARITY:</span>{' '}
                <span className="text-sky-800 font-semibold">{item.resolution}</span>
              </div>
              <div className="col-span-2 pt-1 border-t border-slate-200/60">
                <span className="text-slate-400 font-bold">BENCHMARK CYCLE:</span>{' '}
                <span className="text-slate-700">{item.lastUpdated}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Architecture Disclaimer */}
      <div className="p-4 rounded-xl bg-sky-50/70 border border-sky-200 text-xs text-slate-700 leading-relaxed shadow-gis-xs">
        <strong className="text-sky-900 font-bold uppercase block mb-1">Architecture Integration Note:</strong>
        This prototype renders spatial slices locally. In production, these layers connect directly to BMC’s enterprise GIS, WMS/WFS map servers, and live IMD Doppler radar webhooks via an asynchronous spatial indexing engine.
      </div>
    </div>
  );
};
