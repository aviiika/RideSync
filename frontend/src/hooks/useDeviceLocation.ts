/**
 * Ask the browser where the device is.
 *
 * Geolocation fails often and in mundane ways — permission denied, no fix
 * indoors, unsupported browser — so every outcome produces a message the user
 * can act on rather than a silent no-op. A fix outside campus is also a failure
 * here: this is a campus service, and placing the rider three kilometres away
 * would make every ETA meaningless.
 */

import { useCallback, useState } from 'react';

import { useRiderStore } from '../stores/riderStore';
import type { Coordinate, Route } from '../types/domain';

const TIMEOUT_MS = 10_000;

/** Degrees of slack around the network before a fix counts as off campus. */
const OFF_CAMPUS_PADDING = 0.004;

export function isWithinNetwork(
  position: Coordinate,
  routes: Route[],
  padding = OFF_CAMPUS_PADDING,
): boolean {
  const points = routes.flatMap((route) => route.geometry);
  if (points.length === 0) {
    return true;
  }

  const longitudes = points.map(([longitude]) => longitude);
  const latitudes = points.map(([, latitude]) => latitude);

  return (
    position.longitude >= Math.min(...longitudes) - padding &&
    position.longitude <= Math.max(...longitudes) + padding &&
    position.latitude >= Math.min(...latitudes) - padding &&
    position.latitude <= Math.max(...latitudes) + padding
  );
}

export function useDeviceLocation(routes: Route[]) {
  const [locating, setLocating] = useState(false);
  const setPosition = useRiderStore((state) => state.setPosition);
  const setLocationError = useRiderStore((state) => state.setLocationError);

  const request = useCallback(() => {
    if (!('geolocation' in navigator)) {
      setLocationError('This browser cannot report a location.');
      return;
    }

    setLocating(true);

    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setLocating(false);
        const position = { latitude: coords.latitude, longitude: coords.longitude };

        if (!isWithinNetwork(position, routes)) {
          setLocationError("You are off campus, so campus ETAs would not apply.");
          return;
        }

        setPosition(position, 'device');
      },
      (error) => {
        setLocating(false);
        setLocationError(describeGeolocationError(error));
      },
      { enableHighAccuracy: true, timeout: TIMEOUT_MS, maximumAge: 0 },
    );
  }, [routes, setPosition, setLocationError]);

  return { locating, request };
}

function describeGeolocationError(error: GeolocationPositionError): string {
  switch (error.code) {
    case error.PERMISSION_DENIED:
      return 'Location permission denied. Set your spot on the map instead.';
    case error.POSITION_UNAVAILABLE:
      return 'No location fix available right now.';
    case error.TIMEOUT:
      return 'Locating took too long. Try again, or set your spot on the map.';
    default:
      return 'Could not read your location.';
  }
}
