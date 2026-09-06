/**
 * Map layer construction.
 *
 * Everything is drawn with map-native GeoJSON sources and layers rather than
 * DOM markers. At the 20-50 shuttle target, DOM markers mean fifty absolutely
 * positioned elements repositioned every frame; native layers mean one source
 * update and one GPU draw.
 */

import type { FeatureCollection, Geometry } from 'geojson';
import type { LayerSpecification } from 'maplibre-gl';

import type { Route, Shuttle, Stop } from '../../types/domain';

export const SOURCE_ROUTES = 'routes';
export const SOURCE_STOPS = 'stops';
export const SOURCE_SHUTTLES = 'shuttles';
export const SOURCE_USER = 'user';

export const LAYER_ROUTE_CASING = 'route-casing';
export const LAYER_ROUTE_LINE = 'route-line';
export const LAYER_STOP = 'stop';
export const LAYER_STOP_LABEL = 'stop-label';
export const LAYER_SHUTTLE_HALO = 'shuttle-halo';
export const LAYER_SHUTTLE_BODY = 'shuttle-body';
export const LAYER_SHUTTLE_ARROW = 'shuttle-arrow';
export const LAYER_USER_HALO = 'user-halo';
export const LAYER_USER_DOT = 'user-dot';

export const SHUTTLE_ARROW_ICON = 'shuttle-arrow-icon';

type Collection = FeatureCollection<Geometry>;

export const EMPTY_COLLECTION: Collection = { type: 'FeatureCollection', features: [] };

/** Route polylines, one LineString per route. */
export function routesToGeoJson(routes: Route[]): Collection {
  return {
    type: 'FeatureCollection',
    features: routes.map((route) => ({
      type: 'Feature',
      id: route.id,
      properties: { id: route.id, name: route.name, color: route.color },
      geometry: { type: 'LineString', coordinates: route.geometry },
    })),
  };
}

/** Stop markers, coloured by the route they belong to. */
export function stopsToGeoJson(routes: Route[]): Collection {
  const features = routes.flatMap((route) =>
    route.stops.map((stop: Stop) => ({
      type: 'Feature' as const,
      id: stop.id,
      properties: { id: stop.id, name: stop.name, color: route.color },
      geometry: { type: 'Point' as const, coordinates: [stop.longitude, stop.latitude] },
    })),
  );

  return { type: 'FeatureCollection', features };
}

/** Live vehicles. `position` is the animated position, not the last received one. */
export function shuttlesToGeoJson(
  shuttles: { shuttle: Shuttle; longitude: number; latitude: number }[],
  routeColors: Record<string, string>,
  selectedId: string | null,
): Collection {
  return {
    type: 'FeatureCollection',
    features: shuttles.map(({ shuttle, longitude, latitude }) => ({
      type: 'Feature',
      id: shuttle.id,
      properties: {
        id: shuttle.id,
        name: shuttle.name,
        heading: shuttle.heading,
        color: routeColors[shuttle.route_id] ?? '#2563eb',
        selected: shuttle.id === selectedId,
        stale: shuttle.status === 'STALE',
      },
      geometry: { type: 'Point', coordinates: [longitude, latitude] },
    })),
  };
}

export function pointToGeoJson(longitude: number, latitude: number): Collection {
  return {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        properties: {},
        geometry: { type: 'Point', coordinates: [longitude, latitude] },
      },
    ],
  };
}

/**
 * A white arrow drawn to a canvas, registered as an SDF image.
 *
 * SDF is what allows `icon-color` to tint one shared image per route colour,
 * instead of shipping an icon file for every colour in the network.
 */
export function createArrowImage(size = 24): ImageData {
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;

  const context = canvas.getContext('2d');
  if (!context) {
    // jsdom and headless contexts have no 2D canvas; a blank image keeps the
    // map rendering rather than throwing during tests.
    return new ImageData(size, size);
  }

  const middle = size / 2;
  context.fillStyle = '#ffffff';
  context.beginPath();
  context.moveTo(middle, size * 0.16);
  context.lineTo(size * 0.82, size * 0.84);
  context.lineTo(middle, size * 0.66);
  context.lineTo(size * 0.18, size * 0.84);
  context.closePath();
  context.fill();

  return context.getImageData(0, 0, size, size);
}

