import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { snapshot } from '../../test/fixtures';
import { EtaBadge } from './EtaBadge';
import { NearestShuttleCard } from './NearestShuttleCard';
import { RecommendationPill } from './RecommendationPill';
import { ShuttleDetailsPanel } from './ShuttleDetailsPanel';

describe('NearestShuttleCard', () => {
  it('leads with the ETA', () => {
    render(<NearestShuttleCard snapshot={snapshot} onSelect={vi.fn()} />);
    expect(screen.getByText('~4')).toBeInTheDocument();
    expect(screen.getByText('min')).toBeInTheDocument();
  });

  it('shows distance, destination stop and heading', () => {
    render(<NearestShuttleCard snapshot={snapshot} onSelect={vi.fn()} />);

    expect(screen.getByText('1.2 km')).toBeInTheDocument();
    expect(screen.getByText('Main Building')).toBeInTheDocument();
    expect(screen.getByText(/heading toward anna auditorium/i)).toBeInTheDocument();
  });

  it('shows the recommendation', () => {
    render(<NearestShuttleCard snapshot={snapshot} onSelect={vi.fn()} />);
    expect(screen.getByText('Worth waiting')).toBeInTheDocument();
  });

  it('selects the shuttle when clicked', async () => {
    const onSelect = vi.fn();
    render(<NearestShuttleCard snapshot={snapshot} onSelect={onSelect} />);

    await userEvent.click(screen.getByRole('button'));
    expect(onSelect).toHaveBeenCalledWith('ROUTE-AC-01');
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

describe('walking model and confidence', () => {
  it('warns when the shuttle arrives before you could reach the stop', () => {
    render(
      <RecommendationPill
        recommendation={{
          level: 'TOO_TIGHT',
          label: "You won't make it",
          detail: 'The stop is about 9 min away on foot and this one arrives before that.',
        }}
        showDetail
      />,
    );

    expect(screen.getByText(/won't make it/i)).toBeInTheDocument();
    expect(screen.getByText(/9 min away on foot/i)).toBeInTheDocument();
  });

  it('shows the confidence band and its reason in the details panel', () => {
    render(
      <ShuttleDetailsPanel live={undefined} snapshot={snapshot} onClose={vi.fn()} />,
    );

    expect(screen.getByText('Medium confidence')).toBeInTheDocument();
    expect(screen.getByText(/could shift this by a minute/i)).toBeInTheDocument();
  });

  it('shows the walk to the stop', () => {
    render(
      <ShuttleDetailsPanel live={undefined} snapshot={snapshot} onClose={vi.fn()} />,
    );

    expect(screen.getByText(/walk to stop/i)).toBeInTheDocument();
    expect(screen.getByText('2 min')).toBeInTheDocument();
  });

  it('offers a delay control only when the demo provides one', async () => {
    const onInjectDelay = vi.fn();
    render(
      <ShuttleDetailsPanel
        live={undefined}
        snapshot={snapshot}
        onClose={vi.fn()}
        onInjectDelay={onInjectDelay}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: /delay this shuttle/i }));
    expect(onInjectDelay).toHaveBeenCalledWith('ROUTE-AC-01');
  });

  it('does not offer to delay a shuttle that is already late', () => {
    render(
      <ShuttleDetailsPanel
        live={{ ...snapshot.shuttle, status: 'DELAYED' }}
        snapshot={snapshot}
        onClose={vi.fn()}
        onInjectDelay={vi.fn()}
      />,
    );

    expect(screen.getByRole('button', { name: /running late/i })).toBeDisabled();
  });
});
