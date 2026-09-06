/**
 * Application shell.
 *
 * The map itself needs WebGL, which jsdom does not provide, so it is stubbed.
 * What matters here is the surrounding behaviour: loading, error and empty
 * states, and that the rider's answer is on screen.
 */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { App } from './App';
import { useAuthStore } from './stores/authStore';
import { useShuttleStore } from './stores/shuttleStore';
import { route, shuttle, snapshot } from './test/fixtures';
import { renderWithProviders } from './test/utils';

vi.mock('./components/map/ShuttleMap', () => ({
  ShuttleMap: () => <div data-testid="shuttle-map" />,
}));

vi.mock('./hooks/useShuttleStream', () => ({
  useShuttleStream: () => undefined,
}));

function mockApi(handler: (path: string) => { ok: boolean; body: unknown }) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const { ok, body } = handler(String(input));
      return { ok, status: ok ? 200 : 500, json: async () => body } as Response;
    }),
  );
}

const healthy = (path: string) => {
  if (path.includes('/routes')) return { ok: true, body: [route] };
  if (path.includes('/shuttles/nearby')) return { ok: true, body: [snapshot] };
  if (path.includes('/simulation')) return { ok: true, body: null };
  return { ok: true, body: { status: 'ok', version: '0.1.0', routes_loaded: 1 } };
};

beforeEach(() => {
  // The shell gates on a session, so every test here starts signed in.
  useAuthStore.setState({ registrationNumber: '24MID0159', token: 'test-token' });
  useShuttleStore.setState({
    shuttles: {},
    shuttleIds: [],
    simulation: null,
    connection: 'connected',
    selectedShuttleId: null,
    selectedStopId: null,
    routeFilter: null,
    lastUpdateAt: Date.now(),
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('App', () => {
  it('shows a loading state before the network arrives', () => {
    mockApi(healthy);
    renderWithProviders(<App />);
    expect(screen.getByText(/loading the route network/i)).toBeInTheDocument();
  });

  it('renders the map once routes load', async () => {
    mockApi(healthy);
    renderWithProviders(<App />);
    expect(await screen.findByTestId('shuttle-map')).toBeInTheDocument();
  });

  it('leads with the next shuttle and its ETA', async () => {
    mockApi(healthy);
    renderWithProviders(<App />);

    // Anchored: /next shuttle/i would also match the "Finding your next
    // shuttle..." loading line and pass before the card has rendered.
    expect(await screen.findByText('Academic Block Circuit 1')).toBeInTheDocument();
    expect(screen.getByText(/^Next shuttle$/i)).toBeInTheDocument();
    expect(screen.getByText('~4')).toBeInTheDocument();
    expect(screen.getByText('Worth waiting')).toBeInTheDocument();
  });

  it('opens the details panel when a shuttle is selected', async () => {
    mockApi(healthy);
    useShuttleStore.setState({ shuttles: { [shuttle.id]: shuttle }, shuttleIds: [shuttle.id] });
    renderWithProviders(<App />);

    await userEvent.click(await screen.findByRole('button', { name: /academic block circuit 1/i }));

    expect(await screen.findByText(/route progress/i)).toBeInTheDocument();
    expect(screen.getByText('31%')).toBeInTheDocument();
    expect(screen.getByText(/^Speed$/)).toBeInTheDocument();
  });

  it('closes the details panel again', async () => {
    mockApi(healthy);
    useShuttleStore.setState({ shuttles: { [shuttle.id]: shuttle }, shuttleIds: [shuttle.id] });
    renderWithProviders(<App />);

    await userEvent.click(await screen.findByRole('button', { name: /academic block circuit 1/i }));
    await userEvent.click(screen.getByRole('button', { name: /close shuttle details/i }));

    expect(await screen.findByText(/^Next shuttle$/i)).toBeInTheDocument();
  });

  it('reports an unreachable backend rather than showing a blank panel', async () => {
    mockApi((path) => (path.includes('/routes') ? { ok: false, body: {} } : healthy(path)));
    renderWithProviders(<App />);

    expect(await screen.findByText(/the map could not load/i)).toBeInTheDocument();
  });

  it('shows an empty state when nothing is in service', async () => {
    mockApi((path) =>
      path.includes('/shuttles/nearby') ? { ok: true, body: [] } : healthy(path),
    );
    renderWithProviders(<App />);

    expect(await screen.findByText(/no shuttles are in service/i)).toBeInTheDocument();
  });

  it('surfaces a lost live connection', async () => {
    mockApi(healthy);
    useShuttleStore.setState({ connection: 'reconnecting' });
    renderWithProviders(<App />);

    await waitFor(() => expect(screen.getByText(/live connection lost/i)).toBeInTheDocument());
  });

  it('never claims the simulated feed is real GPS', async () => {
    mockApi(healthy);
    renderWithProviders(<App />);
    expect(await screen.findByText(/telemetry is simulated, not real gps/i)).toBeInTheDocument();
  });
});

describe('near and far grouping', () => {
  it('separates close shuttles from distant ones', async () => {
    const near = { ...snapshot, shuttle: { ...shuttle, id: 'NEAR-1', name: 'Near One' }, direct_distance_m: 180 };
    const far = { ...snapshot, shuttle: { ...shuttle, id: 'FAR-1', name: 'Far One' }, direct_distance_m: 1400 };

    mockApi((path) =>
      path.includes('/shuttles/nearby')
        ? { ok: true, body: [snapshot, near, far] }
        : healthy(path),
    );
    renderWithProviders(<App />);

    // Wait on real content: the group headings render before the data does.
    expect(await screen.findByText('Near One')).toBeInTheDocument();
    expect(screen.getByText('Far One')).toBeInTheDocument();
    expect(screen.getByText(/nearby ·/i)).toBeInTheDocument();
    expect(screen.getByText(/further away/i)).toBeInTheDocument();
  });

  it('says when nothing is close, instead of an empty heading', async () => {
    const far = { ...snapshot, shuttle: { ...shuttle, id: 'FAR-1', name: 'Far One' }, direct_distance_m: 1400 };

    mockApi((path) =>
      path.includes('/shuttles/nearby') ? { ok: true, body: [snapshot, far] } : healthy(path),
    );
    renderWithProviders(<App />);

    expect(await screen.findByText(/no shuttle is close to you/i)).toBeInTheDocument();
  });

  it('lets you set your location by name', async () => {
    mockApi(healthy);
    renderWithProviders(<App />);

    const input = await screen.findByRole('textbox');
    await userEvent.type(input, 'main building');

    const suggestions = screen.getByRole('list', { hidden: false });
    expect(
      within(suggestions).getByRole('button', { name: /main building/i }),
    ).toBeInTheDocument();
  });
});

describe('sign in', () => {
  it('shows the login page when there is no session', () => {
    useAuthStore.setState({ registrationNumber: null, token: null });
    mockApi(healthy);
    renderWithProviders(<App />);

    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    expect(screen.queryByTestId('shuttle-map')).not.toBeInTheDocument();
  });

  it('opens the app once signed in', async () => {
    mockApi(healthy);
    renderWithProviders(<App />);

    expect(await screen.findByTestId('shuttle-map')).toBeInTheDocument();
    expect(screen.getByText('24MID0159')).toBeInTheDocument();
  });

  it('signs out again', async () => {
    mockApi(healthy);
    renderWithProviders(<App />);

    await userEvent.click(await screen.findByRole('button', { name: /sign out/i }));

    expect(screen.getByRole('button', { name: /^sign in$/i })).toBeInTheDocument();
  });
});
