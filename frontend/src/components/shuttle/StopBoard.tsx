/**
 * A departure board for one stop.
 *
 * This is the question a rider standing at a stop actually asks, and it is not
 * the same as "what is near me": only shuttles whose route calls here can ever
 * arrive, however close anything else happens to be.
 */

import { AlertTriangle, Loader2, X } from 'lucide-react';

import type { ShuttleSnapshot, Stop } from '../../types/domain';
import { formatDistance } from '../../utils/format';
import { EtaBadge } from './EtaBadge';
import { RecommendationPill } from './RecommendationPill';

interface StopBoardProps {
  stop: Stop | undefined;
  arrivals: ShuttleSnapshot[];
  loading: boolean;
  error: Error | null;
  onSelectShuttle: (shuttleId: string) => void;
  onClose: () => void;
}

export function StopBoard({
  stop,
  arrivals,
  loading,
  error,
  onSelectShuttle,
  onClose,
}: StopBoardProps) {
  return (
    <section className="rounded-panel border border-border bg-surface p-4 shadow-sm">
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-muted">Departures</p>
          <h2 className="truncate text-base font-semibold">{stop?.name ?? 'This stop'}</h2>
        </div>

        <button
          type="button"
          onClick={onClose}
          aria-label="Close departure board"
          className="rounded-full p-1 text-muted transition hover:bg-surface-muted hover:text-ink"
        >
          <X className="h-4 w-4" />
        </button>
      </header>

      {loading ? (
        <p className="mt-3 flex items-center gap-2 text-sm text-muted">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Checking what is due…
        </p>
      ) : error ? (
        <p className="mt-3 flex items-start gap-2 text-sm text-critical">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          {error.message}
        </p>
      ) : arrivals.length === 0 ? (
        <p className="mt-3 text-sm text-muted">Nothing is due at this stop right now.</p>
      ) : (
        <ul className="mt-2 flex flex-col divide-y divide-border">
          {arrivals.map((arrival) => (
            <li key={arrival.shuttle.id}>
              <button
                type="button"
                onClick={() => onSelectShuttle(arrival.shuttle.id)}
                className="flex w-full items-center justify-between gap-3 py-2.5 text-left transition hover:opacity-70"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <span
                    className="h-2 w-2 shrink-0 rounded-full"
                    style={{ backgroundColor: arrival.route_color }}
                    aria-hidden="true"
                  />
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium">
                      {arrival.shuttle.name}
                    </span>
                    <span className="block truncate text-xs text-muted">
                      {formatDistance(arrival.direct_distance_m)} away
                      {arrival.shuttle.status === 'DELAYED' ? ' · running late' : ''}
                    </span>
                  </span>
                </span>
                <EtaBadge eta={arrival.eta} size="small" />
              </button>
            </li>
          ))}
        </ul>
      )}

      {arrivals[0] ? (
        <div className="mt-3 border-t border-border pt-3">
          <RecommendationPill recommendation={arrivals[0].recommendation} showDetail />
        </div>
      ) : null}
    </section>
  );
}
