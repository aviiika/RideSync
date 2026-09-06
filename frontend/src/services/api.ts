/**
 * REST client.
 *
 * Thin and typed on purpose: it performs requests and surfaces failures as
 * `ApiError`. It holds no business logic and no caching — TanStack Query owns
 * server state, and the WebSocket owns live positions.
 */

import { env } from '../config/env';
import type {
  EtaAccuracy,
  Health,
  Route,
  Session,
  Shuttle,
  ShuttleSnapshot,
  SimulationState,
  Stop,
} from '../types/domain';

/** A request that did not return a usable response. */
export class ApiError extends Error {
  /** HTTP status, or `undefined` when the request never reached the server. */
  readonly status: number | undefined;

  constructor(message: string, status?: number, options?: ErrorOptions) {
    super(message, options);
    this.name = 'ApiError';
    this.status = status;
  }

  /** True when the backend could not be reached at all. */
  get isOffline(): boolean {
    return this.status === undefined;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${env.apiUrl}${path}`, init);
  } catch (cause) {
    // Network-level failure: the backend is down, unreachable or blocked.
    throw new ApiError(`Cannot reach the shuttle service at ${env.apiUrl}`, undefined, { cause });
  }

  if (!response.ok) {
    // Prefer the server's own message: it is written for the user, whereas a
    // status code is not.
    const detail = await readDetail(response);
    throw new ApiError(
      detail ?? `Request to ${path} failed (${response.status})`,
      response.status,
    );
  }

  return (await response.json()) as T;
}

function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

function riderQuery(latitude: number, longitude: number): string {
  return `latitude=${latitude}&longitude=${longitude}`;
}

/** Pull `detail` out of a FastAPI error body, if there is one. */
async function readDetail(response: Response): Promise<string | null> {
  try {
    const body = (await response.clone().json()) as { detail?: unknown };
    return typeof body.detail === 'string' ? body.detail : null;
  } catch {
    return null;
  }
}

export const api = {
  login: (registrationNumber: string, password: string) =>
    post<Session>('/auth/login', {
      registration_number: registrationNumber,
      password,
    }),

  health: () => request<Health>('/health'),
  listRoutes: () => request<Route[]>('/routes'),
  getRoute: (routeId: string) => request<Route>(`/routes/${encodeURIComponent(routeId)}`),
  listStops: (routeId?: string) =>
    request<Stop[]>(routeId ? `/stops?route_id=${encodeURIComponent(routeId)}` : '/stops'),

  /** Shuttles ranked by when they reach the rider — soonest first, not nearest first. */
  nearbyShuttles: (latitude: number, longitude: number) =>
    request<ShuttleSnapshot[]>(`/shuttles/nearby?${riderQuery(latitude, longitude)}`),

  /** A departure board: what is due at one stop, soonest first. */
  arrivalsAt: (stopId: string, latitude?: number, longitude?: number) => {
    const path = `/stops/${encodeURIComponent(stopId)}/arrivals`;
    const query =
      latitude !== undefined && longitude !== undefined
        ? `?${riderQuery(latitude, longitude)}`
        : '';
    return request<ShuttleSnapshot[]>(`${path}${query}`);
  },

  /** Measured ETA error. Against the simulation, and it says so. */
  etaAccuracy: () => request<EtaAccuracy>('/metrics/eta'),

  simulation: {
    state: () => request<SimulationState>('/simulation'),
    start: () => post<SimulationState>('/simulation/start'),
    pause: () => post<SimulationState>('/simulation/pause'),
    reset: () => post<SimulationState>('/simulation/reset'),
    setSpeed: (multiplier: number) => post<SimulationState>('/simulation/speed', { multiplier }),
    delay: (shuttleId: string, seconds = 90) =>
      post<Shuttle>('/simulation/delay', { shuttle_id: shuttleId, seconds }),
    clearDelays: () => post<SimulationState>('/simulation/clear-delays'),
  },
};
