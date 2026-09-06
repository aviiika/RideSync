/**
 * Demo controls.
 *
 * A first-class feature, not a debug panel: a pitch depends on being able to
 * start, speed up and reset the simulation on demand, and on the reset being
 * exact so the run is repeatable.
 */

import { Pause, Play, RotateCcw } from 'lucide-react';

import { useSimulationControls } from '../../hooks/useNetwork';
import type { SimulationState } from '../../types/domain';

const SPEEDS = [1, 2, 5] as const;

export function SimulationControls({ state }: { state: SimulationState | null }) {
  const { start, pause, reset, setSpeed } = useSimulationControls();

  const running = state?.running ?? false;
  const speed = state?.speed_multiplier ?? 1;
  const busy = start.isPending || pause.isPending || reset.isPending;

  return (
    <section className="rounded-panel border border-border bg-surface p-3 shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted">Simulation</p>
        {state ? (
          <p className="text-xs text-muted" title="Runs with the same seed are identical">
            seed {state.seed}
          </p>
        ) : null}
      </div>

      <div className="mt-2.5 flex items-center gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => (running ? pause.mutate() : start.mutate())}
          className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-brand px-3 py-2 text-sm font-medium text-white transition hover:bg-brand/90 disabled:opacity-50"
        >
          {running ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          {running ? 'Pause' : 'Start'}
        </button>

        <button
          type="button"
          disabled={busy}
          onClick={() => reset.mutate()}
          className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm font-medium transition hover:bg-surface-muted disabled:opacity-50"
        >
          <RotateCcw className="h-4 w-4" />
          Reset
        </button>
      </div>

      <div className="mt-2.5 flex items-center gap-1.5" role="group" aria-label="Simulation speed">
        {SPEEDS.map((multiplier) => (
          <button
            key={multiplier}
            type="button"
            aria-pressed={speed === multiplier}
            onClick={() => setSpeed.mutate(multiplier)}
            className={`flex-1 rounded-lg px-2 py-1.5 text-sm font-medium transition ${
              speed === multiplier
                ? 'bg-ink text-white'
                : 'border border-border hover:bg-surface-muted'
            }`}
          >
            {multiplier}×
          </button>
        ))}
      </div>
    </section>
  );
}
