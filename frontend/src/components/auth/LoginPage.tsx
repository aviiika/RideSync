/**
 * Sign in.
 *
 * The first screen anyone sees, so it does two jobs: get out of the way in
 * about five seconds, and say what the product is before the map has loaded.
 * The left panel previews the campus network; the right is the form.
 *
 * Any registration number and any password are accepted - this identifies a
 * student so the app can remember their settings, it does not authenticate
 * anyone. The page says so rather than implying a check that is not there.
 */

import { AlertTriangle, ArrowRight, Bus, Eye, EyeOff, IdCard, Loader2, Lock } from 'lucide-react';
import { useState, type ComponentType } from 'react';

import { CampusMotif } from './CampusMotif';

interface LoginPageProps {
  onSubmit: (registrationNumber: string, password: string) => void;
  pending: boolean;
  error: string | null;
}

/** The network as it stands, so the page states something true rather than filler. */
const NETWORK = [
  { label: 'Academic Block Circuit', color: '#2563eb' },
  { label: "Main Gate - Men's Hostel", color: '#16a34a' },
  { label: 'Main Gate - Ladies Hostel', color: '#db2777' },
];

export function LoginPage({ onSubmit, pending, error }: LoginPageProps) {
  const [registrationNumber, setRegistrationNumber] = useState('');
  const [password, setPassword] = useState('');
  const [revealPassword, setRevealPassword] = useState(false);

  const canSubmit = registrationNumber.trim() !== '' && password.trim() !== '' && !pending;

  return (
    <div className="grid min-h-full lg:grid-cols-[1.1fr_1fr]">
      <ShowcasePanel />

      <main className="flex items-center justify-center bg-surface px-6 py-10">
        <div className="w-full max-w-sm">
          {/* The brand shows here only where the showcase panel is not visible. */}
          <div className="mb-8 flex items-center gap-2.5 lg:hidden">
            <Bus className="h-6 w-6 text-brand" aria-hidden="true" />
            <div>
              <p className="text-base font-semibold leading-tight">RideSync</p>
              <p className="text-xs text-muted">VIT Vellore campus shuttle</p>
            </div>
          </div>

          <h2 className="text-2xl font-semibold tracking-tight">Sign in</h2>
          <p className="mt-1.5 text-sm text-muted">
            Enter your registration number and a password to continue.
          </p>

          <form
            className="mt-6 flex flex-col gap-4"
            onSubmit={(event) => {
              event.preventDefault();
              if (canSubmit) {
                onSubmit(registrationNumber, password);
              }
            }}
          >
            <Field
              id="registration-number"
              label="Registration number"
              Icon={IdCard}
              value={registrationNumber}
              placeholder="24MID0159"
              autoFocus
              onChange={setRegistrationNumber}
            />

            <Field
              id="password"
              label="Password"
              Icon={Lock}
              type={revealPassword ? 'text' : 'password'}
              value={password}
              placeholder="Any password"
              onChange={setPassword}
              trailing={
                <button
                  type="button"
                  onClick={() => setRevealPassword((shown) => !shown)}
                  aria-label={revealPassword ? 'Hide password' : 'Show password'}
                  className="rounded-full p-1 text-muted transition hover:text-ink"
                >
                  {revealPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              }
            />

            {error ? (
              <p
                role="alert"
                className="flex items-start gap-2 rounded-lg bg-critical/10 p-3 text-sm text-critical"
              >
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                {error}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={!canSubmit}
              className="group mt-1 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-brand px-3 py-3 text-sm font-medium text-white shadow-sm transition hover:bg-brand/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40 disabled:opacity-50"
            >
              {pending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  Signing in…
                </>
              ) : (
                <>
                  Sign in
                  <ArrowRight
                    className="h-4 w-4 transition-transform group-hover:translate-x-0.5"
                    aria-hidden="true"
                  />
                </>
              )}
            </button>
          </form>

          <p className="mt-6 border-t border-border pt-4 text-xs leading-relaxed text-muted">
            Signing in identifies you so the app can remember where you wait. It is not a
            security check — any password is accepted, and shuttle data is the same for
            everyone.
          </p>
        </div>
      </main>
    </div>
  );
}

/** The half of the screen that sells the product, on wide screens only. */
function ShowcasePanel() {
  return (
    <aside className="relative hidden overflow-hidden bg-ink text-white lg:flex lg:flex-col lg:justify-between">
      {/* The motif sits high and right, with a wash over it, so the copy below
          stays crisp rather than competing with the artwork. */}
      <div className="pointer-events-none absolute -right-28 -top-24 h-[32rem] w-[32rem] opacity-55">
        <CampusMotif />
      </div>
      <div
        className="pointer-events-none absolute inset-0 bg-gradient-to-t from-ink via-ink/85 to-transparent"
        aria-hidden="true"
      />

      <div className="relative p-10">
        <div className="flex items-center gap-2.5">
          <Bus className="h-7 w-7" aria-hidden="true" />
          <div>
            <p className="text-lg font-semibold leading-tight">RideSync</p>
            <p className="text-xs text-white/60">VIT Vellore campus shuttle</p>
          </div>
        </div>
      </div>

      <div className="relative max-w-md p-10">
        <h1 className="text-3xl font-semibold leading-tight tracking-tight">
          Know exactly when your shuttle arrives.
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-white/70">
          Live positions across campus, ETAs that account for the walk to your stop, and a
          straight answer to the only question that matters — is it worth waiting?
        </p>

        <ul className="mt-7 flex flex-col gap-2.5">
          {NETWORK.map((route) => (
            <li key={route.label} className="flex items-center gap-2.5 text-sm text-white/80">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: route.color }}
                aria-hidden="true"
              />
              {route.label}
            </li>
          ))}
        </ul>

        <dl className="mt-8 flex gap-8 border-t border-white/15 pt-5">
          <Stat value="3" label="routes" />
          <Stat value="31" label="stops" />
          <Stat value="2 Hz" label="live updates" />
        </dl>

        <p className="mt-6 text-xs text-white/45">
          Telemetry is simulated, not real GPS.
        </p>
      </div>
    </aside>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <dt className="sr-only">{label}</dt>
      <dd>
        <span className="block text-xl font-semibold">{value}</span>
        <span className="text-xs text-white/55">{label}</span>
      </dd>
    </div>
  );
}

function Field({
  id,
  label,
  Icon,
  value,
  placeholder,
  type = 'text',
  autoFocus = false,
  trailing,
  onChange,
}: {
  id: string;
  label: string;
  Icon: ComponentType<{ className?: string }>;
  value: string;
  placeholder: string;
  type?: string;
  autoFocus?: boolean;
  trailing?: React.ReactNode;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label htmlFor={id} className="text-xs font-medium text-muted">
        {label}
      </label>

      <div className="mt-1.5 flex items-center gap-2 rounded-lg border border-border px-3 py-2.5 transition focus-within:border-brand focus-within:ring-2 focus-within:ring-brand/15">
        <Icon className="h-4 w-4 shrink-0 text-muted" />
        <input
          id={id}
          type={type}
          value={value}
          placeholder={placeholder}
          // Registration numbers are upper case; typing them in lower case is
          // normal and the server normalises, so this is cosmetic only.
          autoCapitalize="characters"
          autoComplete={id === 'password' ? 'current-password' : 'username'}
          // eslint-disable-next-line jsx-a11y/no-autofocus
          autoFocus={autoFocus}
          onChange={(event) => onChange(event.target.value)}
          className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted"
        />
        {trailing}
      </div>
    </div>
  );
}
