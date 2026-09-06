/** Shared test data, shaped exactly like the backend's responses. */

import type { Route, Shuttle, ShuttleSnapshot, SimulationState } from '../types/domain';

export const route: Route = {
  id: 'ROUTE-A',
  name: 'Main Campus Loop',
  color: '#2563eb',
  average_speed_kmh: 22,
  loop_mode: 'LOOP',
  geometry: [
    [79.1559, 12.9695],
    [79.157, 12.9708],
    [79.1559, 12.9695],
  ],
  stops: [
    {
      id: 'STOP-A1',
      name: 'Main Gate',
      route_id: 'ROUTE-A',
      sequence: 0,
      latitude: 12.9695,
      longitude: 79.1559,
    },
  ],
};

export const shuttle: Shuttle = {
  id: 'ROUTE-A-01',
  route_id: 'ROUTE-A',
  name: 'Main Campus Loop 1',
  status: 'IN_SERVICE',
  latitude: 12.9701,
  longitude: 79.1564,
  heading: 47,
  speed_kmh: 22,
  progress: 0.31,
  occupancy: 0.4,
  next_stop_id: 'STOP-A2',
  next_stop_name: 'Academic Block 1',
  updated_at: '2026-09-06T09:30:00Z',
};

export const snapshot: ShuttleSnapshot = {
  shuttle,
  route_name: 'Main Campus Loop',
  route_color: '#2563eb',
  direct_distance_m: 1240,
  target_stop_id: 'STOP-A1',
  target_stop_name: 'Main Gate',
  eta: {
    minutes: 4,
    seconds: 232.5,
    remaining_distance_m: 1420,
    effective_speed_kmh: 22,
    intervening_stops: 1,
    source: 'deterministic',
  },
  recommendation: {
    level: 'WORTH_WAITING',
    label: 'Worth waiting',
    detail: 'A short wait at the stop.',
  },
};

export const simulationState: SimulationState = {
  running: true,
  speed_multiplier: 1,
  elapsed_seconds: 42,
  tick_count: 84,
  started_at: '2026-09-06T09:29:00Z',
  shuttle_count: 6,
  seed: 42,
};
