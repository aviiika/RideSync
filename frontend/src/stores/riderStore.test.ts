import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { DEFAULT_RIDER, describeRiderSource, useRiderStore } from './riderStore';

const SJT = { latitude: 12.9699, longitude: 79.1606 };

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

describe('riderStore', () => {
  it('starts at the Main Gate', () => {
    expect(useRiderStore.getState().position).toEqual(DEFAULT_RIDER);
    expect(useRiderStore.getState().source).toBe('default');
  });

  it('moves the rider and records how it was set', () => {
    useRiderStore.getState().setPosition(SJT, 'picked');

    expect(useRiderStore.getState().position).toEqual(SJT);
    expect(useRiderStore.getState().source).toBe('picked');
  });

  it('leaves picking mode once a spot is chosen', () => {
    useRiderStore.getState().startPicking();
    expect(useRiderStore.getState().picking).toBe(true);

    useRiderStore.getState().setPosition(SJT, 'picked');
    expect(useRiderStore.getState().picking).toBe(false);
  });

  it('can cancel picking without moving', () => {
    useRiderStore.getState().startPicking();
    useRiderStore.getState().cancelPicking();

    expect(useRiderStore.getState().picking).toBe(false);
    expect(useRiderStore.getState().position).toEqual(DEFAULT_RIDER);
  });

  it('clears a stale error when the rider moves', () => {
    useRiderStore.getState().setLocationError('denied');
    useRiderStore.getState().setPosition(SJT, 'picked');

    expect(useRiderStore.getState().locationError).toBeNull();
  });

  it('returns to the Main Gate on reset', () => {
    useRiderStore.getState().setPosition(SJT, 'device');
    useRiderStore.getState().reset();

    expect(useRiderStore.getState().position).toEqual(DEFAULT_RIDER);
    expect(useRiderStore.getState().source).toBe('default');
  });

  it('remembers a chosen spot across reloads', () => {
    useRiderStore.getState().setPosition(SJT, 'picked');

    const stored = JSON.parse(localStorage.getItem('ridesync.rider') ?? '{}');
    expect(stored.latitude).toBe(SJT.latitude);
    expect(stored.source).toBe('picked');
  });

  it('forgets the spot once reset to the default', () => {
    useRiderStore.getState().setPosition(SJT, 'picked');
    useRiderStore.getState().reset();

    expect(localStorage.getItem('ridesync.rider')).toBeNull();
  });

  it('survives storage being unavailable', () => {
    vi.stubGlobal('localStorage', {
      getItem: () => {
        throw new Error('blocked');
      },
      setItem: () => {
        throw new Error('blocked');
      },
      removeItem: () => {
        throw new Error('blocked');
      },
    });

    expect(() => useRiderStore.getState().setPosition(SJT, 'picked')).not.toThrow();
    expect(useRiderStore.getState().position).toEqual(SJT);
  });
});

describe('describeRiderSource', () => {
  it.each([
    ['default', /main gate/i],
    ['picked', /custom location/i],
    ['device', /device location/i],
  ] as const)('describes %s', (source, expected) => {
    expect(describeRiderSource(source)).toMatch(expected);
  });
});
