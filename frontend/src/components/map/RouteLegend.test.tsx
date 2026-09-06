import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { route } from '../../test/fixtures';
import { RouteLegend } from './RouteLegend';
import { routeFilterExpressions } from './layers';

const routes = [
  route,
  { ...route, id: 'ROUTE-MH', name: "Main Gate - Men's Hostel", color: '#16a34a' },
];

describe('RouteLegend', () => {
  it('names every route, so the colours on the map mean something', () => {
    render(<RouteLegend routes={routes} active={null} onChange={vi.fn()} onRecentre={vi.fn()} />);

    expect(screen.getByRole('button', { name: /all routes/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /academic block circuit/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /main gate - men's hostel/i })).toBeInTheDocument();
  });

  it('isolates a route when one is picked', async () => {
    const onChange = vi.fn();
    render(<RouteLegend routes={routes} active={null} onChange={onChange} onRecentre={vi.fn()} />);

    await userEvent.click(screen.getByRole('button', { name: /main gate - men's hostel/i }));
    expect(onChange).toHaveBeenCalledWith('ROUTE-MH');
  });

  it('clears the filter when the active route is picked again', async () => {
    const onChange = vi.fn();
    render(
      <RouteLegend routes={routes} active="ROUTE-MH" onChange={onChange} onRecentre={vi.fn()} />,
    );

    await userEvent.click(screen.getByRole('button', { name: /main gate - men's hostel/i }));
    expect(onChange).toHaveBeenCalledWith(null);
  });

  it('marks which filter is active', () => {
    render(
      <RouteLegend routes={routes} active="ROUTE-MH" onChange={vi.fn()} onRecentre={vi.fn()} />,
    );

    expect(screen.getByRole('button', { name: /main gate - men's hostel/i })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(screen.getByRole('button', { name: /all routes/i })).toHaveAttribute(
      'aria-pressed',
      'false',
    );
  });

  it('offers a way back to the campus view', async () => {
    const onRecentre = vi.fn();
    render(<RouteLegend routes={routes} active={null} onChange={vi.fn()} onRecentre={onRecentre} />);

    await userEvent.click(screen.getByRole('button', { name: /recentre on campus/i }));
    expect(onRecentre).toHaveBeenCalled();
  });

  it('renders nothing before the network has loaded', () => {
    const { container } = render(
      <RouteLegend routes={[]} active={null} onChange={vi.fn()} onRecentre={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});

describe('routeFilterExpressions', () => {
  it('clears every layer filter when showing the whole network', () => {
    const filters = routeFilterExpressions(null);

    expect(filters['route-line']).toBeNull();
    expect(filters['stop']).toBeNull();
    expect(filters['shuttle-body']).toBeNull();
  });

  it('keeps the selection halo tied to the selected vehicle when unfiltered', () => {
    expect(routeFilterExpressions(null)['shuttle-halo']).toEqual([
      '==',
      ['get', 'selected'],
      true,
    ]);
  });

  it('narrows lines by route id and everything else by route_id', () => {
    const filters = routeFilterExpressions('ROUTE-MH');

    expect(filters['route-line']).toEqual(['==', ['get', 'id'], 'ROUTE-MH']);
    expect(filters['stop']).toEqual(['==', ['get', 'route_id'], 'ROUTE-MH']);
    expect(filters['shuttle-body']).toEqual(['==', ['get', 'route_id'], 'ROUTE-MH']);
  });

  it('combines selection and route for the halo', () => {
    expect(routeFilterExpressions('ROUTE-MH')['shuttle-halo']).toEqual([
      'all',
      ['==', ['get', 'selected'], true],
      ['==', ['get', 'route_id'], 'ROUTE-MH'],
    ]);
  });

  it('covers every filterable layer in both modes', () => {
    expect(Object.keys(routeFilterExpressions(null)).sort()).toEqual(
      Object.keys(routeFilterExpressions('ROUTE-MH')).sort(),
    );
  });
});
