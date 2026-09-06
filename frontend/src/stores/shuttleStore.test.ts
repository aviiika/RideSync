import { beforeEach, describe, expect, it } from 'vitest';

import { shuttle } from '../test/fixtures';
import { STALE_AFTER_MS, isTelemetryStale, useShuttleStore } from './shuttleStore';

beforeEach(() => {
  useShuttleStore.setState({
    shuttles: {},
    shuttleIds: [],
    simulation: null,
    connection: 'connecting',
    selectedShuttleId: null,
    routeFilter: null,
    lastUpdateAt: null,
  });
});

describe('shuttleStore', () => {
  it('normalises shuttles by id', () => {
    useShuttleStore.getState().applyShuttles([shuttle]);

    const state = useShuttleStore.getState();
    expect(state.shuttles[shuttle.id]).toEqual(shuttle);
    expect(state.shuttleIds).toEqual([shuttle.id]);
  });

  it('replaces state on each frame rather than accumulating', () => {
    const store = useShuttleStore.getState();
    store.applyShuttles([shuttle, { ...shuttle, id: 'OTHER' }]);
    store.applyShuttles([shuttle]);

    expect(useShuttleStore.getState().shuttleIds).toEqual([shuttle.id]);
  });

  it('keeps ids in a stable order while positions change', () => {
    const store = useShuttleStore.getState();
    store.applyShuttles([{ ...shuttle, id: 'B' }, { ...shuttle, id: 'A' }]);
    const first = useShuttleStore.getState().shuttleIds;

    store.applyShuttles([{ ...shuttle, id: 'A' }, { ...shuttle, id: 'B' }]);
    expect(useShuttleStore.getState().shuttleIds).toEqual(first);
  });

  it('records when telemetry last arrived', () => {
    expect(useShuttleStore.getState().lastUpdateAt).toBeNull();
    useShuttleStore.getState().applyShuttles([shuttle]);
    expect(useShuttleStore.getState().lastUpdateAt).toBeGreaterThan(0);
  });

  it('tracks selection', () => {
    useShuttleStore.getState().selectShuttle(shuttle.id);
    expect(useShuttleStore.getState().selectedShuttleId).toBe(shuttle.id);

    useShuttleStore.getState().selectShuttle(null);
    expect(useShuttleStore.getState().selectedShuttleId).toBeNull();
  });
});

describe('isTelemetryStale', () => {
  it('is not stale before any frame has arrived', () => {
    expect(isTelemetryStale(null)).toBe(false);
  });

  it('is fresh immediately after a frame', () => {
    const now = 1_000_000;
    expect(isTelemetryStale(now, now + 500)).toBe(false);
  });

  it('goes stale once frames stop arriving', () => {
    const now = 1_000_000;
    expect(isTelemetryStale(now, now + STALE_AFTER_MS + 1)).toBe(true);
  });
});

describe('route filter', () => {
  it('narrows to one route', () => {
    useShuttleStore.getState().setRouteFilter('ROUTE-B');
    expect(useShuttleStore.getState().routeFilter).toBe('ROUTE-B');
  });

  it('keeps a selection that is still on the visible route', () => {
    const store = useShuttleStore.getState();
    store.applyShuttles([shuttle]);
    store.selectShuttle(shuttle.id);

    useShuttleStore.getState().setRouteFilter(shuttle.route_id);
    expect(useShuttleStore.getState().selectedShuttleId).toBe(shuttle.id);
  });

  it('drops a selection the filter would hide', () => {
    const store = useShuttleStore.getState();
    store.applyShuttles([shuttle]);
    store.selectShuttle(shuttle.id);

    useShuttleStore.getState().setRouteFilter('ROUTE-Z');
    expect(useShuttleStore.getState().selectedShuttleId).toBeNull();
  });

  it('keeps the selection when the filter is cleared', () => {
    const store = useShuttleStore.getState();
    store.applyShuttles([shuttle]);
    store.selectShuttle(shuttle.id);

    useShuttleStore.getState().setRouteFilter(null);
    expect(useShuttleStore.getState().selectedShuttleId).toBe(shuttle.id);
  });
});
