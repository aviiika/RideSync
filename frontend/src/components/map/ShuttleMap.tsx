/**
 * The map.
 *
 * Two rules shape this component:
 *
 * 1. It never re-renders when a shuttle moves. Positions arrive on the store,
 *    are read imperatively inside an animation frame, and are pushed straight
 *    into a GeoJSON source. React is not involved in movement at all.
 *
 * 2. Markers are interpolated, never teleported. The backend broadcasts twice
 *    a second; between frames each vehicle eases from where it was to where it
 *    now is, so the eye sees continuous motion rather than a stutter.
 */

import {
  Map as MapLibreMap,
  NavigationControl,
  type GeoJSONSource,
  type MapMouseEvent,
} from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useEffect, useRef } from 'react';

import { env } from '../../config/env';
import { useShuttleStore } from '../../stores/shuttleStore';
import type { Route, Shuttle } from '../../types/domain';
import {
  EMPTY_COLLECTION,
  LAYER_SHUTTLE_BODY,
  SHUTTLE_ARROW_ICON,
  SOURCE_ROUTES,
  SOURCE_SHUTTLES,
  SOURCE_STOPS,
  SOURCE_USER,
  createArrowImage,
  layerSpecs,
  pointToGeoJson,
  routesToGeoJson,
  shuttlesToGeoJson,
  stopsToGeoJson,
} from './layers';

/**
 * How long a marker takes to ease to its new position.
 *
 * Matched to the broadcast interval: shorter and the marker arrives early then
 * waits, longer and it lags visibly behind the reported position.
 */
const INTERPOLATION_MS = 500;

interface AnimatedVehicle {
  from: { longitude: number; latitude: number };
  to: { longitude: number; latitude: number };
  startedAt: number;
  shuttle: Shuttle;
}

interface ShuttleMapProps {
  routes: Route[];
  user: { latitude: number; longitude: number };
  onSelectShuttle: (shuttleId: string | null) => void;
}

