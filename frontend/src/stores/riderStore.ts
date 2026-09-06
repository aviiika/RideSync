/**
 * Where the rider is standing.
 *
 * Kept apart from the shuttle store because it changes for entirely different
 * reasons: telemetry arrives twice a second, a rider moves when a person
 * decides to move. Mixing them would wake every ETA subscriber on every frame.
 *
 * The chosen position survives a reload, so a demo that has been set up stays
 * set up.
 */

import { create } from 'zustand';

import type { Coordinate } from '../types/domain';

const STORAGE_KEY = 'ridesync.rider';

/** VIT Vellore Main Gate — where a rider actually waits. */
export const DEFAULT_RIDER: Coordinate = { latitude: 12.9692, longitude: 79.1554 };

/** How the current position was arrived at, so the UI can say. */
export type RiderSource = 'default' | 'picked' | 'device' | 'place';

interface RiderStore {
  position: Coordinate;
  source: RiderSource;
  /** Name of the campus place chosen, when the rider picked one by name. */
  placeName: string | null;
  /** True while the map is waiting for a click to place the rider. */
  picking: boolean;
  /** Set when the device refused or failed to provide a location. */
  locationError: string | null;

  setPosition: (position: Coordinate, source: RiderSource, placeName?: string) => void;
  startPicking: () => void;
  cancelPicking: () => void;
  setLocationError: (message: string | null) => void;
  reset: () => void;
}

function readStored(): { position: Coordinate; source: RiderSource; placeName: string | null } | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }

    const parsed = JSON.parse(raw) as Partial<Coordinate> & {
      source?: RiderSource;
      placeName?: string;
    };
    if (typeof parsed.latitude !== 'number' || typeof parsed.longitude !== 'number') {
      return null;
    }

    const source: RiderSource =
      parsed.source === 'device' || parsed.source === 'place' ? parsed.source : 'picked';

    return {
      position: { latitude: parsed.latitude, longitude: parsed.longitude },
      source,
      placeName: typeof parsed.placeName === 'string' ? parsed.placeName : null,
    };
  } catch {
    // Private windows, cleared site data, storage disabled: fall back silently.
    return null;
  }
}

function writeStored(position: Coordinate, source: RiderSource, placeName?: string): void {
  try {
    if (source === 'default') {
      localStorage.removeItem(STORAGE_KEY);
      return;
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...position, source, placeName }));
  } catch {
    // Storage is a convenience here, never a requirement.
  }
}

const stored = readStored();

export const useRiderStore = create<RiderStore>((set) => ({
  position: stored?.position ?? DEFAULT_RIDER,
  source: stored?.source ?? 'default',
  placeName: stored?.placeName ?? null,
  picking: false,
  locationError: null,

  setPosition: (position, source, placeName) => {
    writeStored(position, source, placeName);
    set({
      position,
      source,
      placeName: placeName ?? null,
      picking: false,
      locationError: null,
    });
  },

  startPicking: () => set({ picking: true, locationError: null }),
  cancelPicking: () => set({ picking: false }),
  setLocationError: (locationError) => set({ locationError, picking: false }),

  reset: () => {
    writeStored(DEFAULT_RIDER, 'default');
    set({
      position: DEFAULT_RIDER,
      source: 'default',
      placeName: null,
      picking: false,
      locationError: null,
    });
  },
}));

/** Human label for where the position came from. */
export function describeRiderSource(source: RiderSource, placeName?: string | null): string {
  switch (source) {
    case 'device':
      return 'Using your device location';
    case 'place':
      return placeName ?? 'A place on campus';
    case 'picked':
      return 'Custom location on campus';
    default:
      return 'Main Gate';
  }
}
