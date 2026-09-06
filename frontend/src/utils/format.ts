/**
 * Display formatting.
 *
 * Kept out of components so precision is decided once. Every number shown to a
 * rider is rounded to the accuracy it actually has: metres below a kilometre,
 * one decimal above.
 */

export function formatDistance(metres: number): string {
  if (!Number.isFinite(metres) || metres < 0) {
    return '—';
  }
  if (metres < 1000) {
    return `${Math.round(metres / 10) * 10} m`;
  }
  return `${(metres / 1000).toFixed(1)} km`;
}

export function formatSpeed(kmh: number): string {
  if (!Number.isFinite(kmh)) {
    return '—';
  }
  return `${Math.round(kmh)} km/h`;
}

/** A bearing as a compass point — easier to read at a glance than "247°". */
export function formatHeading(degrees: number): string {
  if (!Number.isFinite(degrees)) {
    return '—';
  }
  const points = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  const index = Math.round(((degrees % 360) + 360) % 360 / 45) % 8;
  return `${points[index]} · ${Math.round(degrees)}°`;
}

export function formatPercent(fraction: number): string {
  if (!Number.isFinite(fraction)) {
    return '—';
  }
  return `${Math.round(fraction * 100)}%`;
}

/** Human label for a service status. */
export function formatStatus(status: string): string {
  const labels: Record<string, string> = {
    IN_SERVICE: 'In service',
    ARRIVING: 'Arriving',
    AT_STOP: 'At stop',
    DELAYED: 'Delayed',
    OUT_OF_SERVICE: 'Out of service',
    STALE: 'No recent data',
  };
  return labels[status] ?? status;
}
