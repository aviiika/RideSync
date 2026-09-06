/**
 * The single most important number on the screen.
 *
 * Deliberately approximate: "~4 min", never "3 min 47 sec". The estimate is
 * not that precise, and displaying it as though it were would be a lie the
 * user notices the first time a shuttle is late.
 */

import type { Eta } from '../../types/domain';

interface EtaBadgeProps {
  eta: Eta | null;
  size?: 'large' | 'small';
}

export function EtaBadge({ eta, size = 'large' }: EtaBadgeProps) {
  if (!eta) {
    return (
      <span
        className={size === 'large' ? 'text-2xl font-semibold text-muted' : 'text-sm text-muted'}
      >
        ETA unavailable
      </span>
    );
  }

  if (eta.minutes < 1) {
    return (
      <span
        className={
          size === 'large'
            ? 'whitespace-nowrap text-xl font-semibold tracking-tight text-positive'
            : 'whitespace-nowrap text-sm font-medium text-positive'
        }
      >
        Arriving now
      </span>
    );
  }

  return (
    <span className={size === 'large' ? 'flex items-baseline gap-1.5' : 'text-sm font-medium'}>
      <span className={size === 'large' ? 'text-3xl font-semibold tracking-tight' : undefined}>
        ~{eta.minutes}
      </span>
      <span className={size === 'large' ? 'text-base text-muted' : undefined}>min</span>
    </span>
  );
}
