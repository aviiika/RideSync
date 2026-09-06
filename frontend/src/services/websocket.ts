/**
 * Reconnecting telemetry socket.
 *
 * One socket per client, reused for the life of the page. Reconnection uses
 * exponential backoff with jitter and a ceiling, so a backend that is down
 * does not turn into a tight reconnect loop hammering the network — and so a
 * backend that comes back is picked up within a few seconds.
 */

import { parseServerMessage, type ConnectionStatus, type ServerMessage } from '../types/ws';

const INITIAL_RETRY_MS = 500;
const MAX_RETRY_MS = 10_000;
const BACKOFF_FACTOR = 2;

export interface ShuttleSocketHandlers {
  onMessage: (message: ServerMessage) => void;
  onStatusChange: (status: ConnectionStatus) => void;
}

export class ShuttleSocket {
  private socket: WebSocket | null = null;
  private retryMs = INITIAL_RETRY_MS;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private closedByCaller = false;
  private hasConnectedOnce = false;

  private readonly url: string;
  private readonly handlers: ShuttleSocketHandlers;

  constructor(url: string, handlers: ShuttleSocketHandlers) {
    this.url = url;
    this.handlers = handlers;
  }

  connect(): void {
    this.closedByCaller = false;
    this.clearRetry();

    this.handlers.onStatusChange(this.hasConnectedOnce ? 'reconnecting' : 'connecting');

    let socket: WebSocket;
    try {
      socket = new WebSocket(this.url);
    } catch {
      // A malformed URL throws synchronously; treat it like any other failure
      // so the UI shows "offline" rather than a blank map.
      this.scheduleRetry();
      return;
    }

    this.socket = socket;

    socket.onopen = () => {
      this.hasConnectedOnce = true;
      this.retryMs = INITIAL_RETRY_MS;
      this.handlers.onStatusChange('connected');
    };

    socket.onmessage = (event: MessageEvent<string>) => {
      const message = parseServerMessage(event.data);
      if (message) {
        this.handlers.onMessage(message);
      }
    };

    socket.onerror = () => {
      // `onclose` always follows, and that is where retry is scheduled.
    };

    socket.onclose = () => {
      this.socket = null;
      if (!this.closedByCaller) {
        this.scheduleRetry();
      }
    };
  }

  /** Close for good. Used on unmount; does not trigger a reconnect. */
  close(): void {
    this.closedByCaller = true;
    this.clearRetry();
    this.socket?.close();
    this.socket = null;
  }

  private scheduleRetry(): void {
    this.handlers.onStatusChange(this.hasConnectedOnce ? 'reconnecting' : 'offline');

    // Jitter stops every open tab from reconnecting on the same beat.
    const jitter = Math.random() * 0.3 * this.retryMs;
    const delay = Math.min(this.retryMs + jitter, MAX_RETRY_MS);

    this.retryTimer = setTimeout(() => this.connect(), delay);
    this.retryMs = Math.min(this.retryMs * BACKOFF_FACTOR, MAX_RETRY_MS);
  }

  private clearRetry(): void {
    if (this.retryTimer !== null) {
      clearTimeout(this.retryTimer);
      this.retryTimer = null;
    }
  }
}
