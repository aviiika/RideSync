/** Server-state hooks. Components read data through these, never through `fetch`. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '../services/api';
import { useShuttleStore } from '../stores/shuttleStore';
import type { SimulationState } from '../types/domain';

/** How often rider-relative ETAs are recomputed. */
const NEARBY_REFRESH_MS = 3000;

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: api.health,
    // The health check doubles as the REST connectivity indicator.
    staleTime: 10_000,
    refetchInterval: 15_000,
  });
}

export function useRoutes() {
  return useQuery({
    queryKey: ['routes'],
    queryFn: api.listRoutes,
    // Route geometry is static for the life of the demo.
    staleTime: Infinity,
  });
}

/**
 * Shuttles ranked by arrival time at the rider's nearest stop.
 *
 * Polled rather than streamed: positions arrive over the WebSocket many times
 * a second, but an ETA in whole minutes does not change that often, and
 * recomputing it per frame would be wasted work.
 */
export function useNearbyShuttles(latitude: number, longitude: number) {
  return useQuery({
    queryKey: ['nearby', latitude, longitude],
    queryFn: () => api.nearbyShuttles(latitude, longitude),
    refetchInterval: NEARBY_REFRESH_MS,
    staleTime: NEARBY_REFRESH_MS,
  });
}

/**
 * Demo controls.
 *
 * The server's response is written straight into the store so the controls
 * reflect the true state immediately, without waiting for the next broadcast.
 */
export function useSimulationControls() {
  const queryClient = useQueryClient();
  const applySimulation = useShuttleStore((state) => state.applySimulation);

  const mutation = (action: () => Promise<SimulationState>) => ({
    mutationFn: action,
    onSuccess: (state: SimulationState) => {
      applySimulation(state);
      void queryClient.invalidateQueries({ queryKey: ['nearby'] });
    },
  });

  return {
    start: useMutation(mutation(api.simulation.start)),
    pause: useMutation(mutation(api.simulation.pause)),
    reset: useMutation(mutation(api.simulation.reset)),
    setSpeed: useMutation({
      mutationFn: api.simulation.setSpeed,
      onSuccess: (state: SimulationState) => applySimulation(state),
    }),
  };
}
