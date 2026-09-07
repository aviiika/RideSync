/**
 * Sign in.
 *
 * Any registration number and any password are accepted - this identifies a
 * student so the app can remember their settings, it does not authenticate
 * anyone. The page says so rather than implying a check that is not there.
 */

import { AlertTriangle, Bus, Loader2 } from 'lucide-react';
import { useState } from 'react';

interface LoginPageProps {
  onSubmit: (registrationNumber: string, password: string) => void;
  pending: boolean;
  error: string | null;
}

export function LoginPage({ onSubmit, pending, error }: LoginPageProps) {
  const [registrationNumber, setRegistrationNumber] = useState('');
  const [password, setPassword] = useState('');

  const canSubmit = registrationNumber.trim() !== '' && password.trim() !== '' && !pending;

  return (
    <div className="flex min-h-full items-center justify-center bg-surface-muted p-6">
      <div className="w-full max-w-sm">
        <header className="flex items-center gap-2.5">
          <Bus className="h-7 w-7 text-brand" aria-hidden="true" />
          <div>
            <h1 className="text-xl font-semibold leading-tight">RideSync</h1>
            <p className="text-xs text-muted">VIT Vellore campus shuttle</p>
          </div>
        </header>

        <form
          className="mt-5 rounded-panel border border-border bg-surface p-5 shadow-sm"
          onSubmit={(event) => {
            event.preventDefault();
            if (canSubmit) {
              onSubmit(registrationNumber, password);
            }
          }}
        >
          <h2 className="text-base font-semibold">Sign in</h2>
          <p className="mt-1 text-xs text-muted">
            Enter your registration number and a password to continue.
          </p>

          <div className="mt-4 flex flex-col gap-3">
            <Field
              id="registration-number"
              label="Registration number"
              value={registrationNumber}
              placeholder="24MID0159"
              autoFocus
              onChange={setRegistrationNumber}
            />

            <Field
              id="password"
              label="Password"
              type="password"
              value={password}
              placeholder="Any password"
              onChange={setPassword}
            />
          </div>

          {error ? (
            <p
              role="alert"
              className="mt-3 flex items-start gap-2 rounded-lg bg-critical/10 p-2.5 text-sm text-critical"
            >
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={!canSubmit}
            className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-brand px-3 py-2.5 text-sm font-medium text-white transition hover:bg-brand/90 disabled:opacity-50"
          >
            {pending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
            {pending ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="mt-4 px-1 text-xs text-muted">
          Signing in identifies you so the app can remember where you wait. It is not a
          security check — any password is accepted, and shuttle data is the same for
          everyone.
        </p>
      </div>
    </div>
  );
}

function Field({
  id,
  label,
  value,
  placeholder,
  type = 'text',
  autoFocus = false,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  placeholder: string;
  type?: string;
  autoFocus?: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label htmlFor={id} className="text-xs font-medium text-muted">
        {label}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        placeholder={placeholder}
        // Registration numbers are upper case; typing them in lower case is
        // normal and the server normalises, so this is cosmetic only.
        autoCapitalize="characters"
        autoComplete={type === 'password' ? 'current-password' : 'username'}
        // eslint-disable-next-line jsx-a11y/no-autofocus
        autoFocus={autoFocus}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-lg border border-border px-3 py-2 text-sm outline-none focus:border-brand"
      />
    </div>
  );
}
