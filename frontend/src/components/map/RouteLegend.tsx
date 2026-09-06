/**
 * Route legend and filter.
 *
 * Two jobs at once: it tells a first-time viewer what the coloured lines mean,
 * and it lets a presenter isolate one route mid-demo — "here is just the
 * ladies' hostel service" — without touching the data.
 *
 * It floats over the map deliberately small. The map is the product; this is a
 * caption, not a control panel.
 */

import { Crosshair } from 'lucide-react';

import type { Route } from '../../types/domain';

interface RouteLegendProps {
  routes: Route[];
  active: string | null;
  onChange: (routeId: string | null) => void;
  onRecentre: () => void;
}

export function RouteLegend({ routes, active, onChange, onRecentre }: RouteLegendProps) {
  if (routes.length === 0) {
    return null;
  }

  return (
    <div className="pointer-events-none absolute left-3 top-3 z-10 flex max-w-[calc(100%-1.5rem)] flex-col gap-2">
      <div
        className="pointer-events-auto flex flex-wrap items-center gap-1.5 rounded-panel border border-border bg-surface/95 p-1.5 shadow-sm backdrop-blur"
        role="group"
        aria-label="Filter by route"
      >
        <Chip active={active === null} onClick={() => onChange(null)}>
          All routes
        </Chip>

        {routes.map((route) => (
          <Chip
            key={route.id}
            active={active === route.id}
            color={route.color}
            onClick={() => onChange(active === route.id ? null : route.id)}
          >
            {route.name}
          </Chip>
        ))}

        <button
          type="button"
          onClick={onRecentre}
          title="Recentre on campus"
          aria-label="Recentre on campus"
          className="ml-0.5 rounded-full p-1.5 text-muted transition hover:bg-surface-muted hover:text-ink"
        >
          <Crosshair className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function Chip({
  active,
  color,
  onClick,
  children,
}: {
  active: boolean;
  color?: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition ${
        active ? 'bg-ink text-white' : 'text-muted hover:bg-surface-muted hover:text-ink'
      }`}
    >
      {color ? (
        <span
          className="h-2 w-2 shrink-0 rounded-full"
          style={{ backgroundColor: active ? '#ffffff' : color }}
          aria-hidden="true"
        />
      ) : null}
      {children}
    </button>
  );
}
