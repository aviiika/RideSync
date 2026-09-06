/**
 * Device location.
 *
 * Geolocation fails in mundane ways and the app must say what happened rather
 * than appear to ignore the button.
 */

import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { DEFAULT_RIDER, useRiderStore } from '../stores/riderStore';
import { route } from '../test/fixtures';
import { isWithinNetwork, useDeviceLocation } from './useDeviceLocation';

const ON_CAMPUS = { latitude: 12.9705, longitude: 79.1565 };
const OFF_CAMPUS = { latitude: 13.05, longitude: 79.28 };

function stubGeolocation(
  handler: (
    success: PositionCallback,
    failure: PositionErrorCallback,
  ) => void,
) {
  vi.stubGlobal('navigator', {
    geolocation: { getCurrentPosition: handler },
  });
}

beforeEach(() => {
  localStorage.clear();
  useRiderStore.setState({
    position: DEFAULT_RIDER,
    source: 'default',
    picking: false,
    locationError: null,
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('isWithinNetwork', () => {
  it('accepts a point on campus', () => {
    expect(isWithinNetwork(ON_CAMPUS, [route])).toBe(true);
  });

  it('rejects a point well outside the network', () => {
    expect(isWithinNetwork(OFF_CAMPUS, [route])).toBe(false);
  });

  it('accepts anything when no routes have loaded yet', () => {
    expect(isWithinNetwork(OFF_CAMPUS, [])).toBe(true);
  });
});

describe('useDeviceLocation', () => {
  it('moves the rider to a fix on campus', () => {
    stubGeolocation((success) =>
      success({ coords: ON_CAMPUS } as GeolocationPosition),
    );

    const { result } = renderHook(() => useDeviceLocation([route]));
    act(() => result.current.request());

    expect(useRiderStore.getState().position).toEqual(ON_CAMPUS);
    expect(useRiderStore.getState().source).toBe('device');
  });

  it('refuses a fix outside campus rather than making ETAs meaningless', () => {
    stubGeolocation((success) =>
      success({ coords: OFF_CAMPUS } as GeolocationPosition),
    );

    const { result } = renderHook(() => useDeviceLocation([route]));
    act(() => result.current.request());

    expect(useRiderStore.getState().position).toEqual(DEFAULT_RIDER);
    expect(useRiderStore.getState().locationError).toMatch(/off campus/i);
  });

  it('explains a denied permission', () => {
    stubGeolocation((_success, failure) =>
      failure({ code: 1, PERMISSION_DENIED: 1 } as GeolocationPositionError),
    );

    const { result } = renderHook(() => useDeviceLocation([route]));
    act(() => result.current.request());

    expect(useRiderStore.getState().locationError).toMatch(/permission denied/i);
  });

  it('explains a timeout', () => {
    stubGeolocation((_success, failure) =>
      failure({ code: 3, TIMEOUT: 3 } as GeolocationPositionError),
    );

    const { result } = renderHook(() => useDeviceLocation([route]));
    act(() => result.current.request());

    expect(useRiderStore.getState().locationError).toMatch(/too long/i);
  });

  it('explains an unsupported browser', () => {
    vi.stubGlobal('navigator', {});

    const { result } = renderHook(() => useDeviceLocation([route]));
    act(() => result.current.request());

    expect(useRiderStore.getState().locationError).toMatch(/cannot report a location/i);
  });
});
