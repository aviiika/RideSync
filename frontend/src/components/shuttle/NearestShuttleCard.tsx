/**
 * The five-second answer.
 *
 * If a rider reads nothing else, they read this: which shuttle, how long,
 * how far, where it is heading, and whether it is worth waiting.
 */

import { Navigation } from 'lucide-react';

import type { ShuttleSnapshot } from '../../types/domain';
import { formatDistance } from '../../utils/format';
import { EtaBadge } from './EtaBadge';
import { RecommendationPill } from './RecommendationPill';

interface NearestShuttleCardProps {
  snapshot: ShuttleSnapshot;
  onSelect: (shuttleId: string) => void;
}

export function NearestShuttleCard({ snapshot, onSelect }: NearestShuttleCardProps) {
  const { shuttle, eta, recommendation } = snapshot;

  return (
    <button
      type="button"
      onClick={() => onSelect(shuttle.id)}
      className="w-full rounded-panel border border-border bg-surface p-4 text-left shadow-sm transition hover:border-brand/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-muted">Next shuttle</p>
          <p className="mt-0.5 flex items-center gap-2 text-base font-semibold">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: snapshot.route_color }}
              aria-hidden="true"
            />
            <span className="truncate">{shuttle.name}</span>
          </p>
        </div>
        <EtaBadge eta={eta} />
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-xs text-muted">Distance away</dt>
          <dd className="font-medium">{formatDistance(snapshot.direct_distance_m)}</dd>
        </div>
        <div className="min-w-0">
          <dt className="text-xs text-muted">Arriving at</dt>
          <dd className="truncate font-medium">{snapshot.target_stop_name ?? '—'}</dd>
        </div>
      </dl>

      {shuttle.next_stop_name ? (
        <p className="mt-3 flex items-center gap-1.5 text-xs text-muted">
          <Navigation className="h-3.5 w-3.5" aria-hidden="true" />
          Heading toward {shuttle.next_stop_name}
        </p>
      ) : null}

      <div className="mt-3">
        <RecommendationPill recommendation={recommendation} showDetail />
      </div>
    </button>
  );
}
