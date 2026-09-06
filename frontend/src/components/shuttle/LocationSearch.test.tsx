import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { Stop } from '../../types/domain';
import { LocationSearch } from './LocationSearch';

function stop(id: string, name: string, latitude = 12.97, longitude = 79.16): Stop {
  return { id, name, route_id: 'ROUTE-AC', sequence: 0, latitude, longitude };
}

const stops: Stop[] = [
  stop('S1', 'Main Gate'),
  stop('S2', 'Technology Tower'),
  stop('S3', 'PRP Block'),
  stop('S4', 'MGR Block'),
  stop('S5', "Men's Hostel A Block"),
  stop('S6', 'Ladies Hostel F Block'),
  stop('S7', 'SJT Block'),
  stop('S8', 'Main Gate'),
];

describe('LocationSearch', () => {
  it('shows where you currently are', () => {
    render(<LocationSearch stops={stops} currentLabel="Main Gate" onPick={vi.fn()} />);
    expect(screen.getByPlaceholderText('Main Gate')).toBeInTheDocument();
  });

  it('suggests campus places once focused', async () => {
    render(<LocationSearch stops={stops} currentLabel="Main Gate" onPick={vi.fn()} />);
    await userEvent.click(screen.getByRole('textbox'));

    expect(screen.getByRole('button', { name: /ladies hostel f block/i })).toBeInTheDocument();
  });

  it('filters as you type', async () => {
    render(<LocationSearch stops={stops} currentLabel="Main Gate" onPick={vi.fn()} />);
    await userEvent.type(screen.getByRole('textbox'), 'prp');

    expect(screen.getByRole('button', { name: /prp block/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /technology tower/i })).not.toBeInTheDocument();
  });

  it('matches on any part of the name, not just the start', async () => {
    render(<LocationSearch stops={stops} currentLabel="Main Gate" onPick={vi.fn()} />);
    await userEvent.type(screen.getByRole('textbox'), 'hostel');

    expect(screen.getByRole('button', { name: /men's hostel a block/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /ladies hostel f block/i })).toBeInTheDocument();
  });

  it('offers each place once, however many routes call there', async () => {
    render(<LocationSearch stops={stops} currentLabel="Somewhere" onPick={vi.fn()} />);
    await userEvent.type(screen.getByRole('textbox'), 'main gate');

    expect(screen.getAllByRole('button', { name: /main gate/i })).toHaveLength(1);
  });

  it('moves the rider when a place is chosen', async () => {
    const onPick = vi.fn();
    render(<LocationSearch stops={stops} currentLabel="Main Gate" onPick={onPick} />);

    await userEvent.type(screen.getByRole('textbox'), 'mgr');
    await userEvent.click(screen.getByRole('button', { name: /mgr block/i }));

    expect(onPick).toHaveBeenCalledWith(expect.objectContaining({ name: 'MGR Block' }));
  });

  it('says so when nothing matches, rather than showing an empty list', async () => {
    render(<LocationSearch stops={stops} currentLabel="Main Gate" onPick={vi.fn()} />);
    await userEvent.type(screen.getByRole('textbox'), 'railway station');

    expect(screen.getByText(/no campus stop matches/i)).toBeInTheDocument();
  });

  it('clears the query', async () => {
    render(<LocationSearch stops={stops} currentLabel="Main Gate" onPick={vi.fn()} />);
    const input = screen.getByRole('textbox');

    await userEvent.type(input, 'prp');
    await userEvent.click(screen.getByRole('button', { name: /clear search/i }));

    expect(input).toHaveValue('');
  });
});
