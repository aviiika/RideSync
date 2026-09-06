/**
 * Application shell.
 *
 * Map-first layout: the map owns the screen and the panel is secondary. This
 * component composes and renders — every calculation it displays is performed
 * by the backend or by a hook, never inline here.
 */

import { AlertTriangle, Bus, Loader2, MapPin } from 'lucide-react';

import { StatusDot } from './components/common/StatusDot';
import { useHealth, useRoutes } from './hooks/useNetwork';

export function App() {
  const health = useHealth();
  const routes = useRoutes();

  return (
    <div className="flex h-full flex-col">
      <Header connected={health.isSuccess} connecting={health.isPending} />

      <main className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <section
          className="relative flex min-h-[45vh] flex-1 items-center justify-center bg-[#dfe5ee]"
          aria-label="Map"
        >
          <p className="max-w-xs text-center text-sm text-muted">
            The interactive map arrives in the next phase. Routes and stops are already
            being served by the API.
          </p>
        </section>

        <aside className="flex w-full shrink-0 flex-col gap-3 border-t border-border bg-surface p-4 lg:w-96 lg:border-l lg:border-t-0">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted">Routes</h2>
          <RoutePanel
            loading={routes.isPending}
            error={routes.isError ? routes.error : null}
            routes={routes.data ?? []}
          />
        </aside>
      </main>
    </div>
  );
}

function Header({ connected, connecting }: { connected: boolean; connecting: boolean }) {
  return (
    <header className="flex items-center justify-between gap-4 border-b border-border bg-surface px-4 py-3">
      <div className="flex items-center gap-2">
        <Bus className="h-5 w-5 text-brand" aria-hidden="true" />
        <div>
          <h1 className="text-base font-semibold leading-tight">RideSync</h1>
          <p className="text-xs text-muted">Shuttle tracking &amp; ETA simulation</p>
        </div>
      </div>

      {connecting ? (
        <StatusDot tone="muted">Connecting…</StatusDot>
      ) : connected ? (
        <StatusDot tone="positive">Service online</StatusDot>
      ) : (
        <StatusDot tone="critical">Service unavailable</StatusDot>
      )}
    </header>
  );
}

interface RoutePanelProps {
  loading: boolean;
  error: Error | null;
  routes: { id: string; name: string; color: string; stops: unknown[] }[];
}

function RoutePanel({ loading, error, routes }: RoutePanelProps) {
  if (loading) {
    return (
      <p className="flex items-center gap-2 text-sm text-muted">
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        Loading routes…
      </p>
    );
  }

  if (error) {
    return (
      <div className="flex items-start gap-2 rounded-lg bg-critical/10 p-3 text-sm text-critical">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        <div>
          <p className="font-medium">Could not load routes</p>
          <p className="text-critical/80">{error.message}</p>
        </div>
      </div>
    );
  }

  if (routes.length === 0) {
    return <p className="text-sm text-muted">No routes are configured.</p>;
  }

  return (
    <ul className="flex flex-col gap-2">
      {routes.map((route) => (
        <li
          key={route.id}
          className="flex items-center gap-3 rounded-panel border border-border p-3"
        >
          <span
            className="h-8 w-1.5 shrink-0 rounded-full"
            style={{ backgroundColor: route.color }}
            aria-hidden="true"
          />
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{route.name}</p>
            <p className="flex items-center gap-1 text-xs text-muted">
              <MapPin className="h-3 w-3" aria-hidden="true" />
              {route.stops.length} stops
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}
