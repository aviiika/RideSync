import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { ShuttleSnapshot } from '../../types/domain';
import { route, snapshot } from '../../test/fixtures';
import { StopBoard } from './StopBoard';

const stop = route.stops[0]!;

const second: ShuttleSnapshot = {
  ...snapshot,
  shuttle: { ...snapshot.shuttle, id: 'ROUTE-AC-02', name: 'Academic Block Circuit 2' },
  eta: { ...snapshot.eta!, minutes: 9 },
};

describe('StopBoard', () => {
  it('names the stop it is a board for', () => {
    render(
      <StopBoard
        stop={stop}
        arrivals={[snapshot]}
        loading={false}
        error={null}
        onSelectShuttle={vi.fn()}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText('Main Building')).toBeInTheDocument();
    expect(screen.getByText(/departures/i)).toBeInTheDocument();
  });

  it('lists what is due with each ETA', () => {
    render(
      <StopBoard
        stop={stop}
        arrivals={[snapshot, second]}
        loading={false}
        error={null}
        onSelectShuttle={vi.fn()}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText('Academic Block Circuit 1')).toBeInTheDocument();
    expect(screen.getByText('Academic Block Circuit 2')).toBeInTheDocument();
  });

  it('opens a shuttle when one is picked', async () => {
    const onSelectShuttle = vi.fn();
    render(
      <StopBoard
        stop={stop}
        arrivals={[snapshot]}
        loading={false}
        error={null}
        onSelectShuttle={onSelectShuttle}
        onClose={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: /academic block circuit 1/i }));
    expect(onSelectShuttle).toHaveBeenCalledWith('ROUTE-AC-01');
  });

  it('flags a shuttle that is running late', () => {
    const delayed: ShuttleSnapshot = {
      ...snapshot,
      shuttle: { ...snapshot.shuttle, status: 'DELAYED' },
    };

    render(
      <StopBoard
        stop={stop}
        arrivals={[delayed]}
        loading={false}
        error={null}
        onSelectShuttle={vi.fn()}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText(/running late/i)).toBeInTheDocument();
  });

  it('says so when nothing is due, rather than showing an empty list', () => {
    render(
      <StopBoard
        stop={stop}
        arrivals={[]}
        loading={false}
        error={null}
        onSelectShuttle={vi.fn()}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText(/nothing is due/i)).toBeInTheDocument();
  });

  it('shows a loading state', () => {
    render(
      <StopBoard
        stop={stop}
        arrivals={[]}
        loading
        error={null}
        onSelectShuttle={vi.fn()}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText(/checking what is due/i)).toBeInTheDocument();
  });

  it('surfaces an error rather than an empty board', () => {
    render(
      <StopBoard
        stop={stop}
        arrivals={[]}
        loading={false}
        error={new Error('Cannot reach the shuttle service')}
        onSelectShuttle={vi.fn()}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText(/cannot reach the shuttle service/i)).toBeInTheDocument();
  });

  it('can be closed', async () => {
    const onClose = vi.fn();
    render(
      <StopBoard
        stop={stop}
        arrivals={[snapshot]}
        loading={false}
        error={null}
        onSelectShuttle={vi.fn()}
        onClose={onClose}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: /close departure board/i }));
    expect(onClose).toHaveBeenCalled();
  });
});
