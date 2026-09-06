import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { snapshot } from '../../test/fixtures';
import { EtaBadge } from './EtaBadge';
import { NearestShuttleCard } from './NearestShuttleCard';
import { RecommendationPill } from './RecommendationPill';

describe('NearestShuttleCard', () => {
  it('leads with the ETA', () => {
    render(<NearestShuttleCard snapshot={snapshot} onSelect={vi.fn()} />);
    expect(screen.getByText('~4')).toBeInTheDocument();
    expect(screen.getByText('min')).toBeInTheDocument();
  });

  it('shows distance, destination stop and heading', () => {
    render(<NearestShuttleCard snapshot={snapshot} onSelect={vi.fn()} />);

    expect(screen.getByText('1.2 km')).toBeInTheDocument();
    expect(screen.getByText('Main Gate')).toBeInTheDocument();
    expect(screen.getByText(/heading toward academic block 1/i)).toBeInTheDocument();
  });

  it('shows the recommendation', () => {
    render(<NearestShuttleCard snapshot={snapshot} onSelect={vi.fn()} />);
    expect(screen.getByText('Worth waiting')).toBeInTheDocument();
  });

  it('selects the shuttle when clicked', async () => {
    const onSelect = vi.fn();
    render(<NearestShuttleCard snapshot={snapshot} onSelect={onSelect} />);

    await userEvent.click(screen.getByRole('button'));
    expect(onSelect).toHaveBeenCalledWith('ROUTE-A-01');
  });
});

describe('EtaBadge', () => {
  it('rounds to whole minutes rather than showing false precision', () => {
    render(<EtaBadge eta={{ ...snapshot.eta!, minutes: 4, seconds: 227.4 }} />);
    expect(screen.getByText('~4')).toBeInTheDocument();
    expect(screen.queryByText(/sec/i)).not.toBeInTheDocument();
  });

  it('says "arriving now" under a minute', () => {
    render(<EtaBadge eta={{ ...snapshot.eta!, minutes: 0, seconds: 12 }} />);
    expect(screen.getByText(/arriving now/i)).toBeInTheDocument();
  });

  it('admits when there is no estimate instead of inventing one', () => {
    render(<EtaBadge eta={null} />);
    expect(screen.getByText(/eta unavailable/i)).toBeInTheDocument();
  });
});

describe('RecommendationPill', () => {
  it.each([
    ['ARRIVING_SOON', 'Arriving soon'],
    ['WORTH_WAITING', 'Worth waiting'],
    ['CONSIDER_WAITING', 'Consider waiting'],
    ['LONG_WAIT', 'Long wait'],
    ['UNAVAILABLE', 'ETA unavailable'],
  ] as const)('renders %s', (level, label) => {
    render(<RecommendationPill recommendation={{ level, label, detail: 'detail' }} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });
});
