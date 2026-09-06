/**
 * WebSocket message contracts.
 *
 * A discriminated union on `type`, matching `app/schemas/ws.py`. Anything that
 * does not parse into this union is treated as an error rather than being
 * quietly ignored — silent failure is how a demo ends up showing stale
 * positions as though they were live.
 */

import type { Shuttle, SimulationState } from './domain';

export interface ShuttleUpdateMessage {
  type: 'SHUTTLE_UPDATE';
  timestamp: string;
  shuttles: Shuttle[];
}

export interface SimulationStateMessage {
  type: 'SIMULATION_STATE';
  timestamp: string;
  state: SimulationState;
}

export interface ErrorMessage {
  type: 'ERROR';
  timestamp: string;
  detail: string;
}

export type ServerMessage = ShuttleUpdateMessage | SimulationStateMessage | ErrorMessage;

/** Narrow an unknown frame to a known message, or return null. */
export function parseServerMessage(raw: string): ServerMessage | null {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }

  if (typeof parsed !== 'object' || parsed === null || !('type' in parsed)) {
    return null;
  }

  const { type } = parsed as { type: unknown };

  if (type === 'SHUTTLE_UPDATE' && Array.isArray((parsed as ShuttleUpdateMessage).shuttles)) {
    return parsed as ShuttleUpdateMessage;
  }
  if (type === 'SIMULATION_STATE' && 'state' in parsed) {
    return parsed as SimulationStateMessage;
  }
  if (type === 'ERROR') {
    return parsed as ErrorMessage;
  }

  return null;
}

/** Lifecycle of the live connection, as shown to the user. */
export type ConnectionStatus = 'connecting' | 'connected' | 'reconnecting' | 'offline';
