/**
 * "Where am I?"
 *
 * Every ETA on screen is relative to one point, so being able to move that
 * point is what turns the demo from a picture into something you can interrogate:
 * stand at the hostel, stand at the gate, watch the answer change.
 *
 * Two ways in — pick a spot on the map, or ask the device — and the device is
 * never assumed to work.
 */

import { Crosshair, LocateFixed, MapPin, X } from 'lucide-react';

import { describeRiderSource, type RiderSource } from '../../stores/riderStore';

interface LocationControlProps {
  source: RiderSource;
  picking: boolean;
  locating: boolean;
  error: string | null;
  onPick: () => void;
  onCancelPick: () => void;
  onUseDevice: () => void;
  onReset: () => void;
}

export function LocationControl({
  source,
  picking,
  locating,
  error,
  onPick,
  onCancelPick,
  onUseDevice,
  onReset,
}: LocationControlProps) {
  return (
    <div className="pointer-events-auto flex flex-col gap-1.5 rounded-panel border border-border bg-surface/95 p-1.5 shadow-sm backdrop-blur">
      <div className="flex items-center gap-1.5">
        <MapPin className="ml-1 h-3.5 w-3.5 shrink-0 text-brand" aria-hidden="true" />
        <span className="mr-1 text-xs text-muted">{describeRiderSource(source)}</span>

        {picking ? (
          <button
            type="button"
            onClick={onCancelPick}
            className="inline-flex items-center gap-1 rounded-full bg-ink px-2.5 py-1 text-xs font-medium text-white"
          >
            <X className="h-3 w-3" />
            Cancel
          </button>
        ) : (
          <button
            type="button"
            onClick={onPick}
            className="rounded-full px-2.5 py-1 text-xs font-medium text-muted transition hover:bg-surface-muted hover:text-ink"
          >
            Set on map
          </button>
        )}

        <button
          type="button"
          onClick={onUseDevice}
          disabled={locating}
          title="Use my device location"
          aria-label="Use my device location"
          className="rounded-full p-1.5 text-muted transition hover:bg-surface-muted hover:text-ink disabled:opacity-50"
        >
          <LocateFixed className={`h-4 w-4 ${locating ? 'animate-pulse' : ''}`} />
        </button>

        {source !== 'default' ? (
          <button
            type="button"
            onClick={onReset}
            title="Back to the Main Gate"
            aria-label="Back to the Main Gate"
            className="rounded-full p-1.5 text-muted transition hover:bg-surface-muted hover:text-ink"
          >
            <Crosshair className="h-4 w-4" />
          </button>
        ) : null}
      </div>

      {picking ? (
        <p className="px-1 pb-0.5 text-xs text-brand">Tap anywhere on the map to stand there.</p>
      ) : null}

      {error ? (
        <p className="px-1 pb-0.5 text-xs text-critical" role="status">
          {error}
        </p>
      ) : null}
    </div>
  );
}
