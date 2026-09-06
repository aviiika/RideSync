import type { ReactNode } from 'react';

export type StatusTone = 'positive' | 'caution' | 'critical' | 'muted';

const TONE_CLASS: Record<StatusTone, string> = {
  positive: 'bg-positive',
  caution: 'bg-caution',
  critical: 'bg-critical',
  muted: 'bg-muted',
};

/** A coloured dot plus a label — the connection/service indicator. */
export function StatusDot({ tone, children }: { tone: StatusTone; children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-muted">
      <span
        className={`h-2 w-2 shrink-0 rounded-full ${TONE_CLASS[tone]}`}
        aria-hidden="true"
      />
      {children}
    </span>
  );
}
