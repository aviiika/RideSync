/**
 * Live shuttle state.
 *
 * Shuttles are stored normalised by id and replaced wholesale on each frame,
 * so a moving vehicle never causes a list to be rebuilt or reordered. The map
 * subscribes to this store imperatively rather than through React, which is
 * what keeps a 2 Hz telemetry feed from re-rendering the component tree.
 */

import { create } from 'zustand';

import type { Shuttle, SimulationState } from '../types/domain';
import type { ConnectionStatus } from '../types/ws';

/** Telemetry older than this is no longer presented as live. */
export const STALE_AFTER_MS = 10_000;

interface ShuttleStore {
  shuttles: Record<string, Shuttle>;
  /** Insertion order, kept separately so lists stay stable while positions change. */
  shuttleIds: string[];
  simulation: SimulationState | null;
  connection: ConnectionStatus;
  selectedShuttleId: string | null;
  /** Route the view is narrowed to, or null for the whole network. */
  routeFilter: string | null;
  /** Wall-clock time of the last telemetry frame. */
  lastUpdateAt: number | null;

  applyShuttles: (shuttles: Shuttle[]) => void;
  applySimulation: (state: SimulationState) => void;
  setConnection: (status: ConnectionStatus) => void;
  selectShuttle: (shuttleId: string | null) => void;
  setRouteFilter: (routeId: string | null) => void;
}

export const useShuttleStore = create<ShuttleStore>((set) => ({
  shuttles: {},
  shuttleIds: [],
  simulation: null,
  connection: 'connecting',
  selectedShuttleId: null,
  routeFilter: null,
  lastUpdateAt: null,

  applyShuttles: (incoming) =>
    set(() => {
      const shuttles: Record<string, Shuttle> = {};
      for (const shuttle of incoming) {
        shuttles[shuttle.id] = shuttle;
      }
      return {
        shuttles,
        shuttleIds: incoming.map((shuttle) => shuttle.id).sort(),
        lastUpdateAt: Date.now(),
      };
    }),

  applySimulation: (simulation) => set({ simulation }),

  setConnection: (connection) => set({ connection }),

  selectShuttle: (selectedShuttleId) => set({ selectedShuttleId }),

  // Narrowing to a route clears a selection that is no longer visible, so the
  // details panel can never describe a shuttle the map is not showing.
  setRouteFilter: (routeId) =>
    set((state) => {
      const selected = state.selectedShuttleId
        ? state.shuttles[state.selectedShuttleId]
        : undefined;
      const keepSelection = !routeId || (selected && selected.route_id === routeId);

      return {
        routeFilter: routeId,
        selectedShuttleId: keepSelection ? state.selectedShuttleId : null,
      };
    }),
}));

/** True when the last frame is old enough that positions should not be trusted. */
export function isTelemetryStale(lastUpdateAt: number | null, now: number = Date.now()): boolean {
  if (lastUpdateAt === null) {
    return false;
  }
  return now - lastUpdateAt > STALE_AFTER_MS;
}
