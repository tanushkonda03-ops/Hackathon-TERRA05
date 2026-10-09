import React, { useEffect, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import { Map as MapLibreMap, NavigationControl, ScaleControl, GeoJSONSource } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import { MumbaiLocation, MUMBAI_GEO_LOCATIONS, TimelineImpactMetrics, createLocationFromGridFeature } from '../data/locations';
import { 
  MITHI_RIVER_GEOJSON, 
  BMC_DRAINAGE_GEOJSON, 
  RUNOFF_FLOW_PATHS_GEOJSON,
  MUMBAI_MAJOR_ROADS_GEOJSON,
  CRITICAL_INFRASTRUCTURE_GEOJSON,
  BMC_FLOOD_SPOTS_GEOJSON, 
  HISTORICAL_2019_GEOJSON, 
  getRealisticFloodPolygonsGeoJSON 
} from '../data/mumbaiGeojson';
import { getRiskMap, transformRiskMapToGeoJSON4326, SimulationResponse, simulationDataToGeoJSON } from '../services/api';
import { ChevronDown } from 'lucide-react';

// Configure MapLibre Web Worker for Vite
maplibregl.setWorkerUrl(workerUrl);

interface MapboxMumbaiProps {
  rainfall: number;
  timelineStep: number; // 0 to 6 (T00 to T06) or sim timestep
  timelineMetrics: TimelineImpactMetrics;
  selectedLocation: MumbaiLocation | null;
  onSelectLocation: (loc: MumbaiLocation) => void;
  layers: {
    floodSpots: boolean;
    drainage: boolean;
    runoffFlow: boolean;
    roadsExposure: boolean;
    criticalInfra: boolean;
    floodDepth: boolean;
    uncertainty: boolean;
    historical2019: boolean;
    terrain3D: boolean;
    riskGrid: boolean;
  };
  cameraPreset: '3D' | 'TOP' | 'RESET';
  simulationData?: SimulationResponse | null;
  simStepIndex?: number;
  onStatusChange?: (status: 'CONNECTING' | 'ONLINE' | 'ERROR') => void;
  onDiagnosticsUpdate?: (diag: Record<string, any>) => void;
}

export const MapboxMumbai: React.FC<MapboxMumbaiProps> = ({
  rainfall,
  timelineStep,
  timelineMetrics,
  selectedLocation,
  onSelectLocation,
  layers,
  cameraPreset,
  simulationData,
  simStepIndex,
  onStatusChange,
  onDiagnosticsUpdate,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const rainCanvasRef = useRef<HTMLCanvasElement>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [isLocationDropdownOpen, setIsLocationDropdownOpen] = useState(false);
  const [hoveredFeature, setHoveredFeature] = useState<{
    x: number;
    y: number;
    name: string;
    depth?: number;
    elevation?: number;
    maxDepth?: number;
    builtUp?: number;
    isSimCell?: boolean;
  } | null>(null);

  // 1. Initialize MapLibre GL Instance (Strictly SINGLE instance lifecycle, zero token required)
  useEffect(() => {
    if (!mapContainerRef.current) return;

    onStatusChange?.('CONNECTING');

    // OpenFreeMap Liberty: High-contrast, token-free, high-performance vector basemap
    const openFreeMapLibertyStyle = 'https://tiles.openfreemap.org/styles/liberty';

    console.info('[TERRA05][MAP INIT] Initializing MapLibre GL with OpenFreeMap Liberty style');

    const map = new MapLibreMap({
      container: mapContainerRef.current,
      style: openFreeMapLibertyStyle,
      center: [72.875, 19.068], // Mithi River Basin / Kurla-BKC corridor
      zoom: 14.2,
      pitch: 25, // Professional GIS perspective (clean 2D presentation with subtle relief, not extreme pitch)
      bearing: 0,
      maxPitch: 60,
      minZoom: 11,
      maxZoom: 18.5,
    });

    // Helper: Mount all TERRA05 GIS intelligence layers safely and idempotently
    const setupLayers = () => {
      try {
        console.info('[TERRA05][MAP LAYERS] Registering TERRA05 GIS layers. Style loaded:', map.isStyleLoaded());

        // --- LAYER 1: 3D EXTRUDED BUILDINGS ---
        try {
          // OpenFreeMap Liberty includes native building-3d or openmaptiles building source-layer
          if (map.getSource('openmaptiles') && !map.getLayer('3d-buildings-extrusion')) {
            map.addLayer({
              id: '3d-buildings-extrusion',
              source: 'openmaptiles',
              'source-layer': 'building',
              type: 'fill-extrusion',
              minzoom: 13.5,
              paint: {
                'fill-extrusion-color': '#CBD5E1', // Architectural light grey
                'fill-extrusion-height': [
                  'interpolate',
                  ['linear'],
                  ['zoom'],
                  13.5,
                  0,
                  15.5,
                  ['coalesce', ['get', 'render_height'], ['get', 'height'], 12],
                ],
                'fill-extrusion-base': [
                  'interpolate',
                  ['linear'],
                  ['zoom'],
                  13.5,
                  0,
                  15.5,
                  ['coalesce', ['get', 'render_min_height'], ['get', 'min_height'], 0],
                ],
                'fill-extrusion-opacity': 0.75,
              },
            });
          }
        } catch (bldErr) {
          console.warn('[TERRA05][3D BUILDING NOTE]', bldErr);
        }

        // --- LAYER 2: MITHI RIVER NATURAL CHANNEL (Primary Landmark) ---
        if (!map.getSource('mithi-river-src')) {
          map.addSource('mithi-river-src', {
            type: 'geojson',
            data: MITHI_RIVER_GEOJSON,
          });

          map.addLayer({
            id: 'mithi-river-casing',
            type: 'line',
            source: 'mithi-river-src',
            layout: { 'line-join': 'round', 'line-cap': 'round' },
            paint: {
              'line-color': '#0369A1',
              'line-width': ['interpolate', ['linear'], ['zoom'], 12, 7, 16, 17],
              'line-opacity': 0.9,
            },
          });

          map.addLayer({
            id: 'mithi-river-core',
            type: 'line',
            source: 'mithi-river-src',
            layout: { 'line-join': 'round', 'line-cap': 'round' },
            paint: {
              'line-color': '#38BDF8',
              'line-width': ['interpolate', ['linear'], ['zoom'], 12, 4, 16, 12],
              'line-opacity': 1.0,
            },
          });
        }

        // --- LAYER 3: BMC STORMWATER DRAINAGE NETWORK ---
        if (!map.getSource('bmc-drainage-src')) {
          map.addSource('bmc-drainage-src', {
            type: 'geojson',
            data: BMC_DRAINAGE_GEOJSON,
          });

          map.addLayer({
            id: 'bmc-drainage-layer',
            type: 'line',
            source: 'bmc-drainage-src',
            layout: {
              'line-join': 'round',
              'line-cap': 'round',
              visibility: layers.drainage ? 'visible' : 'none',
            },
            paint: {
              'line-color': '#0891B2',
              'line-width': ['interpolate', ['linear'], ['zoom'], 12, 2.5, 16, 5],
              'line-dasharray': [2, 1],
            },
          });
        }

        // --- LAYER 4: SURFACE RUNOFF FLOW PATHS ---
        if (!map.getSource('runoff-flow-src')) {
          map.addSource('runoff-flow-src', {
            type: 'geojson',
            data: RUNOFF_FLOW_PATHS_GEOJSON,
          });

          map.addLayer({
            id: 'runoff-flow-layer',
            type: 'line',
            source: 'runoff-flow-src',
            layout: {
              'line-join': 'round',
              'line-cap': 'round',
              visibility: layers.runoffFlow ? 'visible' : 'none',
            },
            paint: {
              'line-color': '#0284C7',
              'line-width': 2.0,
              'line-dasharray': [4, 2],
              'line-opacity': 0.85,
            },
          });
        }

        // --- LAYER 5: MAJOR ROAD ARTERIALS ---
        if (!map.getSource('mumbai-roads-src')) {
          map.addSource('mumbai-roads-src', {
            type: 'geojson',
            data: MUMBAI_MAJOR_ROADS_GEOJSON,
          });

          map.addLayer({
            id: 'mumbai-roads-layer',
            type: 'line',
            source: 'mumbai-roads-src',
            layout: {
              'line-join': 'round',
              'line-cap': 'round',
              visibility: layers.roadsExposure ? 'visible' : 'none',
            },
            paint: {
              'line-color': '#64748B',
              'line-width': ['interpolate', ['linear'], ['zoom'], 12, 3.5, 16, 7],
              'line-opacity': 0.85,
            },
          });
        }

        // --- LAYER 6: CRITICAL INFRASTRUCTURE (Hospitals, Transit, Shelters) ---
        if (!map.getSource('critical-infra-src')) {
          map.addSource('critical-infra-src', {
            type: 'geojson',
            data: CRITICAL_INFRASTRUCTURE_GEOJSON,
          });

          map.addLayer({
            id: 'critical-infra-layer',
            type: 'circle',
            source: 'critical-infra-src',
            layout: {
              visibility: layers.criticalInfra ? 'visible' : 'none',
            },
            paint: {
              'circle-radius': 6.0,
              'circle-color': [
                'match',
                ['get', 'category'],
                'HOSPITAL', '#DC2626',
                'TRANSIT_HUB', '#2563EB',
                'FIRE_STATION', '#D97706',
                'SHELTER', '#059669',
                '#64748B'
              ],
              'circle-stroke-width': 2,
              'circle-stroke-color': '#FFFFFF',
            },
          });
        }

        // --- LAYER 7: REALISTIC FLOOD WATER SURFACE (Smooth Geographic Basin Inundation) ---
        if (!map.getSource('terra05-flood-src')) {
          map.addSource('terra05-flood-src', {
            type: 'geojson',
            data: getRealisticFloodPolygonsGeoJSON(rainfall, timelineStep, layers.uncertainty),
          });

          // Depth-sensitive semi-transparent water
          map.addLayer({
            id: 'terra05-flood-layer',
            type: 'fill',
            source: 'terra05-flood-src',
            filter: ['==', ['get', 'layerType'], 'CORE_WATER'],
            paint: {
              'fill-color': [
                'interpolate',
                ['linear'],
                ['get', 'depth'],
                0.0,  '#BAE6FD',
                0.15, '#38BDF8',
                0.30, '#0284C7',
                0.60, '#0369A1',
                1.0,  '#0C4A6E'
              ],
              'fill-opacity': [
                'interpolate',
                ['linear'],
                ['get', 'depth'],
                0.0,  0.35,
                0.30, 0.55,
                1.0,  0.75
              ],
              'fill-outline-color': '#0284C7',
            },
          });

          // Water edge contour
          map.addLayer({
            id: 'terra05-water-edge-layer',
            type: 'line',
            source: 'terra05-flood-src',
            filter: ['==', ['get', 'layerType'], 'CORE_WATER'],
            paint: {
              'line-color': '#0284C7',
              'line-width': 1.5,
              'line-opacity': 0.8,
            },
          });

          // 90% Uncertainty Envelope
          map.addLayer({
            id: 'terra05-uncertainty-layer',
            type: 'line',
            source: 'terra05-flood-src',
            filter: ['==', ['get', 'layerType'], 'UNCERTAINTY_BOUND'],
            layout: {
              visibility: layers.uncertainty ? 'visible' : 'none',
            },
            paint: {
              'line-color': '#6366F1',
              'line-width': 2.0,
              'line-dasharray': [4, 3],
              'line-opacity': 0.70,
            },
          });
        }

        // --- LAYER 7B: 2D COMPUTATIONAL RUNOFF & WATER ACCUMULATION GRID (Dynamic Hydro Prototype) ---
        if (!map.getSource('terra05-sim-water-src')) {
          map.addSource('terra05-sim-water-src', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] },
          });

          map.addLayer({
            id: 'terra05-sim-water-layer',
            type: 'fill',
            source: 'terra05-sim-water-src',
            layout: {
              visibility: layers.floodDepth ? 'visible' : 'none',
            },
            paint: {
              'fill-color': [
                'interpolate',
                ['linear'],
                ['get', 'depth'],
                0.005, 'rgba(186, 230, 253, 0.40)', // Shallow ponding onset
                0.05,  'rgba(56, 189, 248, 0.60)',  // Moderate ponding
                0.15,  'rgba(2, 132, 199, 0.75)',   // Significant stormwater accumulation
                0.30,  'rgba(3, 105, 161, 0.85)',   // Deep inundation
                0.60,  'rgba(12, 74, 110, 0.90)',   // Severe street submersion
                1.00,  'rgba(8, 47, 73, 0.95)'      // Major corridor flooding
              ],
              'fill-opacity': [
                'interpolate',
                ['linear'],
                ['get', 'depth'],
                0.005, 0.45,
                0.10,  0.70,
                0.50,  0.88,
                1.00,  0.95
              ],
              'fill-outline-color': '#0284C7',
            },
          });

          map.addLayer({
            id: 'terra05-sim-water-edge-layer',
            type: 'line',
            source: 'terra05-sim-water-src',
            layout: {
              visibility: layers.floodDepth ? 'visible' : 'none',
            },
            paint: {
              'line-color': '#0369A1',
              'line-width': 1.0,
              'line-opacity': 0.65,
            },
          });
        }

        // --- LAYER 8: BMC CHRONIC FLOOD SPOTS ---
        if (!map.getSource('bmc-spots-src')) {
          map.addSource('bmc-spots-src', {
            type: 'geojson',
            data: BMC_FLOOD_SPOTS_GEOJSON,
          });

          map.addLayer({
            id: 'bmc-spots-layer',
            type: 'circle',
            source: 'bmc-spots-src',
            layout: { visibility: layers.floodSpots ? 'visible' : 'none' },
            paint: {
              'circle-radius': 5.5,
              'circle-color': '#B91C1C',
              'circle-stroke-width': 2,
              'circle-stroke-color': '#FFFFFF',
              'circle-opacity': 0.9,
            },
          });
        }

        // --- LAYER 9: HISTORICAL JULY 2019 BENCHMARK REPLAY ---
        if (!map.getSource('historical-2019-src')) {
          map.addSource('historical-2019-src', {
            type: 'geojson',
            data: HISTORICAL_2019_GEOJSON,
          });

          map.addLayer({
            id: 'historical-2019-layer',
            type: 'fill',
            source: 'historical-2019-src',
            layout: { visibility: layers.historical2019 ? 'visible' : 'none' },
            paint: {
              'fill-color': '#10B981',
              'fill-opacity': 0.25,
              'fill-outline-color': '#059669',
            },
          });
        }

        // --- LAYER 10: 100M ML RISK GRID (FastAPI Backend Grid) ---
        if (!map.getSource('terra05-risk-grid-src')) {
          map.addSource('terra05-risk-grid-src', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] },
          });

          map.addLayer({
            id: 'terra05-risk-grid-fill',
            type: 'fill',
            source: 'terra05-risk-grid-src',
            layout: { visibility: layers.riskGrid ? 'visible' : 'none' },
            paint: {
              'fill-color': [
                'interpolate',
                ['linear'],
                ['coalesce', ['get', 'flood_fraction'], 0],
                0.0, '#E2E8F0',
                0.1, '#BAE6FD',
                0.3, '#7DD3FC',
                0.6, '#38BDF8',
                1.0, '#0284C7'
              ],
              'fill-opacity': 0.16,
            },
          });

          map.addLayer({
            id: 'terra05-risk-grid-line',
            type: 'line',
            source: 'terra05-risk-grid-src',
            layout: { visibility: layers.riskGrid ? 'visible' : 'none' },
            paint: {
              'line-color': '#94A3B8',
              'line-width': 0.75,
              'line-opacity': 0.35,
            },
          });
        }

        // Hover Raycasting
        map.on('mousemove', 'terra05-flood-layer', (e) => {
          if (e.features && e.features[0]) {
            const props = e.features[0].properties;
            setHoveredFeature({
              x: e.point.x,
              y: e.point.y,
              name: props?.name || 'Inundation Basin',
              depth: props?.depth,
              elevation: props?.elevationM,
            });
          }
        });

        map.on('mouseleave', 'terra05-flood-layer', () => {
          setHoveredFeature(null);
        });

        // 2D Computational Simulation Water Cell hover and click handlers
        map.on('mousemove', 'terra05-sim-water-layer', (e) => {
          if (e.features && e.features[0]) {
            const props = e.features[0].properties;
            map.getCanvas().style.cursor = 'pointer';
            setHoveredFeature({
              x: e.point.x,
              y: e.point.y,
              name: `Computational Grid #${props?.grid_id} (Ward ${props?.ward || 'L'})`,
              depth: typeof props?.depth === 'number' ? Number(props.depth) : undefined,
              elevation: typeof props?.elevation_m === 'number' ? Number(props.elevation_m) : undefined,
              maxDepth: typeof props?.max_depth === 'number' ? Number(props.max_depth) : undefined,
              builtUp: typeof props?.built_up_fraction === 'number' ? Math.round(Number(props.built_up_fraction) * 100) : undefined,
              isSimCell: true,
            });
          }
        });

        map.on('mouseleave', 'terra05-sim-water-layer', () => {
          map.getCanvas().style.cursor = '';
          setHoveredFeature(null);
        });

        map.on('click', 'terra05-sim-water-layer', (e) => {
          if (e.features && e.features[0]) {
            const feat = e.features[0];
            const props = feat.properties;
            const newLoc = createLocationFromGridFeature(props, e.lngLat.lng, e.lngLat.lat);
            onSelectLocation(newLoc);
          }
        });

        // 100m Risk Grid hover and click handlers
        map.on('mousemove', 'terra05-risk-grid-fill', (e) => {
          if (e.features && e.features[0]) {
            const props = e.features[0].properties;
            map.getCanvas().style.cursor = 'pointer';
            setHoveredFeature({
              x: e.point.x,
              y: e.point.y,
              name: `Grid Cell #${props?.grid_id} (${props?.ward ? `Ward ${props.ward}` : 'Corridor'})`,
              depth: typeof props?.flood_fraction === 'number' ? Number((props.flood_fraction * 0.5).toFixed(2)) : undefined,
              elevation: typeof props?.elevation_mean === 'number' ? Math.round(props.elevation_mean * 10) / 10 : undefined,
            });
          }
        });

        map.on('mouseleave', 'terra05-risk-grid-fill', () => {
          map.getCanvas().style.cursor = '';
          setHoveredFeature(null);
        });

        map.on('click', 'terra05-risk-grid-fill', (e) => {
          if (e.features && e.features[0]) {
            const feat = e.features[0];
            const props = feat.properties;
            const newLoc = createLocationFromGridFeature(props, e.lngLat.lng, e.lngLat.lat);
            onSelectLocation(newLoc);
          }
        });

        console.info('[TERRA05][MAP LAYERS] Setup completed successfully.');
      } catch (err) {
        console.error('[TERRA05][SETUP LAYERS ERROR]', err);
      }
    };

    // Diagnostics & Lifecycle listeners
    map.on('load', () => {
      console.info('[TERRA05][MAP] LOAD EVENT FIRED');
      setMapLoaded(true);
      onStatusChange?.('ONLINE');
      onDiagnosticsUpdate?.((prev: any) => ({
        ...prev,
        mapLoaded: true,
        styleLoaded: true,
      }));
      setupLayers();

      // Load 100m risk grid from backend around Mithi catchment corridor
      getRiskMap({ minx: 273000, miny: 2106000, maxx: 281000, maxy: 2114000, limit: 350 })
        .then((data) => {
          if (!mapRef.current) return;
          const geojson = transformRiskMapToGeoJSON4326(data);
          const src = mapRef.current.getSource('terra05-risk-grid-src') as GeoJSONSource;
          if (src) {
            src.setData(geojson);
            console.info(`[TERRA05] 100m Risk Grid loaded: ${geojson.features.length} cells`);
          }
        })
        .catch((err) => {
          console.warn('[TERRA05] Risk grid load notice:', err.message);
        });
    });

    map.on('style.load', () => {
      console.info('[TERRA05][MAP] STYLE.LOAD EVENT FIRED');
    });

    map.on('error', (event) => {
      console.warn('[TERRA05][MAP EVENT ERROR]', event);
    });

    // WebGL Context Loss & Recovery Monitoring
    const canvas = map.getCanvas();
    if (canvas) {
      canvas.addEventListener('webglcontextlost', (e) => {
        console.error('[TERRA05][WEBGL] CONTEXT LOST!', e);
        e.preventDefault();
      });
      canvas.addEventListener('webglcontextrestored', () => {
        console.warn('[TERRA05][WEBGL] CONTEXT RESTORED');
      });
    }

    map.addControl(new NavigationControl({ visualizePitch: true }), 'bottom-right');
    map.addControl(new ScaleControl({ unit: 'metric' }), 'bottom-left');

    const resizeObserver = new ResizeObserver(() => {
      if (mapRef.current) {
        requestAnimationFrame(() => mapRef.current?.resize());
      }
    });
    resizeObserver.observe(mapContainerRef.current);

    mapRef.current = map;

    return () => {
      console.info('[TERRA05][MAP CLEANUP] Unmounting component, safely cleaning up map');
      resizeObserver.disconnect();
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []); // Explicit empty dependency array: MapLibre initialized exactly ONCE

  // 2. Realistic Canvas-based Rainfall Particle System
  useEffect(() => {
    if (!rainCanvasRef.current) return;
    const canvas = rainCanvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    const w = (canvas.width = canvas.offsetWidth);
    const h = (canvas.height = canvas.offsetHeight);

    // Subtle rainfall particles scaled to intensity
    const dropsCount = Math.round((rainfall / 25) * 35);
    const drops: { x: number; y: number; speed: number; len: number }[] = [];

    for (let i = 0; i < dropsCount; i++) {
      drops.push({
        x: Math.random() * w,
        y: Math.random() * h,
        speed: 12 + Math.random() * 8,
        len: 7 + Math.random() * 6,
      });
    }

    const renderRain = () => {
      ctx.clearRect(0, 0, w, h);
      ctx.strokeStyle = rainfall >= 100 ? 'rgba(56, 189, 248, 0.35)' : 'rgba(147, 197, 253, 0.22)';
      ctx.lineWidth = 1.0;

      for (let i = 0; i < drops.length; i++) {
        const d = drops[i];
        ctx.beginPath();
        ctx.moveTo(d.x, d.y);
        ctx.lineTo(d.x - 1.5, d.y + d.len);
        ctx.stroke();

        d.y += d.speed;
        d.x -= 1.2;

        if (d.y > h) {
          d.y = -8;
          d.x = Math.random() * w;
        }
      }

      animId = requestAnimationFrame(renderRain);
    };

    // Rain active during rising event; stops at recession (T06)
    if (timelineStep < 6 && rainfall > 0) {
      renderRain();
    } else {
      ctx.clearRect(0, 0, w, h);
    }

    return () => {
      cancelAnimationFrame(animId);
    };
  }, [rainfall, timelineStep]);

  // 3. Update Dynamic Flood Layer GeoJSON and Network Stress Colors (STABLE: Zero style resets)
  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return;
    const map = mapRef.current;

    try {
      // A. Update Water Inundation Polygon Geometry via persistent source setData
      const floodSource = map.getSource('terra05-flood-src') as GeoJSONSource;
      if (floodSource) {
        const updatedGeoJSON = getRealisticFloodPolygonsGeoJSON(rainfall, timelineStep, layers.uncertainty);
        floodSource.setData(updatedGeoJSON);
      }

      // B. Dynamically Update Stormwater Drain Stress Color (Thin Line -> Amber -> Red)
      if (map.getLayer('bmc-drainage-layer')) {
        let drainColor = '#0891B2'; // Optimal (Blue-cyan)
        if (timelineMetrics.drainStressState === 'HIGH LOAD') drainColor = '#D97706'; // Stressed (Amber)
        else if (timelineMetrics.drainStressState === 'OVERLOADED') drainColor = '#EA580C'; // Overloaded (Orange-Red)
        else if (timelineMetrics.drainStressState === 'SURCHARGING OVERFLOW') drainColor = '#DC2626'; // Overflow (Red)

        map.setPaintProperty('bmc-drainage-layer', 'line-color', drainColor);
        map.setPaintProperty('bmc-drainage-layer', 'line-width', timelineStep >= 3 ? 4.0 : 2.5);
      }

      // C. Dynamically Update Road Inundation Colors
      if (map.getLayer('mumbai-roads-layer')) {
        let roadColor = '#64748B'; // Normal
        if (timelineStep === 2) roadColor = '#D97706'; // At Risk (Subtle Amber)
        else if (timelineStep === 3) roadColor = '#EA580C'; // Partially Flooded (Orange)
        else if (timelineStep >= 4) roadColor = '#DC2626'; // Impassable / Submerged (Red)

        map.setPaintProperty('mumbai-roads-layer', 'line-color', roadColor);
      }
    } catch (updateErr) {
      console.error('[TERRA05][SIMULATION UPDATE ERROR]', updateErr);
    }
  }, [rainfall, timelineStep, layers.uncertainty, timelineMetrics, mapLoaded]);

  // 3B. Update 2D Computational Hydrodynamic Simulation Water Layer GeoJSON
  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return;
    const map = mapRef.current;

    try {
      const simSrc = map.getSource('terra05-sim-water-src') as GeoJSONSource;
      if (!simSrc) return;

      if (simulationData && simulationData.cells && simulationData.cells.length > 0) {
        const step = Math.min(
          Math.max(0, simStepIndex ?? timelineStep),
          (simulationData.timesteps?.length || 1) - 1
        );
        const geojson = simulationDataToGeoJSON(simulationData, step);
        simSrc.setData(geojson);

        // When real computational simulation is active, hide schematic polygon layer
        if (map.getLayer('terra05-flood-layer')) {
          map.setLayoutProperty('terra05-flood-layer', 'visibility', 'none');
        }
        if (map.getLayer('terra05-water-edge-layer')) {
          map.setLayoutProperty('terra05-water-edge-layer', 'visibility', 'none');
        }
        if (map.getLayer('terra05-sim-water-layer')) {
          map.setLayoutProperty('terra05-sim-water-layer', 'visibility', layers.floodDepth ? 'visible' : 'none');
        }
        if (map.getLayer('terra05-sim-water-edge-layer')) {
          map.setLayoutProperty('terra05-sim-water-edge-layer', 'visibility', layers.floodDepth ? 'visible' : 'none');
        }
      } else {
        // Clear sim layer, restore schematic polygon if floodDepth layer is active
        simSrc.setData({ type: 'FeatureCollection', features: [] });
        if (map.getLayer('terra05-flood-layer')) {
          map.setLayoutProperty('terra05-flood-layer', 'visibility', layers.floodDepth ? 'visible' : 'none');
        }
        if (map.getLayer('terra05-water-edge-layer')) {
          map.setLayoutProperty('terra05-water-edge-layer', 'visibility', layers.floodDepth ? 'visible' : 'none');
        }
        if (map.getLayer('terra05-sim-water-layer')) {
          map.setLayoutProperty('terra05-sim-water-layer', 'visibility', 'none');
        }
        if (map.getLayer('terra05-sim-water-edge-layer')) {
          map.setLayoutProperty('terra05-sim-water-edge-layer', 'visibility', 'none');
        }
      }
    } catch (err) {
      console.error('[TERRA05][SIM WATER UPDATE ERROR]', err);
    }
  }, [simulationData, simStepIndex, timelineStep, mapLoaded, layers.floodDepth]);

  // 4. Update Layer Visibilities
  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return;
    const map = mapRef.current;

    const setVisibility = (layerId: string, visible: boolean) => {
      try {
        if (map.getLayer(layerId)) {
          map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none');
        }
      } catch (e) {
        // Suppress benign layer query if layer mounting
      }
    };

    setVisibility('bmc-drainage-layer', layers.drainage);
    setVisibility('runoff-flow-layer', layers.runoffFlow);
    setVisibility('mumbai-roads-layer', layers.roadsExposure);
    setVisibility('critical-infra-layer', layers.criticalInfra);
    setVisibility('bmc-spots-layer', layers.floodSpots);
    setVisibility('terra05-sim-water-layer', layers.floodDepth && Boolean(simulationData));
    setVisibility('terra05-sim-water-edge-layer', layers.floodDepth && Boolean(simulationData));
    setVisibility('terra05-flood-layer', layers.floodDepth && !simulationData);
    setVisibility('terra05-water-edge-layer', layers.floodDepth && !simulationData);
    setVisibility('terra05-uncertainty-layer', layers.uncertainty);
    setVisibility('historical-2019-layer', layers.historical2019);
    setVisibility('terra05-risk-grid-fill', layers.riskGrid);
    setVisibility('terra05-risk-grid-line', layers.riskGrid);
  }, [layers, mapLoaded, simulationData]);

  // 5. Smooth camera flyTo when a user explicitly selects a focus area
  const flyToLocation = (loc: MumbaiLocation) => {
    onSelectLocation(loc);
    setIsLocationDropdownOpen(false);
    if (!mapRef.current) return;
    mapRef.current.flyTo({
      center: [loc.lng, loc.lat],
      zoom: 15.0,
      pitch: 25, // Clean, non-extreme perspective
      bearing: 0,
      speed: 1.1,
      essential: true,
    });
  };

  // 6. Camera Presets (3D / 2D Top / Reset)
  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return;
    const map = mapRef.current;

    try {
      if (cameraPreset === 'TOP') {
        map.flyTo({ center: [72.875, 19.068], zoom: 14.0, pitch: 0, bearing: 0, duration: 1000 });
      } else if (cameraPreset === '3D') {
        map.flyTo({ center: [72.875, 19.068], zoom: 14.2, pitch: 42, bearing: 18, duration: 1000 });
      } else if (cameraPreset === 'RESET') {
        map.flyTo({ center: [72.875, 19.068], zoom: 14.2, pitch: 20, bearing: 0, duration: 1000 });
      }
    } catch (camErr) {
      console.warn('[TERRA05][CAMERA PRESET NOTE]', camErr);
    }
  }, [cameraPreset, mapLoaded]);

  // Clamped tooltip positioning to prevent viewport overflow
  const tooltipLeft = hoveredFeature ? Math.min(hoveredFeature.x + 14, (mapContainerRef.current?.offsetWidth || 800) - 240) : 0;
  const tooltipTop = hoveredFeature ? Math.max(hoveredFeature.y + 14, 55) : 0;

  return (
    <div className="w-full h-full relative select-none">
      {/* Real MapLibre GL WebGL Map Viewport */}
      <div 
        ref={mapContainerRef} 
        className="w-full h-full absolute inset-0 bg-[#E2E8F0]" 
        style={{ width: '100%', height: '100%' }}
      />

      {/* Subtle Rainfall Overlay Canvas */}
      <canvas
        ref={rainCanvasRef}
        className="w-full h-full absolute inset-0 pointer-events-none z-10"
      />

      {/* Top Left: Compact Focus Area Indicator & Dropdown */}
      <div className="absolute top-3 left-4 z-20 flex items-center space-x-2">
        <div className="bg-white/95 backdrop-blur-md border border-gis-border rounded-lg shadow-gis px-3 py-1.5 flex items-center space-x-2 text-xs font-mono">
          <span className="w-2 h-2 rounded-full bg-sky-600" />
          <span className="font-bold text-slate-900">MITHI RIVER BASIN</span>
          <span className="text-slate-300">|</span>
          <span className="text-slate-600 font-medium">KURLA–SION CORRIDOR</span>
        </div>

        {/* Compact Dropdown Selector */}
        <div className="relative">
          <button
            onClick={() => setIsLocationDropdownOpen(!isLocationDropdownOpen)}
            className="bg-white/95 backdrop-blur-md border border-gis-border hover:border-slate-400 px-3 py-1.5 rounded-lg shadow-gis text-xs font-mono font-bold text-slate-800 flex items-center space-x-1.5 transition-all"
          >
            <span>FOCUS AREA: {selectedLocation?.name || 'Select'}</span>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </button>

          {isLocationDropdownOpen && (
            <div className="absolute left-0 mt-1.5 w-60 bg-white border border-gis-border rounded-lg shadow-float py-1 z-30 font-mono text-xs">
              <div className="px-3 py-1 text-[10px] uppercase font-bold text-slate-400 border-b border-slate-100">
                SELECT BASIN FOCUS
              </div>
              {MUMBAI_GEO_LOCATIONS.map((loc) => {
                const isSelected = selectedLocation?.id === loc.id;
                const sc = loc.scenarios[rainfall] || loc.scenarios[100];
                return (
                  <button
                    key={loc.id}
                    onClick={() => flyToLocation(loc)}
                    className={`w-full text-left px-3 py-2 flex items-center justify-between hover:bg-slate-50 transition-colors ${
                      isSelected ? 'bg-sky-50 text-sky-900 font-bold' : 'text-slate-700'
                    }`}
                  >
                    <span>{loc.name}</span>
                    <span className="text-[10px] text-slate-500 font-normal">
                      {sc.depthM.toFixed(2)}m
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Top Center: Clean Scenario Event Status Pill */}
      <div className="absolute top-3 left-1/2 -translate-x-1/2 z-20 pointer-events-none">
        <div className="bg-white/95 backdrop-blur-md border border-gis-border rounded-full shadow-gis px-4 py-1.5 flex items-center space-x-2 text-xs font-mono">
          <span className={`w-2 h-2 rounded-full ${
            timelineStep === 0 ? 'bg-slate-400' :
            timelineStep === 4 ? 'bg-rose-600 animate-pulse' :
            timelineStep > 4 ? 'bg-amber-500' : 'bg-sky-600'
          }`} />
          <span className="font-bold text-slate-900">
            {timelineStep === 4 ? 'PEAK INUNDATION EVENT' :
             timelineStep > 4 ? 'RECESSION PHASE' :
             timelineStep === 0 ? 'SCENARIO STANDBY' : 'WATER PROPAGATION ACTIVE'}
          </span>
          <span className="text-slate-300 font-normal">|</span>
          <span className="text-slate-600">{rainfall} mm/hr</span>
          <span className="text-slate-300 font-normal">|</span>
          <span className="font-bold text-sky-700">T+0{timelineStep}</span>
        </div>
      </div>

      {/* Bottom Left: River Status Pill */}
      <div className="absolute bottom-24 left-4 z-20 pointer-events-none">
        <div className="bg-white/95 backdrop-blur-md border border-gis-border text-slate-900 text-[10px] font-mono font-bold px-3 py-1.5 rounded-lg shadow-gis flex items-center space-x-2">
          <span className="w-1.5 h-1.5 rounded-full bg-sky-500" />
          <span>MITHI RIVER</span>
          <span className="text-slate-400 font-normal">| Stress: <strong className={timelineMetrics.mithiRiverStatus === 'BANKFULL / OVERFLOW' ? 'text-rose-600' : 'text-sky-700'}>{timelineMetrics.mithiRiverStatus}</strong></span>
        </div>
      </div>

      {/* GIS Hover Inspection Tooltip (Constrained in Viewport) */}
      {hoveredFeature && (
        <div 
          style={{ left: tooltipLeft, top: tooltipTop }}
          className="absolute z-40 pointer-events-none bg-white/95 backdrop-blur-md border border-gis-border rounded-lg shadow-float p-2.5 text-xs font-mono space-y-1 w-60"
        >
          <div className="font-bold text-slate-900 border-b border-slate-100 pb-1">
            {hoveredFeature.name}
          </div>
          {hoveredFeature.depth !== undefined && (
            <div className="flex justify-between space-x-4 text-[11px]">
              <span className="text-slate-500">Current Depth:</span>
              <span className="font-bold text-sky-700">{hoveredFeature.depth.toFixed(2)}m</span>
            </div>
          )}
          {hoveredFeature.maxDepth !== undefined && (
            <div className="flex justify-between space-x-4 text-[11px]">
              <span className="text-slate-500">Peak Simulated:</span>
              <span className="font-bold text-slate-800">{hoveredFeature.maxDepth.toFixed(2)}m</span>
            </div>
          )}
          {hoveredFeature.elevation !== undefined && (
            <div className="flex justify-between space-x-4 text-[11px]">
              <span className="text-slate-500">Elevation:</span>
              <span className="font-bold text-slate-800">{hoveredFeature.elevation}m MSL</span>
            </div>
          )}
          {hoveredFeature.builtUp !== undefined && (
            <div className="flex justify-between space-x-4 text-[11px]">
              <span className="text-slate-500">Impervious Cover:</span>
              <span className="font-bold text-slate-700">{hoveredFeature.builtUp}%</span>
            </div>
          )}
          <div className="text-[9px] text-sky-700 pt-0.5 border-t border-slate-100 flex items-center justify-between">
            <span>{hoveredFeature.isSimCell ? '2D Hydrodynamic Accumulation Cell' : 'TERRA05 Spatial Cell'}</span>
            <span className="text-slate-400">Click to select</span>
          </div>
        </div>
      )}
    </div>
  );
};
