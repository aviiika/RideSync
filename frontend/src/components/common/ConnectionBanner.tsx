/**
 * Connection state, stated plainly.
 *
 * The application must never present stale telemetry as live, so a lost
 * socket and an old frame both surface here rather than being swallowed.
 */

import { Loader2, WifiOff } from 'lucide-react';

import type { ConnectionStatus } from '../../types/ws';

interface ConnectionBannerProps {
  status: ConnectionStatus;
  stale: boolean;
}

export function ConnectionBanner({ status, stale }: ConnectionBannerProps) {
  if (status === 'connected' && !stale) {
    return null;
  }

  const { tone, Icon, title, detail } = describe(status);

  return (
    <div
      role="status"
      className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${tone}`}
    >
      <Icon className={`h-4 w-4 shrink-0 ${status !== 'offline' ? 'animate-spin' : ''}`} />
      <span>
        <span className="font-medium">{title}</span>
        {detail ? <span className="opacity-80"> · {detail}</span> : null}
      </span>
    </div>
  );
}

function describe(status: ConnectionStatus) {
  if (status === 'connecting') {
    return {
      tone: 'bg-surface-muted text-muted',
      Icon: Loader2,
      title: 'Connecting to live telemetry',
      detail: '',
    };
  }

  if (status === 'reconnecting') {
    return {
      tone: 'bg-caution/15 text-caution',
      Icon: Loader2,
      title: 'Live connection lost',
      detail: 'Reconnecting…',
    };
  }

  if (status === 'offline') {
    return {
      tone: 'bg-critical/10 text-critical',
      Icon: WifiOff,
      title: 'Shuttle service unavailable',
      detail: 'Retrying in the background',
    };
  }

  // Connected, but the last frame is old: positions are no longer live.
  return {
    tone: 'bg-caution/15 text-caution',
    Icon: WifiOff,
    title: 'No recent telemetry',
    detail: 'Positions shown may be out of date',
  };
}
