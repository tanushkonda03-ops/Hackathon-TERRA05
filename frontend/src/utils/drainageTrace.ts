import type { Feature, FeatureCollection, LineString, Point } from 'geojson';

type DrainFeature = Feature<LineString, Record<string, unknown>>;

export interface DrainageTraceResult {
  data: FeatureCollection<LineString | Point>;
  conduitCount: number;
  totalLengthM: number;
  nearestDistanceM: number;
  terminalNode: string;
  truncated: boolean;
}

const numberProperty = (feature: DrainFeature, key: string): number | null => {
  const value = Number(feature.properties?.[key]);
  return Number.isFinite(value) ? value : null;
};

const pointOnSegment = (
  point: [number, number],
  start: [number, number],
  end: [number, number],
): { point: [number, number]; distanceM: number } => {
  const scaleX = Math.cos((point[1] * Math.PI) / 180);
  const px = point[0] * scaleX;
  const ax = start[0] * scaleX;
  const bx = end[0] * scaleX;
  const dx = bx - ax;
  const dy = end[1] - start[1];
  const denominator = dx * dx + dy * dy;
  const t = denominator === 0 ? 0 : Math.max(0, Math.min(1, ((px - ax) * dx + (point[1] - start[1]) * dy) / denominator));
  const nearest: [number, number] = [start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t];
  const deltaX = (nearest[0] - point[0]) * scaleX;
  const deltaY = nearest[1] - point[1];
  return { point: nearest, distanceM: Math.hypot(deltaX, deltaY) * 111_320 };
};

const featureKey = (feature: DrainFeature): string =>
  `${String(feature.properties.US_NODE_ID)}>${String(feature.properties.DS_NODE_ID)}`;

/** Build a nearest-conduit then downstream node trace. This is network topology, not a terrain-derived catchment. */
export function buildDownstreamTrace(
  network: FeatureCollection,
  origin: [number, number],
): DrainageTraceResult | null {
  const conduits = network.features.filter((feature): feature is DrainFeature =>
    feature.geometry?.type === 'LineString' &&
    Boolean(feature.properties?.US_NODE_ID) &&
    Boolean(feature.properties?.DS_NODE_ID) &&
    feature.geometry.coordinates.length >= 2,
  );
  if (!conduits.length) return null;

  let nearestConduit: DrainFeature | null = null;
  let nearestPoint: [number, number] | null = null;
  let nearestDistanceM = Number.POSITIVE_INFINITY;
  for (const conduit of conduits) {
    const coordinates = conduit.geometry.coordinates as [number, number][];
    for (let index = 0; index < coordinates.length - 1; index += 1) {
      const candidate = pointOnSegment(origin, coordinates[index], coordinates[index + 1]);
      if (candidate.distanceM < nearestDistanceM) {
        nearestConduit = conduit;
        nearestPoint = candidate.point;
        nearestDistanceM = candidate.distanceM;
      }
    }
  }
  if (!nearestConduit || !nearestPoint || nearestDistanceM > 1_500) return null;

  const downstreamByNode = new Map<string, DrainFeature[]>();
  for (const conduit of conduits) {
    const node = String(conduit.properties.US_NODE_ID);
    const linked = downstreamByNode.get(node) || [];
    linked.push(conduit);
    downstreamByNode.set(node, linked);
  }

  const path = [nearestConduit];
  const visited = new Set([featureKey(nearestConduit)]);
  let terminalNode = String(nearestConduit.properties.DS_NODE_ID);
  let truncated = false;
  const maxConduits = 1_000;
  while (path.length < maxConduits) {
    const candidates = (downstreamByNode.get(terminalNode) || [])
      .filter((candidate) => !visited.has(featureKey(candidate)));
    if (!candidates.length) break;

    // At a junction, continue through the branch with the lowest downstream invert (the gravity-flow direction).
    candidates.sort((left, right) => {
      const leftInvert = numberProperty(left, 'DS_INVERT') ?? Number.POSITIVE_INFINITY;
      const rightInvert = numberProperty(right, 'DS_INVERT') ?? Number.POSITIVE_INFINITY;
      return leftInvert - rightInvert;
    });
    const next = candidates[0];
    path.push(next);
    visited.add(featureKey(next));
    terminalNode = String(next.properties.DS_NODE_ID);
  }
  if (path.length === maxConduits && (downstreamByNode.get(terminalNode) || []).some((edge) => !visited.has(featureKey(edge)))) {
    truncated = true;
  }

  const routeCoordinates = path.flatMap((feature, index) => {
    const points = feature.geometry.coordinates as [number, number][];
    const previousPoints = index > 0 ? path[index - 1].geometry.coordinates as [number, number][] : [];
    const previousEnd = previousPoints[previousPoints.length - 1];
    return index > 0 && points.length &&
      previousEnd?.[0] === points[0][0] &&
      previousEnd?.[1] === points[0][1]
      ? points.slice(1)
      : points;
  });
  const totalLengthM = path.reduce((total, feature) => total + (numberProperty(feature, 'CONDUIT_LE') || 0), 0);
  const terminalPoint = routeCoordinates[routeCoordinates.length - 1];

  const data: FeatureCollection<LineString | Point> = {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        properties: { kind: 'route' },
        geometry: { type: 'LineString', coordinates: routeCoordinates },
      },
      {
        type: 'Feature',
        properties: { kind: 'connector' },
        geometry: { type: 'LineString', coordinates: [origin, nearestPoint] },
      },
      {
        type: 'Feature',
        properties: { kind: 'origin' },
        geometry: { type: 'Point', coordinates: origin },
      },
      {
        type: 'Feature',
        properties: { kind: 'network-end' },
        geometry: { type: 'Point', coordinates: terminalPoint },
      },
    ],
  };

  return { data, conduitCount: path.length, totalLengthM, nearestDistanceM, terminalNode, truncated };
}
