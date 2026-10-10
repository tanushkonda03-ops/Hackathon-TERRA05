import React, { useEffect, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import { Map as MapLibreMap, NavigationControl, ScaleControl, GeoJSONSource } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import type { FeatureCollection, LineString, Feature } from 'geojson';
import { MumbaiLocation, MUMBAI_GEO_LOCATIONS, getLocationCatchmentBounds } from '../data/locations';
import { 
  MITHI_RIVER_GEOJSON,
  RUNOFF_FLOW_PATHS_GEOJSON,
  MUMBAI_MAJOR_ROADS_GEOJSON,
  CRITICAL_INFRASTRUCTURE_GEOJSON,
  MUMBAI_EVACUATION_CORRIDORS_GEOJSON,
  MUMBAI_MUNICIPAL_SHELTERS_GEOJSON,
} from '../data/mumbaiGeojson';
import { getBundledDrainageNetwork, getFloodSpots, getCompleteRiskMap, convertBounds4326To32643, transformRiskMapToGeoJSON4326, SimulationResponse, simulationDataToGeoJSON } from '../services/api';
import { ChevronDown } from 'lucide-react';
import { buildDownstreamTrace } from '../utils/drainageTrace';

interface DrainageFlowPath {
  coordinates: [number, number][];
  cumulativeMeters: number[];
  totalLengthMeters: number;
  phase: number;
}

// Configure MapLibre Web Worker for Vite
maplibregl.setWorkerUrl(workerUrl);

interface MapboxMumbaiProps {
  rainfall: number;
  timelineStep: number; // 0 to 6 (T00 to T06) or sim timestep
  selectedLocation: MumbaiLocation | null;
  onSelectLocation: (loc: MumbaiLocation) => void;
  layers: {
    floodSpots: boolean;
    drainage: boolean;
    runoffFlow: boolean;
    roadsExposure: boolean;
    criticalInfra: boolean;
    floodDepth: boolean;
    terrain3D: boolean;
    riskGrid: boolean;
    evacuationRoutes?: boolean;
  };
  cameraPreset: '3D' | 'TOP' | 'RESET';
  simulationData?: SimulationResponse | null;
  simStepIndex?: number;
  drainageTraceRequest?: number;
  onDrainageTraceResult?: (message: string | null) => void;
  interventions?: {
    mobilePumps: boolean;
    tidalGates: boolean;
  };
  onStatusChange?: (status: 'CONNECTING' | 'ONLINE' | 'ERROR') => void;
  onDiagnosticsUpdate?: (diag: Record<string, any>) => void;
}

export const MapboxMumbai: React.FC<MapboxMumbaiProps> = ({
  rainfall,
  timelineStep,
  selectedLocation,
  onSelectLocation,
  layers,
  cameraPreset,
  simulationData,
  simStepIndex,
  drainageTraceRequest = 0,
  onDrainageTraceResult,
  interventions,
  onStatusChange,
  onDiagnosticsUpdate,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const rainCanvasRef = useRef<HTMLCanvasElement>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [drainageNetworkLoaded, setDrainageNetworkLoaded] = useState(false);
  const [isLocationDropdownOpen, setIsLocationDropdownOpen] = useState(false);
  const locationDropdownRef = useRef<HTMLDivElement>(null);
  const fullDrainageNetworkRef = useRef<FeatureCollection | null>(null);
  const drainageFlowPathsRef = useRef<DrainageFlowPath[]>([]);
  const drainageFlowEnabledRef = useRef(false);
  const drainageFlowColorRef = useRef('#06B6D4');
  const [hoveredFeature, setHoveredFeature] = useState<{
    x: number;
    y: number;
    name: string;
    depth?: number;
    elevation?: number;
    maxDepth?: number;
    builtUp?: number;
    isSimCell?: boolean;
    isSWD?: boolean;
    isInsideFocusArea?: boolean;
    swdStatus?: string;
    swdWidth?: number;
    swdHeight?: number;
    swdLength?: number;
    invertElevation?: number;
    isEvacCorridor?: boolean;
    evacStatus?: string;
    trafficStatus?: string;
    destinationHospital?: string;
    isShelter?: boolean;
    capacity?: number;
    facilities?: string;
  } | null>(null);

  // Close location dropdown when clicking outside or pressing Escape
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (locationDropdownRef.current && !locationDropdownRef.current.contains(e.target as Node)) {
        setIsLocationDropdownOpen(false);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsLocationDropdownOpen(false);
    };
    if (isLocationDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isLocationDropdownOpen]);

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

        // --- LAYER 1: BASELINE ML RISK GRID & BENCHMARK HISTORICAL FLOOD ---
        // 1A: 100M ML Risk Grid (Backend Spatial Mesh)
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

        // --- LAYER 2: MAJOR ROAD ARTERIALS BASELINE ---
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
              'line-width': ['interpolate', ['linear'], ['zoom'], 12, 2.5, 16, 5],
              'line-dasharray': [4, 2],
              'line-opacity': 0.85,
            },
          });
        }

        // Simulated inundation is drawn only from the backend simulation response.
        if (!map.getSource('terra05-sim-water-src')) {
          map.addSource('terra05-sim-water-src', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] },
          });

          // Fluid water heatmap: continuous, organic, seamless liquid surface with ZERO grid boxes or tiles
          map.addLayer({
            id: 'terra05-sim-water-layer',
            type: 'heatmap',
            source: 'terra05-sim-water-src',
            layout: {
              visibility: layers.floodDepth ? 'visible' : 'none',
            },
            paint: {
              // Weight scales smoothly with depth (0.04m to 1.0m)
              'heatmap-weight': [
                'interpolate',
                ['linear'],
                ['get', 'depth'],
                0.04, 0.20,
                0.10, 0.45,
                0.25, 0.70,
                0.50, 0.88,
                1.00, 1.00
              ],
              // Intensity scales with zoom for consistent saturation
              'heatmap-intensity': [
                'interpolate',
                ['linear'],
                ['zoom'],
                11, 0.7,
                13, 0.9,
                15, 1.15,
                17, 1.4
              ],
              // Natural fluid aquatic palette: transparent edge -> crystal azure -> deep marine navy
              'heatmap-color': [
                'interpolate',
                ['linear'],
                ['heatmap-density'],
                0.00, 'rgba(0, 0, 0, 0)',
                0.10, 'rgba(186, 230, 253, 0.45)', // Crystal shallow edge
                0.28, 'rgba(56, 189, 248, 0.65)',  // Moderate ponding
                0.55, 'rgba(2, 132, 199, 0.80)',   // Solid water depth
                0.80, 'rgba(3, 105, 161, 0.90)',   // Deep street channel
                1.00, 'rgba(8, 47, 73, 0.95)'      // Maximum inundation
              ],
              // Radius scaled to ensure adjacent 100m points merge into a unified body of water
              'heatmap-radius': [
                'interpolate',
                ['linear'],
                ['zoom'],
                11, 14,
                12, 20,
                13, 30,
                14, 48,
                15, 78,
                16, 130,
                17, 210
              ],
              'heatmap-opacity': 0.88,
            },
          });

          // Companion invisible layer for pinpoint feature inspection (hover & click)
          map.addLayer({
            id: 'terra05-sim-water-interact-layer',
            type: 'circle',
            source: 'terra05-sim-water-src',
            layout: {
              visibility: layers.floodDepth ? 'visible' : 'none',
            },
            paint: {
              'circle-radius': [
                'interpolate',
                ['linear'],
                ['zoom'],
                12, 12,
                14, 22,
                16, 45
              ],
              'circle-color': '#0284C7',
              'circle-opacity': 0.001, // 100% visually invisible; captures mouse events
              'circle-stroke-opacity': 0.0,
            },
          });
        }

        // Pabitra's Mithi River line, drawn beneath SWD conduits and above the simulation surface.
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

        // --- LAYER 5: SURFACE RUNOFF OVERLAND FLOW PATHS ---
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

        // --- LAYER 6: BMC STORMWATER DRAINAGE (SWD) NETWORK (Rendered Above Water & Roads) ---
        // Existing and proposed GIS pipes are both shown; only existing conduits enter hydraulic styling.
        if (!map.getSource('bmc-drainage-src')) {
          map.addSource('bmc-drainage-src', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] },
          });

          map.addLayer({
            id: 'bmc-drainage-casing',
            type: 'line',
            source: 'bmc-drainage-src',
            filter: ['==', ['get', 'USER_TEXT2'], 'Existing'],
            layout: {
              'line-join': 'round',
              'line-cap': 'round',
              visibility: layers.drainage ? 'visible' : 'none',
            },
            paint: {
              'line-color': '#0F172A',
              'line-width': [
                'interpolate',
                ['exponential', 1.3],
                ['zoom'],
                11, 1.4,
                13, 2.4,
                15, 3.8,
                17, 5.6,
                19, 7.5
              ],
              'line-opacity': selectedLocation ? 0.20 : 0.40,
            },
          });

          map.addLayer({
            id: 'bmc-drainage-layer',
            type: 'line',
            source: 'bmc-drainage-src',
            filter: ['==', ['get', 'USER_TEXT2'], 'Existing'],
            layout: {
              'line-join': 'round',
              'line-cap': 'round',
              visibility: layers.drainage ? 'visible' : 'none',
            },
            paint: {
              'line-color': '#0891B2',
              'line-width': [
                'interpolate',
                ['exponential', 1.3],
                ['zoom'],
                11, 0.8,
                13, 1.6,
                15, 2.6,
                17, 4.0,
                19, 5.5
              ],
              'line-opacity': selectedLocation ? 0.40 : 0.75,
            },
          });

          map.addLayer({
            id: 'bmc-drainage-proposed-layer',
            type: 'line',
            source: 'bmc-drainage-src',
            filter: ['==', ['get', 'USER_TEXT2'], 'Proposal'],
            layout: {
              'line-join': 'round',
              'line-cap': 'round',
              visibility: layers.drainage ? 'visible' : 'none',
            },
            paint: {
              'line-color': '#D97706',
              'line-width': ['interpolate', ['exponential', 1.3], ['zoom'], 11, 0.7, 13, 1.2, 15, 1.8, 17, 2.6, 19, 3.4],
              'line-dasharray': [2, 2],
              'line-opacity': 0.68,
            },
          });
        }

        if (!map.getSource('drainage-trace-src')) {
          map.addSource('drainage-trace-src', {
            type: 'geojson',
            lineMetrics: true,
            data: { type: 'FeatureCollection', features: [] },
          });
          map.addLayer({
            id: 'drainage-trace-casing',
            type: 'line',
            source: 'drainage-trace-src',
            filter: ['==', ['get', 'kind'], 'route'],
            paint: { 'line-color': '#FFFFFF', 'line-width': 8, 'line-opacity': 0.95 },
          });
          map.addLayer({
            id: 'drainage-trace-line',
            type: 'line',
            source: 'drainage-trace-src',
            filter: ['==', ['get', 'kind'], 'route'],
            paint: {
              'line-gradient': ['interpolate', ['linear'], ['line-progress'], 0, '#0EA5E9', 1, '#7C3AED'],
              'line-width': 4.5,
              'line-opacity': 1,
            },
          });
          map.addLayer({
            id: 'drainage-trace-connector',
            type: 'line',
            source: 'drainage-trace-src',
            filter: ['==', ['get', 'kind'], 'connector'],
            paint: { 'line-color': '#F59E0B', 'line-width': 2, 'line-dasharray': [2, 2], 'line-opacity': 0.9 },
          });
          map.addLayer({
            id: 'drainage-trace-points',
            type: 'circle',
            source: 'drainage-trace-src',
            filter: ['in', ['get', 'kind'], ['literal', ['origin', 'network-end']]],
            paint: {
              'circle-radius': ['case', ['==', ['get', 'kind'], 'origin'], 6, 5],
              'circle-color': ['case', ['==', ['get', 'kind'], 'origin'], '#F59E0B', '#7C3AED'],
              'circle-stroke-color': '#FFFFFF',
              'circle-stroke-width': 2,
            },
          });
        }

        // 6B: Location-Specific Focus & Active Hydraulic Flow Layer
        if (!map.getSource('bmc-drainage-active-src')) {
          map.addSource('bmc-drainage-active-src', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] },
            lineMetrics: true,
          });

          map.addLayer({
            id: 'bmc-drainage-active-casing',
            type: 'line',
            source: 'bmc-drainage-active-src',
            layout: {
              'line-join': 'round',
              'line-cap': 'round',
              visibility: layers.drainage ? 'visible' : 'none',
            },
            paint: {
              'line-color': '#0F172A',
              'line-width': [
                'interpolate',
                ['exponential', 1.3],
                ['zoom'],
                11, 2.2,
                13, 3.6,
                15, 5.2,
                17, 7.2,
                19, 9.5
              ],
              'line-opacity': 0.65,
            },
          });

          map.addLayer({
            id: 'bmc-drainage-active-layer',
            type: 'line',
            source: 'bmc-drainage-active-src',
            layout: {
              'line-join': 'round',
              'line-cap': 'round',
              visibility: layers.drainage ? 'visible' : 'none',
            },
            paint: {
              'line-color': '#06B6D4',
              'line-width': [
                'interpolate',
                ['exponential', 1.3],
                ['zoom'],
                11, 1.4,
                13, 2.4,
                15, 3.6,
                17, 5.2,
                19, 7.0
              ],
              'line-opacity': 0.95,
            },
          });

          map.addSource('bmc-drainage-flow-points-src', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] },
          });
          map.addLayer({
            id: 'bmc-drainage-flow-points',
            type: 'circle',
            source: 'bmc-drainage-flow-points-src',
            layout: { visibility: layers.drainage ? 'visible' : 'none' },
            paint: {
              'circle-radius': ['interpolate', ['linear'], ['zoom'], 11, 1.7, 15, 2.5, 19, 3.4],
              'circle-color': ['get', 'color'],
              'circle-opacity': 0.98,
              'circle-stroke-color': 'rgba(255, 255, 255, 0.8)',
              'circle-stroke-width': 0.7,
            },
          });
        }

        // --- LAYER 7: CRITICAL INFRASTRUCTURE & BMC CHRONIC FLOOD SPOTS (Points & Symbols On Top) ---
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

        if (!map.getSource('bmc-spots-src')) {
          map.addSource('bmc-spots-src', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] },
          });

          map.addLayer({
            id: 'bmc-spots-layer',
            type: 'fill',
            source: 'bmc-spots-src',
            layout: { visibility: layers.floodSpots ? 'visible' : 'none' },
            paint: {
              'fill-color': '#B91C1C',
              'fill-opacity': 0.20,
              'fill-outline-color': '#991B1B',
            },
          });
        }

        // --- LAYER 8: SAFE EMERGENCY EVACUATION CORRIDORS & MUNICIPAL REFUGE SHELTERS ---
        if (!map.getSource('evacuation-corridors-src')) {
          map.addSource('evacuation-corridors-src', {
            type: 'geojson',
            data: MUMBAI_EVACUATION_CORRIDORS_GEOJSON,
          });

          map.addLayer({
            id: 'evacuation-corridors-casing',
            type: 'line',
            source: 'evacuation-corridors-src',
            layout: {
              'line-join': 'round',
              'line-cap': 'round',
              visibility: layers.evacuationRoutes !== false ? 'visible' : 'none',
            },
            paint: {
              'line-color': '#064E3B',
              'line-width': ['interpolate', ['linear'], ['zoom'], 11, 4.5, 14, 7.5, 17, 11],
              'line-opacity': 0.85,
            },
          });

          map.addLayer({
            id: 'evacuation-corridors-line',
            type: 'line',
            source: 'evacuation-corridors-src',
            layout: {
              'line-join': 'round',
              'line-cap': 'round',
              visibility: layers.evacuationRoutes !== false ? 'visible' : 'none',
            },
            paint: {
              'line-color': '#10B981',
              'line-width': ['interpolate', ['linear'], ['zoom'], 11, 2.5, 14, 4.5, 17, 7],
              'line-opacity': 1.0,
            },
          });
        }

        if (!map.getSource('evacuation-shelters-src')) {
          map.addSource('evacuation-shelters-src', {
            type: 'geojson',
            data: MUMBAI_MUNICIPAL_SHELTERS_GEOJSON,
          });

          map.addLayer({
            id: 'evacuation-shelters-pulse',
            type: 'circle',
            source: 'evacuation-shelters-src',
            layout: {
              visibility: layers.evacuationRoutes !== false ? 'visible' : 'none',
            },
            paint: {
              'circle-radius': 11,
              'circle-color': '#10B981',
              'circle-opacity': 0.35,
            },
          });

          map.addLayer({
            id: 'evacuation-shelters-point',
            type: 'circle',
            source: 'evacuation-shelters-src',
            layout: {
              visibility: layers.evacuationRoutes !== false ? 'visible' : 'none',
            },
            paint: {
              'circle-radius': 6.5,
              'circle-color': '#059669',
              'circle-stroke-width': 2.5,
              'circle-stroke-color': '#FFFFFF',
            },
          });
        }

        // 2D Computational Simulation Water Inundation hover and inspect handlers
        map.on('mousemove', 'terra05-sim-water-interact-layer', (e) => {
          if (e.features && e.features[0]) {
            const props = e.features[0].properties;
            map.getCanvas().style.cursor = 'pointer';
            setHoveredFeature({
              x: e.point.x,
              y: e.point.y,
              name: `Flood Inundation Zone (${props?.ward ? `Ward ${props.ward}` : 'Catchment Basin'})`,
              depth: typeof props?.depth === 'number' ? Number(props.depth) : undefined,
              elevation: typeof props?.elevation_m === 'number' ? Number(props.elevation_m) : undefined,
              maxDepth: typeof props?.max_depth === 'number' ? Number(props.max_depth) : undefined,
              builtUp: typeof props?.built_up_fraction === 'number' ? Math.round(Number(props.built_up_fraction) * 100) : undefined,
              isSimCell: true,
            });
          }
        });

        map.on('mouseleave', 'terra05-sim-water-interact-layer', () => {
          map.getCanvas().style.cursor = '';
          setHoveredFeature(null);
        });

        map.on('click', 'terra05-sim-water-interact-layer', (e) => {
          if (e.features && e.features[0]) {
            const props = e.features[0].properties;
            setHoveredFeature({
              x: e.point.x,
              y: e.point.y,
              name: `Flood Inundation Zone (${props?.ward ? `Ward ${props.ward}` : 'Catchment Basin'})`,
              depth: typeof props?.depth === 'number' ? Number(props.depth) : undefined,
              elevation: typeof props?.elevation_m === 'number' ? Number(props.elevation_m) : undefined,
              maxDepth: typeof props?.max_depth === 'number' ? Number(props.max_depth) : undefined,
              builtUp: typeof props?.built_up_fraction === 'number' ? Math.round(Number(props.built_up_fraction) * 100) : undefined,
              isSimCell: true,
            });
          }
        });

        // 100m Risk Grid hover and inspect handlers (does not hijack municipal focus)
        map.on('mousemove', 'terra05-risk-grid-fill', (e) => {
          if (e.features && e.features[0]) {
            const props = e.features[0].properties;
            map.getCanvas().style.cursor = 'pointer';
            setHoveredFeature({
              x: e.point.x,
              y: e.point.y,
              name: `Hydraulic Mesh Cell (${props?.ward ? `Ward ${props.ward}` : 'Corridor'})`,
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
            const props = e.features[0].properties;
            setHoveredFeature({
              x: e.point.x,
              y: e.point.y,
              name: `Hydraulic Mesh Cell (${props?.ward ? `Ward ${props.ward}` : 'Corridor'})`,
              depth: typeof props?.flood_fraction === 'number' ? Number((props.flood_fraction * 0.5).toFixed(2)) : undefined,
              elevation: typeof props?.elevation_mean === 'number' ? Math.round(props.elevation_mean * 10) / 10 : undefined,
            });
          }
        });

        // SWD Active Conduits Hover
        map.on('mousemove', 'bmc-drainage-active-layer', (e) => {
          if (e.features && e.features[0]) {
            const props = e.features[0].properties;
            map.getCanvas().style.cursor = 'pointer';
            setHoveredFeature({
              x: e.point.x,
              y: e.point.y,
              name: `SWD Conduit ${props?.US_NODE_ID ? `#${props.US_NODE_ID} → #${props.DS_NODE_ID}` : 'Municipal Drain'}`,
              swdWidth: typeof props?.CONDUIT_WI === 'number' ? props.CONDUIT_WI : undefined,
              swdHeight: typeof props?.CONDUIT_HE === 'number' ? props.CONDUIT_HE : undefined,
              swdLength: typeof props?.CONDUIT_LE === 'number' ? props.CONDUIT_LE : undefined,
              invertElevation: typeof props?.US_INVERT === 'number' ? props.US_INVERT : undefined,
              isSWD: true,
              isInsideFocusArea: true,
              swdStatus: 'Existing municipal asset',
            });
          }
        });

        map.on('mouseleave', 'bmc-drainage-active-layer', () => {
          map.getCanvas().style.cursor = '';
          setHoveredFeature(null);
        });

        // Existing and proposed SWD inventory inspection
        map.on('mousemove', 'bmc-drainage-layer', (e) => {
          if (e.features && e.features[0]) {
            const props = e.features[0].properties;
            map.getCanvas().style.cursor = 'pointer';
            setHoveredFeature({
              x: e.point.x,
              y: e.point.y,
              name: `SWD Conduit ${props?.US_NODE_ID ? `#${props.US_NODE_ID} → #${props.DS_NODE_ID}` : 'Municipal Drain'}`,
              swdWidth: typeof props?.CONDUIT_WI === 'number' ? props.CONDUIT_WI : undefined,
              swdHeight: typeof props?.CONDUIT_HE === 'number' ? props.CONDUIT_HE : undefined,
              swdLength: typeof props?.CONDUIT_LE === 'number' ? props.CONDUIT_LE : undefined,
              invertElevation: typeof props?.US_INVERT === 'number' ? props.US_INVERT : undefined,
              isSWD: true,
              isInsideFocusArea: false,
              swdStatus: 'Existing municipal asset',
            });
          }
        });

        map.on('mouseleave', 'bmc-drainage-layer', () => {
          map.getCanvas().style.cursor = '';
          setHoveredFeature(null);
        });

        map.on('mousemove', 'bmc-drainage-proposed-layer', (e) => {
          if (e.features && e.features[0]) {
            const props = e.features[0].properties;
            map.getCanvas().style.cursor = 'pointer';
            setHoveredFeature({
              x: e.point.x,
              y: e.point.y,
              name: `Proposed SWD conduit ${props?.US_NODE_ID ? `#${props.US_NODE_ID} → #${props.DS_NODE_ID}` : ''}`,
              swdWidth: typeof props?.CONDUIT_WI === 'number' ? props.CONDUIT_WI : undefined,
              swdHeight: typeof props?.CONDUIT_HE === 'number' ? props.CONDUIT_HE : undefined,
              swdLength: typeof props?.CONDUIT_LE === 'number' ? props.CONDUIT_LE : undefined,
              isSWD: true,
              isInsideFocusArea: false,
              swdStatus: 'Proposed · excluded from simulation',
            });
          }
        });

        map.on('mouseleave', 'bmc-drainage-proposed-layer', () => {
          map.getCanvas().style.cursor = '';
          setHoveredFeature(null);
        });

        // Evacuation Corridors Hover
        map.on('mousemove', 'evacuation-corridors-line', (e) => {
          if (e.features && e.features[0]) {
            const props = e.features[0].properties;
            map.getCanvas().style.cursor = 'pointer';
            setHoveredFeature({
              x: e.point.x,
              y: e.point.y,
              name: props?.name || 'Safe Evacuation Corridor',
              elevation: typeof props?.elevationM === 'number' ? props.elevationM : undefined,
              isEvacCorridor: true,
              evacStatus: props?.status,
              trafficStatus: props?.trafficStatus,
              destinationHospital: props?.destinationHospital,
            });
          }
        });

        map.on('mouseleave', 'evacuation-corridors-line', () => {
          map.getCanvas().style.cursor = '';
          setHoveredFeature(null);
        });

        // Evacuation Shelters Hover
        map.on('mousemove', 'evacuation-shelters-point', (e) => {
          if (e.features && e.features[0]) {
            const props = e.features[0].properties;
            map.getCanvas().style.cursor = 'pointer';
            setHoveredFeature({
              x: e.point.x,
              y: e.point.y,
              name: props?.name || 'Municipal Refuge Shelter',
              elevation: typeof props?.elevationM === 'number' ? props.elevationM : undefined,
              isShelter: true,
              capacity: props?.capacity,
              facilities: props?.facilities,
            });
          }
        });

        map.on('mouseleave', 'evacuation-shelters-point', () => {
          map.getCanvas().style.cursor = '';
          setHoveredFeature(null);
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
      onDiagnosticsUpdate?.({
        mapLoaded: true,
        styleLoaded: true,
        drainageNetwork: 'LOADING',
        floodSpots: 'LOADING',
        riskGrid: 'NOT LOADED',
      });
      setupLayers();

      getFloodSpots()
        .then((spots) => {
          if (!mapRef.current || !spots.features?.length) throw new Error('No flood-prone locations returned');
          const src = mapRef.current.getSource('bmc-spots-src') as GeoJSONSource | undefined;
          src?.setData(spots);
          onDiagnosticsUpdate?.({ floodSpots: `AVAILABLE · ${spots.features.length} locations` });
        })
        .catch((err) => {
          console.warn('[TERRA05][FLOOD SPOTS] Municipal flood-prone locations unavailable:', err);
          const src = mapRef.current?.getSource('bmc-spots-src') as GeoJSONSource | undefined;
          src?.setData({ type: 'FeatureCollection', features: [] });
          onDiagnosticsUpdate?.({ floodSpots: 'UNAVAILABLE' });
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

  // Keep mapped conduits neutral until conduit-specific hydraulic outputs exist.
  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return;
    const map = mapRef.current;

    try {
      if (map.getLayer('bmc-drainage-layer')) {
        map.setPaintProperty('bmc-drainage-layer', 'line-color', '#0891B2');
        map.setPaintProperty('bmc-drainage-layer', 'line-opacity', selectedLocation ? 0.40 : 0.75);
      }
      if (map.getLayer('bmc-drainage-casing')) {
        map.setPaintProperty('bmc-drainage-casing', 'line-opacity', selectedLocation ? 0.20 : 0.40);
      }

    } catch (updateErr) {
      console.error('[TERRA05][MAP INPUT STYLE ERROR]', updateErr);
    }
  }, [mapLoaded, selectedLocation]);

  // Highlight local conduits and restore rainfall-responsive hydraulic color progression.
  const updateActiveDrainage = (
    network: FeatureCollection | null,
    location: MumbaiLocation | null
  ) => {
    if (!mapRef.current) return;
    const map = mapRef.current;
    const activeSrc = map.getSource('bmc-drainage-active-src') as GeoJSONSource | undefined;
    if (!activeSrc) return;

    const net = network || fullDrainageNetworkRef.current;
    if (!net || !net.features || net.features.length === 0) {
      activeSrc.setData({ type: 'FeatureCollection', features: [] });
      drainageFlowPathsRef.current = [];
      return;
    }

    if (!location) {
      activeSrc.setData({ type: 'FeatureCollection', features: [] });
      drainageFlowPathsRef.current = [];
      return;
    }

    const bounds = getLocationCatchmentBounds(location);
    let localizedFeatures: Feature[] = [];

    if (bounds) {
      localizedFeatures = net.features.filter((feat) => {
        if (String(feat.properties?.USER_TEXT2 ?? '').trim().toLowerCase() !== 'existing') return false;
        if (!feat.geometry) return false;
        if (feat.geometry.type === 'LineString') {
          const coords = feat.geometry.coordinates;
          return coords.some(([lng, lat]) =>
            lng >= bounds.minLng && lng <= bounds.maxLng &&
            lat >= bounds.minLat && lat <= bounds.maxLat
          );
        }
        if (feat.geometry.type === 'MultiLineString') {
          const coords = feat.geometry.coordinates;
          return coords.some((line) => line.some(([lng, lat]) =>
            lng >= bounds.minLng && lng <= bounds.maxLng &&
            lat >= bounds.minLat && lat <= bounds.maxLat
          ));
        }
        return false;
      });
    }

    activeSrc.setData({
      type: 'FeatureCollection',
      features: localizedFeatures,
    });

    // Build tracer paths only from the backend conduits selected for this locality.
    const flowCandidates = localizedFeatures.flatMap((feature, featureIndex) => {
      if (!feature.geometry) return [];
      const geometry = feature.geometry;
      const lines: [number, number][][] = geometry.type === 'LineString'
        ? [geometry.coordinates as [number, number][]]
        : geometry.type === 'MultiLineString'
          ? geometry.coordinates as [number, number][][]
          : [];

      return lines.map((coordinates, lineIndex) => {
        if (coordinates.length < 2) return null;
        const cumulativeMeters = [0];
        for (let index = 1; index < coordinates.length; index += 1) {
          const [lngA, latA] = coordinates[index - 1];
          const [lngB, latB] = coordinates[index];
          const meanLatitude = ((latA + latB) / 2) * Math.PI / 180;
          const dx = (lngB - lngA) * 111_320 * Math.cos(meanLatitude);
          const dy = (latB - latA) * 110_540;
          cumulativeMeters.push(cumulativeMeters[index - 1] + Math.hypot(dx, dy));
        }
        const totalLengthMeters = cumulativeMeters[cumulativeMeters.length - 1];
        if (!Number.isFinite(totalLengthMeters) || totalLengthMeters <= 0) return null;
        const nodeId = String(feature.properties?.US_NODE_ID ?? `${featureIndex}-${lineIndex}`);
        const seed = Array.from(nodeId).reduce((value, character) => (value * 31 + character.charCodeAt(0)) % 997, 7);
        return { coordinates, cumulativeMeters, totalLengthMeters, phase: seed / 997 };
      }).filter((path): path is DrainageFlowPath => path !== null);
    });
    const flowStride = Math.max(1, Math.ceil(flowCandidates.length / 240));
    drainageFlowPathsRef.current = flowCandidates.filter((_, index) => index % flowStride === 0).slice(0, 240);

    if (map.getLayer('bmc-drainage-active-layer')) {
      let style = { color: '#06B6D4', width: 2.8 };
      const timestepIndex = Math.min(
        Math.max(0, simStepIndex ?? timelineStep),
        Math.max(0, (simulationData?.timesteps.length || 1) - 1),
      );
      const current = simulationData?.timesteps[timestepIndex];
      const previous = simulationData?.timesteps[timestepIndex - 1];
      drainageFlowEnabledRef.current = Boolean(current && current.drainage_removed_volume_m3 > 0);

      if (current) {
        const storagePeak = Math.max(1, ...simulationData.timesteps.map((step) => step.surface_storage_volume_m3));
        const storageShare = current.surface_storage_volume_m3 / storagePeak;
        const storageRising = previous
          ? current.surface_storage_volume_m3 > previous.surface_storage_volume_m3
          : current.surface_storage_volume_m3 > 0;
        if (current.rainfall_intensity_mm_per_hr <= 0) {
          style = current.drainage_removed_volume_m3 > 0
            ? { color: '#0284C7', width: 3.2 }
            : { color: '#06B6D4', width: 2.8 };
        } else if (storageRising) {
          style = storageShare >= 0.68
            ? { color: '#EF4444', width: 5.2 }
            : storageShare >= 0.34
              ? { color: '#F97316', width: 4.4 }
              : { color: '#FACC15', width: 3.2 };
        } else {
          style = storageShare >= 0.68
            ? { color: '#F97316', width: 4.4 }
            : storageShare >= 0.28
              ? { color: '#FACC15', width: 3.2 }
              : { color: '#06B6D4', width: 2.8 };
        }
      }
      const activeWidth = style.width;
      drainageFlowColorRef.current = style.color;

      // Use one color per rainfall step so the whole selected pipe shifts together.
      map.setPaintProperty('bmc-drainage-active-layer', 'line-color', style.color);
      map.setPaintProperty('bmc-drainage-active-layer', 'line-width', [
        'interpolate', ['exponential', 1.3], ['zoom'],
        11, activeWidth * 0.7,
        14, activeWidth * 1.0,
        17, activeWidth * 1.5,
        19, activeWidth * 2.0
      ]);

      if (map.getLayer('bmc-drainage-active-casing')) {
        map.setPaintProperty('bmc-drainage-active-casing', 'line-width', [
          'interpolate', ['exponential', 1.3], ['zoom'],
          11, activeWidth * 0.7 + 1.2,
          14, activeWidth * 1.0 + 1.6,
          17, activeWidth * 1.5 + 2.2,
          19, activeWidth * 2.0 + 2.6
        ]);
      }
    }
  };

  // Load Pabitra's full municipal SWD inventory bundled with the frontend build.
  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return;
    const source = mapRef.current.getSource('bmc-drainage-src') as GeoJSONSource | undefined;
    if (!source) return;

    const controller = new AbortController();
    getBundledDrainageNetwork(controller.signal)
      .then((network) => {
        if (!network.features?.length) throw new Error('The existing municipal drainage layer is empty');
        fullDrainageNetworkRef.current = network;
        source.setData(network);
        updateActiveDrainage(network, selectedLocation);
        const existingCount = network.features.filter((feature) => String(feature.properties?.USER_TEXT2 ?? '').trim().toLowerCase() === 'existing').length;
        const proposedCount = network.features.length - existingCount;
        onDiagnosticsUpdate?.({ drainageNetwork: `AVAILABLE · ${existingCount} existing + ${proposedCount} proposed conduits` });
        setDrainageNetworkLoaded(true);
      })
      .catch((error: unknown) => {
        if ((error as { name?: string })?.name !== 'AbortError') {
          console.warn('[TERRA05][DRAINAGE] Existing municipal network unavailable:', error);
          fullDrainageNetworkRef.current = null;
          source.setData({ type: 'FeatureCollection', features: [] });
          updateActiveDrainage(null, selectedLocation);
          onDiagnosticsUpdate?.({ drainageNetwork: 'UNAVAILABLE' });
          setDrainageNetworkLoaded(true);
        }
      });

    return () => controller.abort();
  }, [mapLoaded]);

  // Fetch every historical flood-label grid cell in the current view, rather than an arbitrary first page.
  useEffect(() => {
    if (!mapLoaded || !layers.riskGrid || !mapRef.current) return;
    const map = mapRef.current;
    let debounceTimer: number | undefined;
    let controller: AbortController | null = null;

    const loadVisibleGrid = () => {
      if (debounceTimer !== undefined) window.clearTimeout(debounceTimer);
      debounceTimer = window.setTimeout(async () => {
        controller?.abort();
        const requestController = new AbortController();
        controller = requestController;
        try {
          const bounds = map.getBounds();
          const projectedBounds = convertBounds4326To32643(
            bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth(),
          );
          onDiagnosticsUpdate?.({ riskGrid: 'LOADING' });
          const data = await getCompleteRiskMap({ ...projectedBounds, signal: requestController.signal });
          if (!mapRef.current || requestController.signal.aborted) return;
          const geojson = transformRiskMapToGeoJSON4326(data);
          const src = mapRef.current.getSource('terra05-risk-grid-src') as GeoJSONSource | undefined;
          src?.setData(geojson);
          onDiagnosticsUpdate?.({ riskGrid: `AVAILABLE · ${geojson.features.length} historical cells` });
          console.info(`[TERRA05] Complete visible historical flood grid loaded: ${geojson.features.length} cells`);
        } catch (error) {
          if ((error as { name?: string })?.name !== 'AbortError' && !requestController.signal.aborted) {
            console.warn('[TERRA05][RISK GRID] Visible historical flood grid unavailable:', error);
            onDiagnosticsUpdate?.({ riskGrid: 'UNAVAILABLE' });
          }
        }
      }, 250);
    };

    map.on('moveend', loadVisibleGrid);
    loadVisibleGrid();
    return () => {
      map.off('moveend', loadVisibleGrid);
      if (debounceTimer !== undefined) window.clearTimeout(debounceTimer);
      controller?.abort();
    };
  }, [mapLoaded, layers.riskGrid]);

  // Trace from the selected locality to its nearest mapped conduit, then follow downstream node IDs.
  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return;
    const source = mapRef.current.getSource('drainage-trace-src') as GeoJSONSource | undefined;
    if (!source) return;
    if (!drainageTraceRequest) {
      source.setData({ type: 'FeatureCollection', features: [] });
      onDrainageTraceResult?.(null);
      return;
    }
    if (!selectedLocation) {
      onDrainageTraceResult?.('Select an area before tracing its drainage network.');
      return;
    }
    if (!drainageNetworkLoaded) {
      onDrainageTraceResult?.('Loading the drainage network…');
      return;
    }

    const network = fullDrainageNetworkRef.current;
    if (!network) {
      source.setData({ type: 'FeatureCollection', features: [] });
      onDrainageTraceResult?.('Existing municipal drainage data is unavailable. Reconnect the backend before tracing.');
      return;
    }
    const trace = network ? buildDownstreamTrace(network, [selectedLocation.lng, selectedLocation.lat]) : null;
    if (!trace) {
      source.setData({ type: 'FeatureCollection', features: [] });
      onDrainageTraceResult?.('No connected, node-linked drain found within 1.5 km of this area.');
      return;
    }

    source.setData(trace.data);
    ['drainage-trace-casing', 'drainage-trace-line', 'drainage-trace-connector', 'drainage-trace-points'].forEach((layerId) => {
      if (mapRef.current?.getLayer(layerId)) mapRef.current.moveLayer(layerId);
    });
    const points = trace.data.features.flatMap((feature) => {
      if (feature.geometry.type === 'Point') return [feature.geometry.coordinates as [number, number]];
      if (feature.geometry.type === 'LineString') return feature.geometry.coordinates as [number, number][];
      return [];
    });
    const bounds = points.reduce<[number, number, number, number]>(
      (value, point) => [
        Math.min(value[0], point[0]), Math.min(value[1], point[1]),
        Math.max(value[2], point[0]), Math.max(value[3], point[1]),
      ],
      [Infinity, Infinity, -Infinity, -Infinity],
    );
    mapRef.current.fitBounds([[bounds[0], bounds[1]], [bounds[2], bounds[3]]], {
      padding: { top: 90, right: 90, bottom: 90, left: 90 }, maxZoom: 15, duration: 700,
    });
    const lengthKm = (trace.totalLengthM / 1_000).toFixed(2);
    onDrainageTraceResult?.(
      `Nearest drain ${Math.round(trace.nearestDistanceM)} m away · ${trace.conduitCount} connected conduits · ${lengthKm} km to network end ${trace.terminalNode}${trace.truncated ? ' (trace capped)' : ''}. Network end is not confirmed as an outfall; no catchment boundary or surface-flow connection is available.`,
    );
  }, [drainageTraceRequest, drainageNetworkLoaded, mapLoaded, selectedLocation?.id, selectedLocation?.lat, selectedLocation?.lng, onDrainageTraceResult]);

  // Update the selected location highlight when the focus point changes.
  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return;
    updateActiveDrainage(fullDrainageNetworkRef.current, selectedLocation);
  }, [selectedLocation?.id, selectedLocation?.lat, selectedLocation?.lng, mapLoaded, rainfall, timelineStep, simulationData, simStepIndex]);

  // Animate small same-color tracers along real selected conduit geometries only while the
  // backend timestep reports drainage removal. They visualize network activity, not measured
  // conduit-by-conduit velocity or direction.
  useEffect(() => {
    if (!mapLoaded || !layers.drainage || !selectedLocation || !mapRef.current) return;
    const map = mapRef.current;
    const source = map.getSource('bmc-drainage-flow-points-src') as GeoJSONSource | undefined;
    if (!source) return;
    let frame = 0;
    let lastUpdate = 0;
    let hasParticles = false;

    const animate = (now: number) => {
      if (!mapRef.current || !map.getLayer('bmc-drainage-flow-points')) return;
      if (now - lastUpdate >= 66) {
        if (drainageFlowEnabledRef.current) {
          const features = drainageFlowPathsRef.current.map((path, index) => {
            const progress = (now / 7_500 + path.phase) % 1;
            const distance = progress * path.totalLengthMeters;
            let segment = 1;
            while (segment < path.cumulativeMeters.length - 1 && path.cumulativeMeters[segment] < distance) segment += 1;
            const startDistance = path.cumulativeMeters[segment - 1];
            const endDistance = path.cumulativeMeters[segment];
            const fraction = endDistance > startDistance ? (distance - startDistance) / (endDistance - startDistance) : 0;
            const start = path.coordinates[segment - 1];
            const end = path.coordinates[segment];
            return {
              type: 'Feature' as const,
              properties: { color: drainageFlowColorRef.current, particle: index },
              geometry: {
                type: 'Point' as const,
                coordinates: [start[0] + (end[0] - start[0]) * fraction, start[1] + (end[1] - start[1]) * fraction],
              },
            };
          });
          source.setData({ type: 'FeatureCollection', features });
          hasParticles = features.length > 0;
        } else if (hasParticles) {
          source.setData({ type: 'FeatureCollection', features: [] });
          hasParticles = false;
        }
        lastUpdate = now;
      }
      frame = window.requestAnimationFrame(animate);
    };

    frame = window.requestAnimationFrame(animate);
    return () => {
      window.cancelAnimationFrame(frame);
      source.setData({ type: 'FeatureCollection', features: [] });
    };
  }, [mapLoaded, layers.drainage, selectedLocation?.id]);

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
        if (map.getLayer('terra05-sim-water-layer')) {
          map.setLayoutProperty('terra05-sim-water-layer', 'visibility', layers.floodDepth ? 'visible' : 'none');
        }
        if (map.getLayer('terra05-sim-water-interact-layer')) {
          map.setLayoutProperty('terra05-sim-water-interact-layer', 'visibility', layers.floodDepth ? 'visible' : 'none');
        }
      } else {
        simSrc.setData({ type: 'FeatureCollection', features: [] });
        if (map.getLayer('terra05-sim-water-layer')) {
          map.setLayoutProperty('terra05-sim-water-layer', 'visibility', 'none');
        }
        if (map.getLayer('terra05-sim-water-interact-layer')) {
          map.setLayoutProperty('terra05-sim-water-interact-layer', 'visibility', 'none');
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

    setVisibility('bmc-drainage-casing', layers.drainage);
    setVisibility('bmc-drainage-layer', layers.drainage);
    setVisibility('bmc-drainage-proposed-layer', layers.drainage);
    setVisibility('bmc-drainage-active-casing', layers.drainage);
    setVisibility('bmc-drainage-active-layer', layers.drainage);
    setVisibility('bmc-drainage-flow-points', layers.drainage);
    setVisibility('runoff-flow-layer', layers.runoffFlow);
    setVisibility('mumbai-roads-layer', layers.roadsExposure);
    setVisibility('critical-infra-layer', layers.criticalInfra);
    setVisibility('bmc-spots-layer', layers.floodSpots);
    setVisibility('terra05-sim-water-layer', layers.floodDepth && Boolean(simulationData));
    setVisibility('terra05-sim-water-interact-layer', layers.floodDepth && Boolean(simulationData));
    setVisibility('terra05-risk-grid-fill', layers.riskGrid);
    setVisibility('terra05-risk-grid-line', layers.riskGrid);
    const evacVisible = layers.evacuationRoutes !== false;
    setVisibility('evacuation-corridors-casing', evacVisible);
    setVisibility('evacuation-corridors-line', evacVisible);
    setVisibility('evacuation-shelters-pulse', evacVisible);
    setVisibility('evacuation-shelters-point', evacVisible);
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
      speed: 1.2,
      essential: true,
    });
  };

  // Auto-fly camera whenever selectedLocation changes (from header or sidebar)
  useEffect(() => {
    if (!mapLoaded || !mapRef.current || !selectedLocation) return;
    mapRef.current.flyTo({
      center: [selectedLocation.lng, selectedLocation.lat],
      zoom: 14.8,
      pitch: 28,
      speed: 1.2,
      essential: true,
    });
  }, [selectedLocation?.id, mapLoaded]);

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

      {/* Top Map HUD Bar: Responsive Unified Container bounded away from top-right MapLayersControl */}
      <div className="absolute top-3 left-3 sm:left-4 max-w-[calc(100%-250px)] z-20 pointer-events-none flex flex-wrap items-center gap-2">
        {/* Basin Context & Focus Area Dropdown */}
        <div className="pointer-events-auto flex items-center flex-wrap gap-2">
          <div className="bg-white/95 backdrop-blur-md border border-gis-border rounded-xl shadow-gis px-3 py-1.5 flex items-center space-x-2 text-xs font-mono">
            <span className="w-2 h-2 rounded-full bg-sky-600 shrink-0" />
            <span className="font-bold text-slate-900 uppercase truncate max-w-[120px] sm:max-w-none">
              {selectedLocation?.subDistrict || "MUMBAI METROPOLITAN"}
            </span>
            <span className="text-slate-300">|</span>
            <span className="text-slate-600 font-medium uppercase">
              {selectedLocation?.ward || "CITYWIDE"}
            </span>
          </div>

          {/* Basin Selector Dropdown */}
          <div className="relative" ref={locationDropdownRef}>
            <button
              onClick={() => setIsLocationDropdownOpen(!isLocationDropdownOpen)}
              className="bg-white/95 backdrop-blur-md border border-gis-border hover:border-slate-400 px-3 py-1.5 rounded-xl shadow-gis text-xs font-mono font-bold text-slate-800 flex items-center space-x-1.5 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
            >
              <span className="truncate max-w-[140px] sm:max-w-none">
                FOCUS AREA: {selectedLocation?.name || 'Select'}
              </span>
              <ChevronDown className={`w-3.5 h-3.5 text-slate-400 shrink-0 transition-transform duration-200 ${isLocationDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {isLocationDropdownOpen && (
              <div className="absolute left-0 mt-1.5 w-64 bg-white border border-gis-border rounded-xl shadow-float py-1.5 z-30 font-mono text-xs max-h-72 overflow-y-auto">
                <div className="px-3 py-1.5 text-[9.5px] uppercase font-bold text-slate-400 border-b border-slate-100 tracking-wider">
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
                        isSelected ? 'bg-sky-50 text-sky-900 font-bold border-l-2 border-sky-600' : 'text-slate-700'
                      }`}
                    >
                      <div>
                        <div className="text-xs">{loc.name}</div>
                        <div className="text-[10px] text-slate-400 font-normal">{loc.ward}</div>
                      </div>
                      <span className="text-[10px] text-sky-800 font-mono font-semibold bg-slate-100 px-1.5 py-0.5 rounded">
                        {sc.depthM.toFixed(2)}m
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Scenario Event Status Pill */}
        <div className="pointer-events-auto flex items-center">
          <div className="bg-white/95 backdrop-blur-md border border-gis-border rounded-xl shadow-gis px-3 py-1.5 flex items-center space-x-2 text-xs font-mono">
            <span className={`w-2 h-2 rounded-full shrink-0 ${
              !simulationData ? 'bg-slate-400' :
              timelineStep === 0 ? 'bg-slate-400' :
              timelineStep === 4 ? 'bg-rose-600 animate-pulse' :
              timelineStep > 4 ? 'bg-amber-500' : 'bg-sky-600'
            }`} />
            <span className="font-bold text-slate-900 text-[11px] truncate max-w-[130px] sm:max-w-none">
              {!simulationData ? 'NO SIMULATION OUTPUT' :
               timelineStep === 4 ? 'SIMULATION PEAK' :
               timelineStep > 4 ? 'RECESSION PHASE' :
               timelineStep === 0 ? 'SCENARIO STANDBY' : 'SIMULATION TIMELINE'}
            </span>
            <span className="text-slate-300 font-normal">|</span>
            <span className="text-slate-600 text-[11px]">{rainfall} mm/hr</span>
            <span className="text-slate-300 font-normal">|</span>
            <span className="font-bold text-sky-700 text-[11px]">T+0{timelineStep}</span>
          </div>
        </div>

        {/* Active Countermeasure Mitigation Pill */}
        {(interventions?.mobilePumps || interventions?.tidalGates) && (
          <div className="pointer-events-auto flex items-center">
            <div className="bg-emerald-900/95 text-white backdrop-blur-md border border-emerald-600 rounded-xl shadow-gis px-3 py-1.5 flex items-center space-x-2 text-xs font-mono animate-in fade-in">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping shrink-0" />
              <span className="font-bold text-[11px] text-emerald-100 tracking-wide">
                {interventions.mobilePumps && interventions.tidalGates
                  ? 'MITIGATION ACTIVE: PUMPS + SLUICE GATES (-45% DEPTH)'
                  : interventions.mobilePumps
                  ? 'MITIGATION ACTIVE: MOBILE PUMPS (-30% DEPTH)'
                  : 'MITIGATION ACTIVE: TIDAL SLUICE GATES (-15% DEPTH)'}
              </span>
            </div>
          </div>
        )}
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
          {hoveredFeature.isSWD ? (
            <div className="space-y-1 text-[11px]">
              <div className="flex justify-between text-slate-500">
                <span>Catchment Scope:</span>
                <span className="font-semibold text-slate-800">
                  {hoveredFeature.isInsideFocusArea
                    ? `${selectedLocation?.name || 'Selected'} Catchment`
                    : 'Municipal Baseline'}
                </span>
              </div>
              {hoveredFeature.swdStatus && (
                <div className="flex justify-between gap-2 text-slate-500">
                  <span>Asset status:</span>
                  <span className="text-right font-semibold text-slate-800">{hoveredFeature.swdStatus}</span>
                </div>
              )}
              {hoveredFeature.swdWidth && (
                <div className="flex justify-between text-slate-500">
                  <span>Conduit Size:</span>
                  <span className="font-bold text-sky-800">
                    {hoveredFeature.swdWidth}mm × {hoveredFeature.swdHeight || hoveredFeature.swdWidth}mm
                  </span>
                </div>
              )}
              {hoveredFeature.invertElevation !== undefined && (
                <div className="flex justify-between text-slate-500">
                  <span>Invert Level:</span>
                  <span className="font-semibold text-slate-700">
                    {hoveredFeature.invertElevation}m MSL
                  </span>
                </div>
              )}
              {hoveredFeature.swdLength && (
                <div className="flex justify-between text-slate-500">
                  <span>Conduit Run:</span>
                  <span className="font-semibold text-slate-700">
                    {hoveredFeature.swdLength}m
                  </span>
                </div>
              )}
              <div className="text-[9.5px] text-slate-500 pt-0.5 border-t border-slate-100 space-y-0.5">
                <div>
                  {hoveredFeature.swdStatus?.startsWith('Proposed')
                    ? 'Proposed drainage alignment · excluded from the current backend simulation'
                    : hoveredFeature.isInsideFocusArea
                    ? 'Existing conduit within selected area · conduit-level hydraulic status unavailable'
                    : (selectedLocation
                        ? 'Municipal Baseline Infrastructure (Outside Selected Basin)'
                        : 'Municipal Baseline SWD Network (Citywide)')}
                </div>
              </div>
            </div>
          ) : hoveredFeature.isEvacCorridor ? (
            <div className="space-y-1 text-[11px]">
              <div className="flex justify-between">
                <span className="text-slate-500">Route Type:</span>
                <span className="font-bold text-emerald-800">ELEVATED EVACUATION TRUNK</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Status:</span>
                <span className="font-bold text-emerald-700 bg-emerald-50 px-1 rounded">
                  {hoveredFeature.evacStatus || 'OPEN / DRY'}
                </span>
              </div>
              {hoveredFeature.elevation !== undefined && (
                <div className="flex justify-between">
                  <span className="text-slate-500">Elevation:</span>
                  <span className="font-bold text-slate-800">{hoveredFeature.elevation}m MSL (Above Water)</span>
                </div>
              )}
              {hoveredFeature.destinationHospital && (
                <div className="text-[10px] text-slate-600 border-t border-slate-100 pt-1">
                  <span className="font-bold text-slate-800">Hospital Corridor: </span>
                  {hoveredFeature.destinationHospital}
                </div>
              )}
            </div>
          ) : hoveredFeature.isShelter ? (
            <div className="space-y-1 text-[11px]">
              <div className="flex justify-between">
                <span className="text-slate-500">Facility:</span>
                <span className="font-bold text-emerald-800">MUNICIPAL FLOOD REFUGE</span>
              </div>
              {hoveredFeature.capacity !== undefined && (
                <div className="flex justify-between">
                  <span className="text-slate-500">Shelter Capacity:</span>
                  <span className="font-bold text-slate-900">{hoveredFeature.capacity} Citizens</span>
                </div>
              )}
              {hoveredFeature.elevation !== undefined && (
                <div className="flex justify-between">
                  <span className="text-slate-500">Elevation:</span>
                  <span className="font-bold text-slate-800">{hoveredFeature.elevation}m MSL (High Ground)</span>
                </div>
              )}
              {hoveredFeature.facilities && (
                <div className="text-[10px] text-slate-600 border-t border-slate-100 pt-1">
                  <span className="font-bold text-slate-800">Amenities: </span>
                  {hoveredFeature.facilities}
                </div>
              )}
            </div>
          ) : (
            <>
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
            </>
          )}
        </div>
      )}
    </div>
  );
};
