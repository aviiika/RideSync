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

export interface Health {
  status: string;
  version: string;
  routes_loaded: number;
}
