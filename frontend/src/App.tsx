/**
 * Application shell.
 *
 * Map-first: the map owns the screen and the panel is secondary. This
 * component composes and renders — every number it shows was calculated by the
 * backend, and no business logic lives here.
 */

import { AlertTriangle, Bus, ChevronDown, Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';

import { ConnectionBanner } from './components/common/ConnectionBanner';
import { ShuttleMap } from './components/map/ShuttleMap';
import { SimulationControls } from './components/simulation/SimulationControls';
import { LocationSearch } from './components/shuttle/LocationSearch';
import { NearestShuttleCard } from './components/shuttle/NearestShuttleCard';
import { StopBoard } from './components/shuttle/StopBoard';
import { ShuttleDetailsPanel } from './components/shuttle/ShuttleDetailsPanel';
import { EtaBadge } from './components/shuttle/EtaBadge';
import {
  useEtaAccuracy,
  useNearbyShuttles,
  useRoutes,
  useSimulationControls,
  useStopArrivals,
} from './hooks/useNetwork';
import { useShuttleStream } from './hooks/useShuttleStream';
import { isTelemetryStale, useShuttleStore } from './stores/shuttleStore';
import type { ShuttleSnapshot } from './types/domain';
import { describeRiderSource, useRiderStore } from './stores/riderStore';
import type { ConnectionStatus } from './types/ws';
import { formatDistance } from './utils/format';

/**
 * Where "nearby" stops and "further away" begins.
 *
 * Roughly five minutes on foot: close enough that walking to meet the shuttle
 * is a real option.
 */
const NEAR_DISTANCE_M = 400;

export function App() {
  useShuttleStream();

  // The rider starts at the Main Gate and can be moved from the map. A pitch
  // should not open with a permission dialog, so the device is never asked
  // unless someone presses the button.
  const rider = useRiderStore((state) => state.position);
  const riderSource = useRiderStore((state) => state.source);
  const riderPlace = useRiderStore((state) => state.placeName);
  const setRiderPosition = useRiderStore((state) => state.setPosition);

  const routes = useRoutes();
  const nearby = useNearbyShuttles(rider.latitude, rider.longitude);

  const connection = useShuttleStore((state) => state.connection);
  const simulation = useShuttleStore((state) => state.simulation);
  const lastUpdateAt = useShuttleStore((state) => state.lastUpdateAt);
  const selectedId = useShuttleStore((state) => state.selectedShuttleId);
  const selectShuttle = useShuttleStore((state) => state.selectShuttle);
  const selectedStopId = useShuttleStore((state) => state.selectedStopId);
  const selectStop = useShuttleStore((state) => state.selectStop);
  const routeFilter = useShuttleStore((state) => state.routeFilter);
  const setRouteFilter = useShuttleStore((state) => state.setRouteFilter);
  const liveShuttle = useShuttleStore((state) =>
    selectedId ? state.shuttles[selectedId] : undefined,
  );

  const arrivals = useStopArrivals(selectedStopId, rider.latitude, rider.longitude);
  const accuracy = useEtaAccuracy();
  const { delay } = useSimulationControls();

  const stale = useStaleTelemetry(lastUpdateAt);
  const [sheetOpen, setSheetOpen] = useState(true);

  // The panel honours the same filter as the map: isolating a route must not
  // leave the list advertising a shuttle that is no longer drawn.
  const snapshots = (nearby.data ?? []).filter(
    (item) => !routeFilter || item.shuttle.route_id === routeFilter,
  );
  const nearest = snapshots[0];
  const stops = (routes.data ?? []).flatMap((route) => route.stops);

  // Grouped by how far the shuttle is, ordered by when it arrives. Distance is
  // what a rider glances at; arrival is what actually decides the answer, so
  // the grouping never reorders within a group.
  const others = snapshots.slice(1);
  const closeBy = others.filter((item) => item.direct_distance_m <= NEAR_DISTANCE_M);
  const faraway = others.filter((item) => item.direct_distance_m > NEAR_DISTANCE_M);
  const selectedSnapshot = snapshots.find((item) => item.shuttle.id === selectedId);

  return (
    <div className="flex h-full flex-col">
      <Header
        connection={connection}
        shuttleCount={simulation?.shuttle_count ?? null}
        running={simulation?.running ?? false}
      />

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
              user={rider}
              routeFilter={routeFilter}
              onSelectShuttle={selectShuttle}
              onSelectStop={selectStop}
              onChangeRouteFilter={setRouteFilter}
            />
          )}
        </section>

        <aside className="flex w-full shrink-0 flex-col gap-3 overflow-y-auto border-t border-border bg-surface-muted p-4 lg:max-h-none lg:w-[24rem] lg:border-l lg:border-t-0">
          <button
            type="button"
            onClick={() => setSheetOpen((open) => !open)}
            aria-expanded={sheetOpen}
            className="-mt-1 flex items-center justify-between gap-2 text-left lg:hidden"
          >
            <span className="text-xs font-semibold uppercase tracking-wide text-muted">
              {sheetOpen ? 'Hide details' : nearestSummary(nearest)}
            </span>
            <ChevronDown
              className={`h-4 w-4 shrink-0 text-muted transition-transform ${
                sheetOpen ? '' : 'rotate-180'
              }`}
              aria-hidden="true"
            />
          </button>

          <div className={sheetOpen ? 'contents' : 'hidden lg:contents'}>
              <ConnectionBanner status={connection} stale={stale} />

            <LocationSearch
              stops={stops}
              currentLabel={describeRiderSource(riderSource, riderPlace)}
              onPick={(stop) =>
                setRiderPosition(
                  { latitude: stop.latitude, longitude: stop.longitude },
                  'place',
                  stop.name,
                )
              }
            />

            {selectedStopId ? (
              <StopBoard
                stop={stops.find((stop) => stop.id === selectedStopId)}
                arrivals={arrivals.data ?? []}
                loading={arrivals.isPending}
                error={arrivals.isError ? arrivals.error : null}
                onSelectShuttle={selectShuttle}
                onClose={() => selectStop(null)}
              />
            ) : selectedId ? (
              <ShuttleDetailsPanel
                live={liveShuttle}
                snapshot={selectedSnapshot}
                onClose={() => selectShuttle(null)}
                onInjectDelay={(shuttleId) => delay.mutate(shuttleId)}
                delaying={delay.isPending}
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

            {accuracy.data && accuracy.data.resolved_predictions > 0 ? (
              <p className="rounded-panel border border-border bg-surface p-3 text-xs text-muted">
                <span className="font-medium text-ink">
                  ETA off by ~{formatErrorMinutes(accuracy.data.mean_absolute_error_seconds)} on
                  average
                </span>{' '}
                over {accuracy.data.resolved_predictions} predictions scored against{' '}
                {accuracy.data.measured_against}. Not a real-world accuracy claim.
              </p>
            ) : null}

            <ShuttleGroup
              title={`Nearby · within ${NEAR_DISTANCE_M} m`}
              snapshots={closeBy}
              onSelect={selectShuttle}
              emptyLabel="No shuttle is close to you right now."
            />

            <ShuttleGroup
              title="Further away"
              snapshots={faraway}
              onSelect={selectShuttle}
            />

            <p className="px-1 pb-1 text-xs text-muted">
                Telemetry is simulated, not real GPS. The architecture is built so a real fleet
                feed can replace it without changing this interface.
              </p>
          </div>
        </aside>
      </main>
    </div>
  );
}

/**
 * A group of shuttles in the panel: near, or far.
 *
 * Renders nothing at all when empty unless given a label to show, so an
 * absent group never leaves a bare heading behind.
 */
function ShuttleGroup({
  title,
  snapshots,
  onSelect,
  emptyLabel,
}: {
  title: string;
  snapshots: ShuttleSnapshot[];
  onSelect: (shuttleId: string) => void;
  emptyLabel?: string;
}) {
  if (snapshots.length === 0 && !emptyLabel) {
    return null;
  }

  return (
    <section className="rounded-panel border border-border bg-surface p-3">
      <h2 className="flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-muted">
        <span>{title}</span>
        {snapshots.length > 0 ? <span>{snapshots.length}</span> : null}
      </h2>

      {snapshots.length === 0 ? (
        <p className="mt-2 text-sm text-muted">{emptyLabel}</p>
      ) : (
        <ul className="mt-2 flex flex-col divide-y divide-border">
          {snapshots.map((snapshot) => (
            <li key={snapshot.shuttle.id}>
              <button
                type="button"
                onClick={() => onSelect(snapshot.shuttle.id)}
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
                      {snapshot.shuttle.status === 'DELAYED' ? ' · running late' : ''}
                    </span>
                  </span>
                </span>
                <EtaBadge eta={snapshot.eta} size="small" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** Error in the units a person reads: seconds while small, minutes once not. */
function formatErrorMinutes(seconds: number | null): string {
  if (seconds === null) {
    return '—';
  }
  return seconds < 90 ? `${Math.round(seconds)} s` : `${(seconds / 60).toFixed(1)} min`;
}

/** One line for the collapsed mobile sheet: the answer, without the detail. */
function nearestSummary(nearest: { shuttle: { name: string }; eta: { minutes: number } | null } | undefined): string {
  if (!nearest) {
    return 'No shuttles nearby';
  }
  if (!nearest.eta) {
    return `${nearest.shuttle.name} · ETA unavailable`;
  }
  if (nearest.eta.minutes < 1) {
    return `${nearest.shuttle.name} · arriving now`;
  }
  return `${nearest.shuttle.name} · ~${nearest.eta.minutes} min`;
}

function Header({
  connection,
  shuttleCount,
  running,
}: {
  connection: ConnectionStatus;
  shuttleCount: number | null;
  running: boolean;
}) {
  const live = connection === 'connected';

  return (
    <header className="flex items-center justify-between gap-4 border-b border-border bg-surface px-4 py-3">
      <div className="flex items-center gap-2">
        <Bus className="h-5 w-5 text-brand" aria-hidden="true" />
        <div>
          <h1 className="text-base font-semibold leading-tight">RideSync</h1>
          <p className="text-xs text-muted">VIT Vellore campus shuttle &middot; live ETA</p>
        </div>
      </div>

      {shuttleCount !== null ? (
        <p className="flex items-center gap-2 text-xs text-muted" role="status">
          <span
            className={`h-2 w-2 rounded-full ${
              live && running ? 'animate-pulse bg-positive' : 'bg-muted'
            }`}
            aria-hidden="true"
          />
          {shuttleCount} shuttles {running ? 'in service' : 'paused'}
        </p>
      ) : null}
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
