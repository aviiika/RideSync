/**
 * Domain types mirroring the backend's Pydantic schemas.
 *
 * The backend is the authoritative source of shuttle state; these types
 * describe what it sends, never what the frontend invents.
 */

/** How a shuttle behaves once it reaches the end of its route geometry. */
export type LoopMode = 'LOOP' | 'REVERSE';

/** A GeoJSON position: `[longitude, latitude]` — the order MapLibre expects. */
export type Position = [longitude: number, latitude: number];

/** A point, in the (latitude, longitude) order the API uses. */
export interface Coordinate {
  latitude: number;
  longitude: number;
}

export type ShuttleStatus =
  | 'IN_SERVICE'
  | 'ARRIVING'
  | 'AT_STOP'
  | 'DELAYED'
  | 'OUT_OF_SERVICE'
  | 'STALE';

export type RecommendationLevel =
  | 'ARRIVING_SOON'
  | 'WORTH_WAITING'
  | 'CONSIDER_WAITING'
  | 'LONG_WAIT'
  | 'TOO_TIGHT'
  | 'UNAVAILABLE';

export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW';

/** A heuristic band, deliberately not a probability. */
export interface Confidence {
  level: ConfidenceLevel;
  label: string;
  reason: string;
}

export interface Stop {
  id: string;
  name: string;
  route_id: string;
  sequence: number;
  latitude: number;
  longitude: number;
}

export interface Route {
  id: string;
  name: string;
  color: string;
  average_speed_kmh: number;
  loop_mode: LoopMode;
  geometry: Position[];
  stops: Stop[];
}

export interface Shuttle {
  id: string;
  route_id: string;
  name: string;
  status: ShuttleStatus;
  latitude: number;
  longitude: number;
  heading: number;
  speed_kmh: number;
  progress: number;
  occupancy: number;
  next_stop_id: string | null;
  next_stop_name: string | null;
  updated_at: string;
}

export interface Eta {
  minutes: number;
  seconds: number;
  remaining_distance_m: number;
  effective_speed_kmh: number;
  intervening_stops: number;
  /** Which estimator produced this — shown so the demo never overclaims. */
  source: string;
  confidence: Confidence | null;
}

export interface Recommendation {
  level: RecommendationLevel;
  label: string;
  detail: string;
}

/** A shuttle described relative to the rider: distance, ETA and advice. */
export interface ShuttleSnapshot {
  shuttle: Shuttle;
  route_name: string;
  route_color: string;
  /** Straight-line distance — deliberately not the travel distance. */
  direct_distance_m: number;
  target_stop_id: string | null;
  target_stop_name: string | null;
  eta: Eta | null;
  recommendation: Recommendation;
  /** Time on foot from the rider to the target stop. */
  walk_seconds: number | null;
  walk_minutes: number | null;
  /** False when the shuttle arrives before the rider could get there. */
  reachable: boolean | null;
}

/** Measured error of the ETA engine, against simulated arrivals. */
export interface EtaAccuracy {
  resolved_predictions: number;
  pending_predictions: number;
  recorded_arrivals: number;
  mean_absolute_error_seconds: number | null;
  mean_absolute_error_minutes: number | null;
  median_absolute_error_seconds: number | null;
  bias_seconds: number | null;
  /** What the error was measured against. Never real-world GPS. */
  measured_against: string;
}

export interface SimulationState {
  running: boolean;
  speed_multiplier: number;
  elapsed_seconds: number;
  tick_count: number;
  started_at: string | null;
  shuttle_count: number;
  seed: number;
}

/** A signed-in student. The token is signed and expiring, server-side. */
export interface Session {
  registration_number: string;
  token: string;
  expires_at: string;
}

export interface Health {
  status: string;
  version: string;
  routes_loaded: number;
}
