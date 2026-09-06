/**
 * Progressive disclosure: the technical detail, revealed only on selection.
 *
 * Telemetry lives here rather than on the main card so the default screen
 * stays a five-second answer instead of a dashboard.
 */

import { ShieldCheck, TimerReset, X } from 'lucide-react';

import type { Shuttle, ShuttleSnapshot } from '../../types/domain';
import { formatDistance, formatHeading, formatPercent, formatSpeed, formatStatus } from '../../utils/format';
import { EtaBadge } from './EtaBadge';
import { RecommendationPill } from './RecommendationPill';

interface ShuttleDetailsPanelProps {
  /** Live position from the socket — fresher than the polled snapshot. */
  live: Shuttle | undefined;
  snapshot: ShuttleSnapshot | undefined;
  onClose: () => void;
  onInjectDelay?: (shuttleId: string) => void;
  delaying?: boolean;
}

export function ShuttleDetailsPanel({
  live,
  snapshot,
  onClose,
  onInjectDelay,
  delaying = false,
}: ShuttleDetailsPanelProps) {
  const shuttle = live ?? snapshot?.shuttle;

  if (!shuttle) {
    return (
      <section className="rounded-panel border border-border bg-surface p-4">
        <p className="text-sm text-muted">That shuttle is no longer in service.</p>
      </section>
    );
  }

  return (
    <section className="rounded-panel border border-border bg-surface p-4 shadow-sm">
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="flex items-center gap-2 text-base font-semibold">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: snapshot?.route_color ?? 'var(--color-brand)' }}
              aria-hidden="true"
            />
            <span className="truncate">{shuttle.name}</span>
          </p>
          <p className="mt-0.5 truncate text-xs text-muted">
            {snapshot?.route_name ?? shuttle.route_id} · {formatStatus(shuttle.status)}
          </p>
        </div>

        <button
          type="button"
          onClick={onClose}
          aria-label="Close shuttle details"
          className="rounded-full p-1 text-muted transition hover:bg-surface-muted hover:text-ink"
        >
          <X className="h-4 w-4" />
        </button>
      </header>

      {snapshot ? (
        <div className="mt-3 flex items-center justify-between gap-3">
          <EtaBadge eta={snapshot.eta} />
          <RecommendationPill recommendation={snapshot.recommendation} />
        </div>
      ) : null}

      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
        <Detail label="Speed" value={formatSpeed(shuttle.speed_kmh)} />
        <Detail label="Heading" value={formatHeading(shuttle.heading)} />
        <Detail label="Next stop" value={shuttle.next_stop_name ?? '—'} />
        <Detail label="Route progress" value={formatPercent(shuttle.progress)} />
        {snapshot ? (
          <>
            <Detail label="Distance away" value={formatDistance(snapshot.direct_distance_m)} />
            <Detail
              label="Travel to stop"
              value={
                snapshot.eta ? formatDistance(snapshot.eta.remaining_distance_m) : '—'
              }
            />
          </>
        ) : null}
        <Detail label="Occupancy" value={formatPercent(shuttle.occupancy)} />
        {snapshot?.walk_minutes !== null && snapshot?.walk_minutes !== undefined ? (
          <Detail
            label="Walk to stop"
            value={snapshot.walk_minutes < 1 ? 'under a minute' : `${snapshot.walk_minutes} min`}
          />
        ) : null}
      </dl>

      {snapshot?.eta?.confidence ? (
        <p className="mt-3 flex items-start gap-1.5 rounded-lg bg-surface-muted p-2 text-xs text-muted">
          <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          <span>
            <span className="font-medium">{snapshot.eta.confidence.label}</span>{' '}
            {snapshot.eta.confidence.reason}
          </span>
        </p>
      ) : null}

      <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-surface-muted">
        <div
          className="h-full rounded-full transition-[width] duration-500 ease-linear"
          style={{
            width: `${Math.round(shuttle.progress * 100)}%`,
            backgroundColor: snapshot?.route_color ?? 'var(--color-brand)',
          }}
        />
      </div>

      {onInjectDelay ? (
        <button
          type="button"
          disabled={delaying || shuttle.status === 'DELAYED'}
          onClick={() => onInjectDelay(shuttle.id)}
          className="mt-3 inline-flex w-full items-center justify-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm font-medium transition hover:bg-surface-muted disabled:opacity-50"
        >
          <TimerReset className="h-4 w-4" />
          {shuttle.status === 'DELAYED' ? 'Running late' : 'Delay this shuttle'}
        </button>
      ) : null}

      {snapshot?.eta ? (
        <p className="mt-3 text-xs text-muted">
          Estimate from {snapshot.eta.source} arithmetic:{' '}
          {formatDistance(snapshot.eta.remaining_distance_m)} of route at{' '}
          {formatSpeed(snapshot.eta.effective_speed_kmh)}
          {snapshot.eta.intervening_stops > 0
            ? `, calling at ${snapshot.eta.intervening_stops} stop${
                snapshot.eta.intervening_stops === 1 ? '' : 's'
              } on the way`
            : ''}
          .
        </p>
      ) : null}
    </section>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="truncate font-medium">{value}</dd>
    </div>
  );
}
