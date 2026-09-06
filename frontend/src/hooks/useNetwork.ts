/** Server-state hooks. Components read data through these, never through `fetch`. */

import { useQuery } from '@tanstack/react-query';

import { api } from '../services/api';

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: api.health,
    // The health check doubles as the connectivity indicator, so keep it fresh.
    staleTime: 10_000,
    refetchInterval: 15_000,
  });
}

export function useRoutes() {
  return useQuery({
    queryKey: ['routes'],
    queryFn: api.listRoutes,
  });
}
