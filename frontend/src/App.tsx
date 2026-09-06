/**
 * Application shell.
 *
 * Map-first: the map owns the screen and the panel is secondary. This
 * component composes and renders — every number it shows was calculated by the
 * backend, and no business logic lives here.
 */

import { AlertTriangle, Bus, Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';

import { ConnectionBanner } from './components/common/ConnectionBanner';
import { ShuttleMap } from './components/map/ShuttleMap';
import { SimulationControls } from './components/simulation/SimulationControls';
import { NearestShuttleCard } from './components/shuttle/NearestShuttleCard';
import { ShuttleDetailsPanel } from './components/shuttle/ShuttleDetailsPanel';
import { EtaBadge } from './components/shuttle/EtaBadge';
import { useNearbyShuttles, useRoutes } from './hooks/useNetwork';
import { useShuttleStream } from './hooks/useShuttleStream';
import { isTelemetryStale, useShuttleStore } from './stores/shuttleStore';
import { formatDistance } from './utils/format';

/**
 * The rider's position.
 *
 * Fixed at the campus Main Gate for the demo. Real geolocation is a browser
 * permission prompt away, but a pitch should not open with a dialog, and a
 * fixed position keeps the run repeatable.
 */
const RIDER = { latitude: 12.9695, longitude: 79.1559 };

export function App() {
  useShuttleStream();

  const routes = useRoutes();
  const nearby = useNearbyShuttles(RIDER.latitude, RIDER.longitude);

  const connection = useShuttleStore((state) => state.connection);
  const simulation = useShuttleStore((state) => state.simulation);
  const lastUpdateAt = useShuttleStore((state) => state.lastUpdateAt);
  const selectedId = useShuttleStore((state) => state.selectedShuttleId);
  const selectShuttle = useShuttleStore((state) => state.selectShuttle);
  const liveShuttle = useShuttleStore((state) =>
    selectedId ? state.shuttles[selectedId] : undefined,
  );

  const stale = useStaleTelemetry(lastUpdateAt);

  const snapshots = nearby.data ?? [];
  const nearest = snapshots[0];
  const selectedSnapshot = snapshots.find((item) => item.shuttle.id === selectedId);

  return (
    <div className="flex h-full flex-col">
      <Header />

      <main className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <section className="relative min-h-[50vh] flex-1" aria-label="Live shuttle map">
          {routes.isPending ? (
            <div className="flex h-full items-center justify-center bg-surface-muted">
              <p className="flex items-center gap-2 text-sm text-muted">
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                Loading the route network…
              </p>
            </div>
          ) : routes.isError ? (
            <MapUnavailable message={routes.error.message} />
          ) : (
            <ShuttleMap
              routes={routes.data ?? []}
              user={RIDER}
              onSelectShuttle={selectShuttle}
            />
          )}
        </section>

        <aside className="flex w-full shrink-0 flex-col gap-3 overflow-y-auto border-t border-border bg-surface-muted p-4 lg:w-[24rem] lg:border-l lg:border-t-0">
          <ConnectionBanner status={connection} stale={stale} />

          {selectedId ? (
            <ShuttleDetailsPanel
              live={liveShuttle}
              snapshot={selectedSnapshot}
              onClose={() => selectShuttle(null)}
            />
          ) : nearby.isPending ? (
            <p className="flex items-center gap-2 rounded-panel border border-border bg-surface p-4 text-sm text-muted">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              Finding your next shuttle…
            </p>
          ) : nearby.isError ? (
            <ErrorCard title="Could not load shuttles" detail={nearby.error.message} />
          ) : nearest ? (
            <NearestShuttleCard snapshot={nearest} onSelect={selectShuttle} />
          ) : (
            <p className="rounded-panel border border-border bg-surface p-4 text-sm text-muted">
              No shuttles are in service near you right now.
            </p>
          )}

          <SimulationControls state={simulation} />

          {snapshots.length > 1 ? (
            <section className="rounded-panel border border-border bg-surface p-3">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-muted">
                Other shuttles
              </h2>
              <ul className="mt-2 flex flex-col divide-y divide-border">
                {snapshots.slice(1).map((snapshot) => (
                  <li key={snapshot.shuttle.id}>
                    <button
                      type="button"
                      onClick={() => selectShuttle(snapshot.shuttle.id)}
                      className="flex w-full items-center justify-between gap-3 py-2.5 text-left transition hover:opacity-70"
                    >
                      <span className="flex min-w-0 items-center gap-2">
                        <span
                          className="h-2 w-2 shrink-0 rounded-full"
                          style={{ backgroundColor: snapshot.route_color }}
                          aria-hidden="true"
                        />
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-medium">
                            {snapshot.shuttle.name}
                          </span>
                          <span className="block truncate text-xs text-muted">
                            {formatDistance(snapshot.direct_distance_m)} away
                          </span>
                        </span>
                      </span>
                      <EtaBadge eta={snapshot.eta} size="small" />
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <p className="px-1 pb-1 text-xs text-muted">
            Telemetry is simulated, not real GPS. The architecture is built so a real fleet
            feed can replace it without changing this interface.
          </p>
        </aside>
      </main>
    </div>
  );
}

function Header() {
  return (
    <header className="flex items-center justify-between gap-4 border-b border-border bg-surface px-4 py-3">
      <div className="flex items-center gap-2">
        <Bus className="h-5 w-5 text-brand" aria-hidden="true" />
        <div>
          <h1 className="text-base font-semibold leading-tight">RideSync</h1>
          <p className="text-xs text-muted">Real-time shuttle tracking &amp; ETA simulation</p>
        </div>
      </div>
    </header>
  );
}

function MapUnavailable({ message }: { message: string }) {
  return (
    <div className="flex h-full items-center justify-center bg-surface-muted p-6">
      <div className="max-w-sm text-center">
        <AlertTriangle className="mx-auto h-6 w-6 text-critical" aria-hidden="true" />
        <p className="mt-2 font-medium">The map could not load</p>
        <p className="mt-1 text-sm text-muted">{message}</p>
      </div>
    </div>
  );
}

function ErrorCard({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="flex items-start gap-2 rounded-panel bg-critical/10 p-3 text-sm text-critical">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <div>
        <p className="font-medium">{title}</p>
        <p className="opacity-80">{detail}</p>
      </div>
    </div>
  );
}

/**
 * Re-evaluate staleness on a timer.
 *
 * Without this the banner would only appear when a frame arrives — which is
 * precisely what stops happening when the feed goes stale.
 */
function useStaleTelemetry(lastUpdateAt: number | null): boolean {
  const [stale, setStale] = useState(false);

  useEffect(() => {
    const check = () => setStale(isTelemetryStale(lastUpdateAt));
    check();

    const timer = setInterval(check, 2000);
    return () => clearInterval(timer);
  }, [lastUpdateAt]);

  return stale;
}
