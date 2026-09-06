/**
 * REST client.
 *
 * Thin and typed on purpose: it performs requests and surfaces failures as
 * `ApiError`. It holds no business logic and no caching — TanStack Query owns
 * server state.
 */

import { env } from '../config/env';
import type { Health, Route, Stop } from '../types/domain';

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

async function request<T>(path: string): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${env.apiUrl}${path}`);
  } catch (cause) {
    // Network-level failure: the backend is down, unreachable or blocked.
    throw new ApiError(`Cannot reach the shuttle service at ${env.apiUrl}`, undefined, { cause });
  }

  if (!response.ok) {
    throw new ApiError(`Request to ${path} failed (${response.status})`, response.status);
  }

  return (await response.json()) as T;
}

export const api = {
  health: () => request<Health>('/health'),
  listRoutes: () => request<Route[]>('/routes'),
  getRoute: (routeId: string) => request<Route>(`/routes/${encodeURIComponent(routeId)}`),
  listStops: (routeId?: string) =>
    request<Stop[]>(routeId ? `/stops?route_id=${encodeURIComponent(routeId)}` : '/stops'),
};
