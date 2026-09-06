/** Application-wide providers, kept out of `App` so `App` stays presentational. */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

import { ApiError } from './services/api';

const MAX_RETRIES = 2;

// Not exported: the client is an implementation detail of this provider, and
// exporting a non-component from this file breaks React Fast Refresh.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: (failureCount, error) => {
        // A 404 is an answer, not an outage — retrying it just delays the error state.
        if (error instanceof ApiError && error.status === 404) {
          return false;
        }
        return failureCount < MAX_RETRIES;
      },
    },
  },
});

export function AppProviders({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
