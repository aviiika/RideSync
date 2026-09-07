/** Shared test data, shaped exactly like the backend's responses. */

import type {
  EtaAccuracy,
  Route,
  Shuttle,
  ShuttleSnapshot,
  SimulationState,
} from '../types/domain';

export const route: Route = {
  id: 'ROUTE-AC',
  name: 'Academic Block Circuit',
  color: '#2563eb',
  average_speed_kmh: 22,
  loop_mode: 'LOOP',
  geometry: [
    [79.1578, 12.9698],
    [79.1587, 12.9709],
    [79.1578, 12.9698],
  ],
  stops: [
    {
      id: 'STOP-AC-01',
      name: 'Main Building',
      route_id: 'ROUTE-AC',
      sequence: 0,
      latitude: 12.9698,
      longitude: 79.1578,
    },
  ],
};

export const shuttle: Shuttle = {
  id: 'ROUTE-AC-01',
  route_id: 'ROUTE-AC',
  name: 'Academic Block Circuit 1',
  status: 'IN_SERVICE',
  latitude: 12.9701,
  longitude: 79.1564,
  heading: 47,
  speed_kmh: 22,
  progress: 0.31,
  occupancy: 0.4,
  next_stop_id: 'STOP-AC-03',
  next_stop_name: 'Anna Auditorium',
  updated_at: '2026-09-06T09:30:00Z',
};

export const snapshot: ShuttleSnapshot = {
  shuttle,
  route_name: 'Academic Block Circuit',
  route_color: '#2563eb',
  direct_distance_m: 1240,
  target_stop_id: 'STOP-AC-01',
  target_stop_name: 'Main Building',
  eta: {
    minutes: 4,
    seconds: 232.5,
    remaining_distance_m: 1420,
    effective_speed_kmh: 22,
    intervening_stops: 1,
    source: 'deterministic',
    confidence: {
      level: 'MEDIUM',
      label: 'Medium confidence',
      reason: 'A stop or two on the way could shift this by a minute.',
    },
  },
  recommendation: {
    level: 'WORTH_WAITING',
    label: 'Worth waiting',
    detail: 'A short wait at the stop.',
  },
  walk_seconds: 132,
  walk_minutes: 2,
  reachable: true,
};

export const etaAccuracy: EtaAccuracy = {
  resolved_predictions: 886,
  pending_predictions: 14,
  recorded_arrivals: 1004,
  mean_absolute_error_seconds: 19.1,
  mean_absolute_error_minutes: 0.32,
  median_absolute_error_seconds: 16.3,
  bias_seconds: 18.8,
  measured_against: 'simulated arrivals',
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
