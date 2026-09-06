/** Opens the telemetry socket and feeds it into the store. */

import { useEffect } from 'react';

import { env } from '../config/env';
import { ShuttleSocket } from '../services/websocket';
import { useShuttleStore } from '../stores/shuttleStore';

/**
 * Connect once for the life of the component.
 *
 * Handlers read from the store's `getState` rather than closing over selected
 * values, so the effect never needs to re-run and the socket is never torn
 * down and rebuilt because an unrelated piece of state changed.
 */
export function useShuttleStream(): void {
  useEffect(() => {
    const { applyShuttles, applySimulation, setConnection } = useShuttleStore.getState();

    const socket = new ShuttleSocket(env.wsUrl, {
      onMessage: (message) => {
        switch (message.type) {
          case 'SHUTTLE_UPDATE':
            applyShuttles(message.shuttles);
            break;
          case 'SIMULATION_STATE':
            applySimulation(message.state);
            break;
          case 'ERROR':
            console.error('shuttle service error:', message.detail);
            break;
        }
      },
      onStatusChange: setConnection,
    });

    socket.connect();
    return () => socket.close();
  }, []);
}
