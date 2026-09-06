/**
 * "Where are you?"
 *
 * The ride-hailing pattern: type a place, pick it, and everything on screen
 * re-answers itself from there. There is no geocoder behind this and there does
 * not need to be — a campus has a known, finite list of places, and searching
 * the stops the service actually calls at is both faster and more honest than
 * free-text search that can return somewhere no shuttle goes.
 */

import { MapPin, Search, X } from 'lucide-react';
import { useMemo, useRef, useState } from 'react';

import type { Stop } from '../../types/domain';

/** Enough matches to choose from, few enough to scan. */
const MAX_SUGGESTIONS = 6;

interface LocationSearchProps {
  stops: Stop[];
  /** What the box shows when it is not being typed in. */
  currentLabel: string;
  onPick: (stop: Stop) => void;
}

export function LocationSearch({ stops, currentLabel, onPick }: LocationSearchProps) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // One entry per place, not per stop: several routes call at the Main Gate,
  // and offering it three times would be noise.
  const places = useMemo(() => {
    const byName = new Map<string, Stop>();
    for (const stop of stops) {
      if (!byName.has(stop.name)) {
        byName.set(stop.name, stop);
      }
    }
    return [...byName.values()].sort((a, b) => a.name.localeCompare(b.name));
  }, [stops]);

  const matches = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (needle === '') {
      return places.slice(0, MAX_SUGGESTIONS);
    }
    return places
      .filter((place) => place.name.toLowerCase().includes(needle))
      .slice(0, MAX_SUGGESTIONS);
  }, [places, query]);

  const choose = (stop: Stop) => {
    onPick(stop);
    setQuery('');
    setOpen(false);
    inputRef.current?.blur();
  };

  return (
    <section className="relative rounded-panel border border-border bg-surface p-3 shadow-sm">
      <label
        className="text-xs font-semibold uppercase tracking-wide text-muted"
        htmlFor="location-search"
      >
        Your location
      </label>

      <div className="mt-1.5 flex items-center gap-2 rounded-lg border border-border px-2.5 py-2 focus-within:border-brand">
        <Search className="h-4 w-4 shrink-0 text-muted" aria-hidden="true" />
        <input
          id="location-search"
          ref={inputRef}
          type="text"
          value={query}
          placeholder={currentLabel}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          // Blur is deferred so a click on a suggestion lands before the list
          // closes underneath the pointer.
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          autoComplete="off"
          className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted"
        />
        {query ? (
          <button
            type="button"
            onClick={() => setQuery('')}
            aria-label="Clear search"
            className="rounded-full p-0.5 text-muted transition hover:text-ink"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        ) : null}
      </div>

      {open ? (
        <ul className="absolute inset-x-3 top-full z-20 mt-1 overflow-hidden rounded-lg border border-border bg-surface shadow-lg">
          {matches.length === 0 ? (
            <li className="px-3 py-2.5 text-sm text-muted">
              No campus stop matches “{query.trim()}”.
            </li>
          ) : (
            matches.map((place) => (
              <li key={place.id}>
                <button
                  type="button"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => choose(place)}
                  className="flex w-full items-center gap-2 px-3 py-2.5 text-left text-sm transition hover:bg-surface-muted"
                >
                  <MapPin className="h-3.5 w-3.5 shrink-0 text-muted" aria-hidden="true" />
                  <span className="truncate">{place.name}</span>
                </button>
              </li>
            ))
          )}
        </ul>
      ) : null}
    </section>
  );
}
