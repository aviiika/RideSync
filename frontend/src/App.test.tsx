import { screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { App } from './App';
import { renderWithProviders } from './test/utils';

function mockFetch(handler: (path: string) => { ok: boolean; body: unknown }) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const { ok, body } = handler(String(input));
      return { ok, status: ok ? 200 : 500, json: async () => body } as Response;
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

const ROUTES = [
  { id: 'ROUTE-A', name: 'Main Campus Loop', color: '#2563eb', stops: [{}, {}, {}] },
];

describe('App', () => {
  it('shows a loading state before data arrives', () => {
    mockFetch(() => ({ ok: true, body: [] }));
    renderWithProviders(<App />);
    expect(screen.getByText(/loading routes/i)).toBeInTheDocument();
  });

  it('lists routes once loaded and reports the service as online', async () => {
    mockFetch((path) =>
      path.includes('/health')
        ? { ok: true, body: { status: 'ok', version: '0.1.0', routes_loaded: 1 } }
        : { ok: true, body: ROUTES },
    );

    renderWithProviders(<App />);

    expect(await screen.findByText('Main Campus Loop')).toBeInTheDocument();
    expect(screen.getByText('3 stops')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/service online/i)).toBeInTheDocument());
  });

  it('shows an error state instead of failing silently', async () => {
    mockFetch(() => ({ ok: false, body: {} }));
    renderWithProviders(<App />);
    expect(await screen.findByText(/could not load routes/i)).toBeInTheDocument();
  });

  it('shows an empty state when no routes are configured', async () => {
    mockFetch((path) =>
      path.includes('/health')
        ? { ok: true, body: { status: 'ok', version: '0.1.0', routes_loaded: 0 } }
        : { ok: true, body: [] },
    );

    renderWithProviders(<App />);
    expect(await screen.findByText(/no routes are configured/i)).toBeInTheDocument();
  });
});