export function ShuttleMap({ routes, user, onSelectShuttle }: ShuttleMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const readyRef = useRef(false);
  const vehiclesRef = useRef<Map<string, AnimatedVehicle>>(new Map());
  const routeColorsRef = useRef<Record<string, string>>({});
  const selectRef = useRef(onSelectShuttle);
  const routesRef = useRef<Route[]>(routes);
  const userRef = useRef(user);

  selectRef.current = onSelectShuttle;
  routesRef.current = routes;
  userRef.current = user;
  routeColorsRef.current = Object.fromEntries(routes.map((route) => [route.id, route.color]));

  // --- map lifecycle -------------------------------------------------------
  useEffect(() => {
    if (!containerRef.current || mapRef.current) {
      return;
    }

    const map = new MapLibreMap({
      container: containerRef.current,
      style: env.mapStyleUrl,
      center: [user.longitude, user.latitude],
      zoom: 14.6,
      attributionControl: { compact: true },
    });
    mapRef.current = map;

    map.addControl(new NavigationControl({ showCompass: false }), 'top-right');

    // Whatever data arrived before the style was ready is applied here, so
    // the map is never left holding empty sources.
    const onReady = () => {
      if (routesRef.current.length > 0) {
        geoJsonSource(map, SOURCE_ROUTES)?.setData(routesToGeoJson(routesRef.current));
        geoJsonSource(map, SOURCE_STOPS)?.setData(stopsToGeoJson(routesRef.current));
      }
      geoJsonSource(map, SOURCE_USER)?.setData(
        pointToGeoJson(userRef.current.longitude, userRef.current.latitude),
      );
    };

    // Overlay setup is idempotent and driven from more than one event.
    //
    // Relying on `load` alone is fragile: with a warm cache the style can be
    // ready before the listener is attached, and React's development double
    // mount creates and destroys a map around the same container. Running
    // setup on every style event, and skipping anything already present,
    // makes the outcome independent of which of those happens first.
    const initialiseOverlay = () => {
      if (!map.isStyleLoaded()) {
        return;
      }

      try {
        if (!map.hasImage(SHUTTLE_ARROW_ICON)) {
          map.addImage(SHUTTLE_ARROW_ICON, createArrowImage(), { sdf: true });
        }

        for (const id of [SOURCE_ROUTES, SOURCE_STOPS, SOURCE_SHUTTLES, SOURCE_USER]) {
          if (!map.getSource(id)) {
            map.addSource(id, { type: 'geojson', data: EMPTY_COLLECTION });
          }
        }

        for (const layer of layerSpecs()) {
          if (!map.getLayer(layer.id)) {
            map.addLayer(layer);
          }
        }
      } catch (error) {
        // Never fail silently: a half-built map is worse than a loud one.
        console.error('could not build the map overlay', error);
        return;
      }

      readyRef.current = true;
      onReady();
    };

    map.on('load', initialiseOverlay);
    map.on('styledata', initialiseOverlay);
    initialiseOverlay();

    map.on('error', (event) => {
      console.error('map error', event.error ?? event);
    });

    map.on('click', LAYER_SHUTTLE_BODY, (event: MapMouseEvent & { features?: GeoJSON.Feature[] }) => {
      const feature = event.features?.[0];
      const id = feature?.properties?.['id'];
      if (typeof id === 'string') {
        selectRef.current(id);
      }
    });

    // Clicking empty map clears the selection, the way a map app behaves.
    map.on('click', (event: MapMouseEvent) => {
      const hits = map.queryRenderedFeatures(event.point, { layers: [LAYER_SHUTTLE_BODY] });
      if (hits.length === 0) {
        selectRef.current(null);
      }
    });

    map.on('mouseenter', LAYER_SHUTTLE_BODY, () => {
      map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', LAYER_SHUTTLE_BODY, () => {
      map.getCanvas().style.cursor = '';
    });

    return () => {
      readyRef.current = false;
      map.remove();
      mapRef.current = null;
    };
    // Intentionally mounts once: the map is imperative and manages its own
    // updates from here on.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- static geometry -----------------------------------------------------
  useEffect(() => {
    const map = mapRef.current;
    if (!map || routes.length === 0) {
      return;
    }

    // If the style is not ready yet, the map's own setup will apply this.
    if (readyRef.current) {
      geoJsonSource(map, SOURCE_ROUTES)?.setData(routesToGeoJson(routes));
      geoJsonSource(map, SOURCE_STOPS)?.setData(stopsToGeoJson(routes));
    }
  }, [routes]);

  // --- rider position ------------------------------------------------------
  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    if (readyRef.current) {
      geoJsonSource(map, SOURCE_USER)?.setData(pointToGeoJson(user.longitude, user.latitude));
    }
  }, [user.latitude, user.longitude]);

  // --- live positions ------------------------------------------------------
  useEffect(() => {
    // Subscribing outside React is the point: a telemetry frame updates the
    // map without rendering a single component.
    const unsubscribe = useShuttleStore.subscribe((state) => {
      const now = performance.now();

      for (const id of state.shuttleIds) {
        const shuttle = state.shuttles[id];
        if (!shuttle) {
          continue;
        }

        const existing = vehiclesRef.current.get(id);
        const from = existing
          ? currentPosition(existing, now)
          : { longitude: shuttle.longitude, latitude: shuttle.latitude };

        vehiclesRef.current.set(id, {
          from,
          to: { longitude: shuttle.longitude, latitude: shuttle.latitude },
          startedAt: now,
          shuttle,
        });
      }

      // Drop vehicles the server no longer reports.
      for (const id of vehiclesRef.current.keys()) {
        if (!state.shuttles[id]) {
          vehiclesRef.current.delete(id);
        }
      }
    });

    return unsubscribe;
  }, []);

  // --- animation loop ------------------------------------------------------
  useEffect(() => {
    let frame = 0;

    const render = () => {
      frame = requestAnimationFrame(render);

      const map = mapRef.current;
      if (!map || !readyRef.current) {
        return;
      }

      const source = geoJsonSource(map, SOURCE_SHUTTLES);
      if (!source) {
        return;
      }

      const now = performance.now();
      const selectedId = useShuttleStore.getState().selectedShuttleId;

      const positioned = [...vehiclesRef.current.values()].map((vehicle) => {
        const { longitude, latitude } = currentPosition(vehicle, now);
        return { shuttle: vehicle.shuttle, longitude, latitude };
      });

      source.setData(shuttlesToGeoJson(positioned, routeColorsRef.current, selectedId));
    };

    frame = requestAnimationFrame(render);
    return () => cancelAnimationFrame(frame);
  }, []);

  return <div ref={containerRef} className="h-full w-full" data-testid="shuttle-map" />;
}

/** Narrow a source to a GeoJSON source, or undefined if it is not ready yet. */
function geoJsonSource(map: MapLibreMap, id: string): GeoJSONSource | undefined {
  const source = map.getSource(id);
  return source && source.type === 'geojson' ? (source as GeoJSONSource) : undefined;
}

/** Ease a vehicle from its previous position towards its reported one. */
function currentPosition(
  vehicle: AnimatedVehicle,
  now: number,
): { longitude: number; latitude: number } {
  const elapsed = now - vehicle.startedAt;
  const t = Math.min(1, Math.max(0, elapsed / INTERPOLATION_MS));
  // Smoothstep: no visible acceleration jolt at either end of a tick.
  const eased = t * t * (3 - 2 * t);

  return {
    longitude: vehicle.from.longitude + (vehicle.to.longitude - vehicle.from.longitude) * eased,
    latitude: vehicle.from.latitude + (vehicle.to.latitude - vehicle.from.latitude) * eased,
  };
}
