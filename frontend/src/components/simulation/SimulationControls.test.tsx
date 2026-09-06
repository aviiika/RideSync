import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useShuttleStore } from '../../stores/shuttleStore';
import { simulationState } from '../../test/fixtures';
import { renderWithProviders } from '../../test/utils';
import { ConnectionBanner } from '../common/ConnectionBanner';
import { SimulationControls } from './SimulationControls';

let requested: string[] = [];

beforeEach(() => {
  requested = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      requested.push(String(input));
      return {
        ok: true,
        status: 200,
        json: async () => ({ ...simulationState, running: false }),
      } as Response;
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  useShuttleStore.setState({ simulation: null });
});

describe('SimulationControls', () => {
  it('offers pause while running', () => {
    renderWithProviders(<SimulationControls state={simulationState} />);
    expect(screen.getByRole('button', { name: /pause/i })).toBeInTheDocument();
  });

  it('offers start while paused', () => {
    renderWithProviders(<SimulationControls state={{ ...simulationState, running: false }} />);
    expect(screen.getByRole('button', { name: /start/i })).toBeInTheDocument();
  });

  it('starts the simulation', async () => {
    renderWithProviders(<SimulationControls state={{ ...simulationState, running: false }} />);
    await userEvent.click(screen.getByRole('button', { name: /start/i }));

    await waitFor(() => expect(requested.some((url) => url.endsWith('/simulation/start'))).toBe(true));
  });

  it('resets the simulation', async () => {
    renderWithProviders(<SimulationControls state={simulationState} />);
    await userEvent.click(screen.getByRole('button', { name: /reset/i }));

    await waitFor(() => expect(requested.some((url) => url.endsWith('/simulation/reset'))).toBe(true));
  });

  it('changes speed', async () => {
    renderWithProviders(<SimulationControls state={simulationState} />);
    await userEvent.click(screen.getByRole('button', { name: '5×' }));

    await waitFor(() => expect(requested.some((url) => url.endsWith('/simulation/speed'))).toBe(true));
  });

  it('marks the active speed', () => {
    renderWithProviders(<SimulationControls state={{ ...simulationState, speed_multiplier: 2 }} />);
    expect(screen.getByRole('button', { name: '2×' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: '1×' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('shows the seed, so the run is visibly repeatable', () => {
    renderWithProviders(<SimulationControls state={simulationState} />);
    expect(screen.getByText(/seed 42/i)).toBeInTheDocument();
  });
});

describe('ConnectionBanner', () => {
  it('says nothing while the feed is healthy', () => {
    const { container } = renderWithProviders(
      <ConnectionBanner status="connected" stale={false} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('announces a dropped connection and that it is retrying', () => {
    renderWithProviders(<ConnectionBanner status="reconnecting" stale={false} />);
    expect(screen.getByText(/live connection lost/i)).toBeInTheDocument();
    expect(screen.getByText(/reconnecting/i)).toBeInTheDocument();
  });

  it('announces an unreachable backend', () => {
    renderWithProviders(<ConnectionBanner status="offline" stale={false} />);
    expect(screen.getByText(/shuttle service unavailable/i)).toBeInTheDocument();
  });

  it('warns rather than presenting stale telemetry as live', () => {
    renderWithProviders(<ConnectionBanner status="connected" stale />);
    expect(screen.getByText(/no recent telemetry/i)).toBeInTheDocument();
  });
});
