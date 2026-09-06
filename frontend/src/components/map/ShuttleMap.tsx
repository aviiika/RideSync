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
import type { Coordinate, Route, Shuttle } from '../../types/domain';
import { useRiderStore } from '../../stores/riderStore';
import { useDeviceLocation } from '../../hooks/useDeviceLocation';
import { LocationControl } from './LocationControl';
import { RouteLegend } from './RouteLegend';
import {
  EMPTY_COLLECTION,
  LAYER_SHUTTLE_BODY,
  LAYER_STOP,
  SHUTTLE_ARROW_ICON,
  SOURCE_ROUTES,
  SOURCE_SHUTTLES,
  SOURCE_STOPS,
  SOURCE_USER,
  createArrowImage,
  layerSpecs,
  networkBounds,
  pointToGeoJson,
  routeFilterExpressions,
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
  user: Coordinate;
  routeFilter: string | null;
  onSelectShuttle: (shuttleId: string | null) => void;
  onSelectStop: (stopId: string | null) => void;
  onChangeRouteFilter: (routeId: string | null) => void;
}

export function ShuttleMap({
  routes,
  user,
  routeFilter,
  onSelectShuttle,
  onSelectStop,
  onChangeRouteFilter,
}: ShuttleMapProps) {
  const riderSource = useRiderStore((state) => state.source);
  const picking = useRiderStore((state) => state.picking);
  const locationError = useRiderStore((state) => state.locationError);
  const startPicking = useRiderStore((state) => state.startPicking);
  const cancelPicking = useRiderStore((state) => state.cancelPicking);
  const resetRider = useRiderStore((state) => state.reset);
  const { locating, request: requestDeviceLocation } = useDeviceLocation(routes);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const readyRef = useRef(false);
  const vehiclesRef = useRef<Map<string, AnimatedVehicle>>(new Map());
  const routeColorsRef = useRef<Record<string, string>>({});
  const selectRef = useRef(onSelectShuttle);
  const selectStopRef = useRef(onSelectStop);
  const routesRef = useRef<Route[]>(routes);
  const framedRef = useRef(false);
  // Set once the map can be recentred; a no-op until then.
  const recentreRef = useRef<() => void>(() => {});
  const userRef = useRef(user);
  const filterRef = useRef(routeFilter);

  selectRef.current = onSelectShuttle;
  selectStopRef.current = onSelectStop;
  routesRef.current = routes;
  userRef.current = user;
  filterRef.current = routeFilter;
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

    // Zoom buttons only where there is room for them. On a phone the route
    // legend occupies that corner, and pinch-to-zoom is the natural gesture
    // anyway.
    if (window.innerWidth >= 1024) {
      map.addControl(new NavigationControl({ showCompass: false }), 'top-right');
    }

    // Whatever data arrived before the style was ready is applied here, so
    // the map is never left holding empty sources.
    const onReady = () => {
      if (routesRef.current.length > 0) {
        geoJsonSource(map, SOURCE_ROUTES)?.setData(routesToGeoJson(routesRef.current));
        geoJsonSource(map, SOURCE_STOPS)?.setData(stopsToGeoJson(routesRef.current));
        frameNetwork();
      }
      geoJsonSource(map, SOURCE_USER)?.setData(
        pointToGeoJson(userRef.current.longitude, userRef.current.latitude),
      );
      applyRouteFilter(map, filterRef.current);
    };

    /**
     * Fit the view to the campus and fence the map to it.
     *
     * The service is a closed campus network, so panning off to the next town
     * is never useful - it just loses the shuttles. Bounds come from the route
     * data, so editing the network moves the map with it. Framing happens once;
     * after that the view belongs to the user.
     */
    const frameNetwork = (force = false) => {
      if (framedRef.current && !force) {
        return;
      }

      const bounds = networkBounds(routesRef.current);
      if (!bounds) {
        return;
      }

      framedRef.current = true;
      map.fitBounds(bounds, { padding: 48, animate: force });
      // A wider fence than the fit, so the edges of campus stay reachable.
      map.setMaxBounds(networkBounds(routesRef.current, 0.006));
      map.setMinZoom(Math.max(13, map.getZoom() - 1.5));
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
      recentreRef.current = () => frameNetwork(true);
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

    map.on('click', (event: MapMouseEvent) => {
      // While placing the rider, a click means "stand here" and nothing else.
      if (useRiderStore.getState().picking) {
        useRiderStore
          .getState()
          .setPosition(
            { latitude: event.lngLat.lat, longitude: event.lngLat.lng },
            'picked',
          );
        return;
      }

      // Otherwise clicking empty map clears whatever panel is open, as a map
      // app does.
      const hits = map.queryRenderedFeatures(event.point, {
        layers: [LAYER_SHUTTLE_BODY, LAYER_STOP],
      });
      if (hits.length === 0) {
        selectRef.current(null);
        selectStopRef.current(null);
      }
    });

    // A stop opens its departure board: what is due here, soonest first.
    map.on('click', LAYER_STOP, (event: MapMouseEvent & { features?: GeoJSON.Feature[] }) => {
      const id = event.features?.[0]?.properties?.['id'];
      if (typeof id === 'string') {
        selectStopRef.current(id);
      }
    });

    map.on('mouseenter', LAYER_STOP, () => {
      map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', LAYER_STOP, () => {
      map.getCanvas().style.cursor = '';
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

  // --- picking mode --------------------------------------------------------
  useEffect(() => {
    const map = mapRef.current;
    if (map) {
      map.getCanvas().style.cursor = picking ? 'crosshair' : '';
    }
  }, [picking]);

  // --- route filter --------------------------------------------------------
  useEffect(() => {
    const map = mapRef.current;
    if (map && readyRef.current) {
      applyRouteFilter(map, routeFilter);
    }
  }, [routeFilter]);

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

  return (
    <div className="relative h-full w-full">
      <div className="pointer-events-none absolute left-3 top-3 z-10 flex max-w-[calc(100%-1.5rem)] flex-col items-start gap-2">
        <RouteLegend
          routes={routes}
          active={routeFilter}
          onChange={onChangeRouteFilter}
          onRecentre={() => recentreRef.current()}
        />
        <LocationControl
          source={riderSource}
          picking={picking}
          locating={locating}
          error={locationError}
          onPick={startPicking}
          onCancelPick={cancelPicking}
          onUseDevice={requestDeviceLocation}
          onReset={resetRider}
        />
      </div>
      <div ref={containerRef} className="h-full w-full" data-testid="shuttle-map" />
    </div>
  );
}

/** Show one route's lines, stops and vehicles, or the whole network. */
function applyRouteFilter(map: MapLibreMap, routeId: string | null): void {
  for (const [layerId, expression] of Object.entries(routeFilterExpressions(routeId))) {
    if (map.getLayer(layerId)) {
      map.setFilter(layerId, expression as never);
    }
  }
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
