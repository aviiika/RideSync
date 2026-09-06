/**
 * Reconnection behaviour.
 *
 * The demo runs on a laptop that may sleep, and the backend restarts during
 * development, so recovering from a dropped socket is a feature, not an edge
 * case. Timers are faked so backoff is asserted rather than waited out.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ShuttleSocket } from './websocket';
import type { ConnectionStatus } from '../types/ws';

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];

  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  closed = false;

  readonly url: string;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  close(): void {
    this.closed = true;
    this.onclose?.();
  }

  open(): void {
    this.onopen?.();
  }

  emit(payload: unknown): void {
    this.onmessage?.({ data: JSON.stringify(payload) } as MessageEvent<string>);
  }
}

describe('ShuttleSocket', () => {
  let statuses: ConnectionStatus[];
  let messages: unknown[];

  beforeEach(() => {
    vi.useFakeTimers();
    FakeWebSocket.instances = [];
    statuses = [];
    messages = [];
    vi.stubGlobal('WebSocket', FakeWebSocket);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  function connect() {
    const socket = new ShuttleSocket('ws://test/ws', {
      onMessage: (message) => messages.push(message),
      onStatusChange: (status) => statuses.push(status),
    });
    socket.connect();
    return socket;
  }

  it('reports connecting, then connected', () => {
    connect();
    expect(statuses).toEqual(['connecting']);

    FakeWebSocket.instances[0]!.open();
    expect(statuses).toEqual(['connecting', 'connected']);
  });

  it('delivers parsed messages', () => {
    connect();
    const socket = FakeWebSocket.instances[0]!;
    socket.open();
    socket.emit({ type: 'SHUTTLE_UPDATE', timestamp: 'now', shuttles: [] });

    expect(messages).toHaveLength(1);
    expect((messages[0] as { type: string }).type).toBe('SHUTTLE_UPDATE');
  });

  it('ignores frames it cannot parse rather than crashing', () => {
    connect();
    const socket = FakeWebSocket.instances[0]!;
    socket.open();
    socket.onmessage?.({ data: 'not json' } as MessageEvent<string>);
    socket.emit({ type: 'SOMETHING_ELSE' });

    expect(messages).toHaveLength(0);
  });

  it('reconnects after the connection drops', () => {
    connect();
    FakeWebSocket.instances[0]!.open();
    FakeWebSocket.instances[0]!.close();

    expect(statuses).toContain('reconnecting');

    vi.advanceTimersByTime(1000);
    expect(FakeWebSocket.instances).toHaveLength(2);
  });

  it('backs off instead of hammering a dead server', () => {
    connect();

    // Never opened: each failure should wait longer than the last.
    FakeWebSocket.instances[0]!.close();
    vi.advanceTimersByTime(1000);
    const afterFirst = FakeWebSocket.instances.length;

    FakeWebSocket.instances[afterFirst - 1]!.close();
    vi.advanceTimersByTime(600);
    expect(FakeWebSocket.instances).toHaveLength(afterFirst);

    vi.advanceTimersByTime(2000);
    expect(FakeWebSocket.instances.length).toBeGreaterThan(afterFirst);
  });

  it('reports offline before it has ever connected', () => {
    connect();
    FakeWebSocket.instances[0]!.close();
    expect(statuses).toContain('offline');
  });

  it('stops retrying once closed by the caller', () => {
    const socket = connect();
    FakeWebSocket.instances[0]!.open();
    socket.close();

    vi.advanceTimersByTime(30_000);
    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it('resets its backoff after a successful reconnect', () => {
    connect();
    const first = FakeWebSocket.instances[0]!;
    first.open();
    first.close();

    vi.advanceTimersByTime(1000);
    const second = FakeWebSocket.instances[1]!;
    second.open();
    second.close();

    // Backoff was reset by the successful open, so the next attempt is quick.
    vi.advanceTimersByTime(1000);
    expect(FakeWebSocket.instances).toHaveLength(3);
  });
});