/** Every layer, in draw order: routes underneath, vehicles on top. */
export function layerSpecs(): LayerSpecification[] {
  return [
    {
      id: LAYER_ROUTE_CASING,
      type: 'line',
      source: SOURCE_ROUTES,
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': '#ffffff', 'line-width': 7, 'line-opacity': 0.9 },
    },
    {
      id: LAYER_ROUTE_LINE,
      type: 'line',
      source: SOURCE_ROUTES,
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': ['get', 'color'], 'line-width': 4, 'line-opacity': 0.9 },
    },
    {
      id: LAYER_STOP,
      type: 'circle',
      source: SOURCE_STOPS,
      paint: {
        'circle-radius': 5,
        'circle-color': '#ffffff',
        'circle-stroke-width': 2.5,
        'circle-stroke-color': ['get', 'color'],
      },
    },
    {
      id: LAYER_STOP_LABEL,
      type: 'symbol',
      source: SOURCE_STOPS,
      minzoom: 14.5,
      layout: {
        'text-field': ['get', 'name'],
        'text-size': 11,
        'text-offset': [0, 1.1],
        'text-anchor': 'top',
        'text-font': ['Noto Sans Regular'],
      },
      paint: {
        'text-color': '#334155',
        'text-halo-color': '#ffffff',
        'text-halo-width': 1.5,
      },
    },
    {
      id: LAYER_USER_HALO,
      type: 'circle',
      source: SOURCE_USER,
      paint: { 'circle-radius': 18, 'circle-color': '#2563eb', 'circle-opacity': 0.15 },
    },
    {
      id: LAYER_USER_DOT,
      type: 'circle',
      source: SOURCE_USER,
      paint: {
        'circle-radius': 7,
        'circle-color': '#2563eb',
        'circle-stroke-width': 3,
        'circle-stroke-color': '#ffffff',
      },
    },
    {
      id: LAYER_SHUTTLE_HALO,
      type: 'circle',
      source: SOURCE_SHUTTLES,
      // Only the selected vehicle gets a halo, so the selection is obvious
      // without adding another colour to the palette.
      filter: ['==', ['get', 'selected'], true],
      paint: { 'circle-radius': 22, 'circle-color': ['get', 'color'], 'circle-opacity': 0.2 },
    },
    {
      id: LAYER_SHUTTLE_BODY,
      type: 'circle',
      source: SOURCE_SHUTTLES,
      paint: {
        'circle-radius': ['case', ['==', ['get', 'selected'], true], 13, 11],
        'circle-color': ['case', ['==', ['get', 'stale'], true], '#94a3b8', ['get', 'color']],
        'circle-stroke-width': 2.5,
        'circle-stroke-color': '#ffffff',
      },
    },
    {
      id: LAYER_SHUTTLE_ARROW,
      type: 'symbol',
      source: SOURCE_SHUTTLES,
      layout: {
        'icon-image': SHUTTLE_ARROW_ICON,
        'icon-size': 0.55,
        // Rotate with the map so the arrow always points where the shuttle is
        // actually heading, not where it heads on an unrotated screen.
        'icon-rotate': ['get', 'heading'],
        'icon-rotation-alignment': 'map',
        'icon-allow-overlap': true,
        'icon-ignore-placement': true,
      },
      paint: { 'icon-color': '#ffffff' },
    },
  ];
}
/**
 * Bounding box of the whole route network, as `[[west, south], [east, north]]`.
 *
 * Derived from the data rather than hard-coded, so editing `data/routes/*.json`
 * moves the map with it. `padding` is in degrees and keeps markers near the
 * edge of the network from sitting flush against the viewport.
 */
export function networkBounds(
  routes: Route[],
  padding = 0.0015,
): [[number, number], [number, number]] | null {
  const positions = routes.flatMap((route) => route.geometry);
  if (positions.length === 0) {
    return null;
  }

  let west = Number.POSITIVE_INFINITY;
  let south = Number.POSITIVE_INFINITY;
  let east = Number.NEGATIVE_INFINITY;
  let north = Number.NEGATIVE_INFINITY;

  for (const [longitude, latitude] of positions) {
    west = Math.min(west, longitude);
    east = Math.max(east, longitude);
    south = Math.min(south, latitude);
    north = Math.max(north, latitude);
  }

  return [
    [west - padding, south - padding],
    [east + padding, north + padding],
  ];
}
