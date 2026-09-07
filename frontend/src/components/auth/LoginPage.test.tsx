import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { LoginPage } from './LoginPage';

describe('LoginPage', () => {
  it('asks for a registration number and a password', () => {
    render(<LoginPage onSubmit={vi.fn()} pending={false} error={null} />);

    expect(screen.getByLabelText(/registration number/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
  });

  it('is honest that this is not a security check', () => {
    render(<LoginPage onSubmit={vi.fn()} pending={false} error={null} />);

    expect(screen.getByText(/not a security check/i)).toBeInTheDocument();
    expect(screen.getByText(/any password is accepted/i)).toBeInTheDocument();
  });

  it('does not imply the password has to be anything in particular', () => {
    render(<LoginPage onSubmit={vi.fn()} pending={false} error={null} />);
    expect(screen.getByLabelText(/^password$/i)).toHaveAttribute('placeholder', 'Any password');
  });

  it('will not submit until both fields are filled', async () => {
    const onSubmit = vi.fn();
    render(<LoginPage onSubmit={onSubmit} pending={false} error={null} />);

    const button = screen.getByRole('button', { name: /sign in/i });
    expect(button).toBeDisabled();

    await userEvent.type(screen.getByLabelText(/registration number/i), '24MID0159');
    expect(button).toBeDisabled();

    await userEvent.type(screen.getByLabelText(/^password$/i), '24MID0159');
    expect(button).toBeEnabled();
  });

  it('submits what was typed, whatever the password is', async () => {
    const onSubmit = vi.fn();
    render(<LoginPage onSubmit={onSubmit} pending={false} error={null} />);

    await userEvent.type(screen.getByLabelText(/registration number/i), '24MID0159');
    await userEvent.type(screen.getByLabelText(/^password$/i), 'hunter2');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

    expect(onSubmit).toHaveBeenCalledWith('24MID0159', 'hunter2');
  });

  it('shows the server’s message when sign-in is refused', () => {
    render(
      <LoginPage onSubmit={vi.fn()} pending={false} error="Enter your registration number." />,
    );

    expect(screen.getByRole('alert')).toHaveTextContent(/enter your registration number/i);
  });

  it('shows progress and blocks a second submit while signing in', () => {
    render(<LoginPage onSubmit={vi.fn()} pending error={null} />);

    expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled();
  });

  it('masks the password field', () => {
    render(<LoginPage onSubmit={vi.fn()} pending={false} error={null} />);
    expect(screen.getByLabelText(/^password$/i)).toHaveAttribute('type', 'password');
  });
});
