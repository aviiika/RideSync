/**
 * Who is signed in.
 *
 * The token is signed and expiring on the server, so a session cannot be
 * forged by editing local storage - but it is still only *identification*.
 * The password is the registration number; see `auth_service.py`.
 */

import { create } from 'zustand';

const STORAGE_KEY = 'ridesync.session';

interface StoredSession {
  registrationNumber: string;
  token: string;
  expiresAt: string;
}

interface AuthStore {
  registrationNumber: string | null;
  token: string | null;
  signIn: (session: StoredSession) => void;
  signOut: () => void;
}

function readStored(): StoredSession | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }

    const parsed = JSON.parse(raw) as Partial<StoredSession>;
    if (
      typeof parsed.registrationNumber !== 'string' ||
      typeof parsed.token !== 'string' ||
      typeof parsed.expiresAt !== 'string'
    ) {
      return null;
    }

    // Expiry is enforced server-side; checking it here just avoids showing a
    // signed-in shell that is about to be rejected.
    if (new Date(parsed.expiresAt).getTime() <= Date.now()) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }

    return parsed as StoredSession;
  } catch {
    // Private windows, cleared site data, storage disabled.
    return null;
  }
}

function writeStored(session: StoredSession | null): void {
  try {
    if (session === null) {
      localStorage.removeItem(STORAGE_KEY);
      return;
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } catch {
    // Staying signed in across reloads is a convenience, never a requirement.
  }
}

const stored = readStored();

export const useAuthStore = create<AuthStore>((set) => ({
  registrationNumber: stored?.registrationNumber ?? null,
  token: stored?.token ?? null,

  signIn: (session) => {
    writeStored(session);
    set({ registrationNumber: session.registrationNumber, token: session.token });
  },

  signOut: () => {
    writeStored(null);
    set({ registrationNumber: null, token: null });
  },
}));
