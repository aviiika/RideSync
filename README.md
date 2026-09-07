# RideSync

**Real-time shuttle tracking and ETA simulation platform.**

Open the app and know, in about five seconds, which shuttle to take and how long
you need to wait: where every shuttle is, which one is nearest, how far away it
is, which way it is heading, when it arrives, and whether waiting is worthwhile.

> **Telemetry in this project is simulated, not real GPS.** The architecture is
> deliberately shaped so simulated telemetry can be replaced by a real fleet feed
> without rewriting the frontend — but nothing here reads a real vehicle.

---

## Status

| Phase | Scope | State |
| --- | --- | --- |
| 1 | Repository discovery | Done |
| 2 | Skeleton — backend, frontend, seed data, docs | Done |
| 3 | Live map: geospatial, simulation, ETA, recommendation, WebSocket, demo controls | Done |
| 4 | Makefile, CI workflow, architecture document | Done |
| 5 | Route filtering, live header, demo script | Done |
| 6 | Rider location and responsive layout | Done |
| 7 | Stop departure boards and delay injection | Done |
| 8 | Walking model and ETA confidence | Done |
| 9 | Trip history and measured ETA error | Done |

---

## Architecture

[`docs/demo-script.md`](docs/demo-script.md) is the three-minute pitch
run-through, with the exact clicks, what to say, the questions to expect and
what to do when something breaks on stage.

[`docs/architecture.md`](docs/architecture.md) is the full design document —
module boundaries, why position is stored as a distance along a route, why
"nearby" is ranked by ETA rather than proximity, where a learned ETA model and
a real GPS feed would attach, the decisions taken with their reasons, and the
known gaps.

```text
Map rendering (MapLibre)
        ↓
Frontend state (Zustand / TanStack Query)
        ↓
REST + WebSocket
        ↓
Backend services (FastAPI)
        ↓
Simulation engine
        ↓
Geospatial engine
        ↓
ETA engine
```

Each layer is independently testable. Business logic never lives in a React
component, and the frontend is never the authoritative source of shuttle state.

```text
RideSync/
├── backend/            FastAPI service
│   ├── app/
│   │   ├── api/        HTTP layer — routers only
│   │   ├── data/       Repository protocol + JSON implementation
│   │   ├── models/     Framework-free domain dataclasses
│   │   ├── schemas/    Pydantic wire contracts
│   │   └── services/   Business logic
│   └── tests/
├── frontend/           React + TypeScript + Vite
├── data/routes/        Seed routes, stops and geometry (JSON)
└── docs/
```

### Storage

Routes and stops are static, so the MVP reads them from `data/routes/*.json` and
keeps live shuttle state in memory inside the simulation engine. Access goes
through the `RouteRepository` protocol, so a PostgreSQL/PostGIS implementation
can be added later without touching the services, API or simulation engine.

---

## Requirements

- Python 3.11+ (3.13 recommended)
- Node.js 20+
- No database, no Docker, no API keys

---

## Setup

Copy the environment template — `.env` is gitignored and holds no secrets today,
but the app reads its configuration from it:

```powershell
Copy-Item .env.example .env
```

### Backend

```powershell
cd backend
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

### Frontend

```powershell
cd frontend
npm install
```

---

## Run

Two terminals.

**Terminal 1 — API** (from `backend/`):

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — web app** (from `frontend/`):

```powershell
npm run dev
```

Then open http://localhost:5173. Interactive API docs are at
http://localhost:8000/docs.

---

## Verify

Backend (from `backend/`):

```powershell
.venv\Scripts\python.exe -m pytest
```

```powershell
.venv\Scripts\python.exe -m ruff check .
```

Frontend (from `frontend/`):

```powershell
npm run typecheck
```

```powershell
npm run lint
```

```powershell
npm run test
```

```powershell
npm run build
```

These are exactly the commands CI runs on every push and pull request; see
[`.github/workflows/ci.yml`](.github/workflows/ci.yml).

A `Makefile` wraps all of them — `make check` runs lint, typecheck, tests and
build together. It is a convenience only: `make` is not installed by default on
Windows, and every target maps to a command documented above.

---

## API

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/auth/login` | Sign in with a registration number |
| GET | `/auth/me` | Confirm a stored session is still valid |
| GET | `/health` | Liveness plus the number of routes loaded |
| GET | `/routes` | Every route with geometry and stops |
| GET | `/routes/{route_id}` | One route |
| GET | `/stops` | Every stop, optional `?route_id=` filter |
| GET | `/shuttles` | Every live shuttle, optional `?route_id=` filter |
| GET | `/shuttles/nearby` | Shuttles ranked by arrival time at the rider's stop |
| GET | `/shuttles/nearest` | The single shuttle worth waiting for |
| GET | `/shuttles/{id}` | One shuttle, described relative to the rider |
| GET | `/stops/{id}/arrivals` | Departure board: what is due at one stop |
| GET | `/metrics/eta` | Measured ETA error, against recorded arrivals |
| POST | `/simulation/delay` | Slow one shuttle, to demonstrate the delayed path |
| POST | `/simulation/clear-delays` | Return every shuttle to normal service |
| GET | `/simulation` | Simulation clock state |
| POST | `/simulation/start` · `/pause` · `/reset` · `/speed` | Demo controls |
| WS | `/ws/shuttles` | Live telemetry, one batched frame per tick |

`/shuttles/nearby` and `/shuttles/nearest` require `latitude` and `longitude`
query parameters. Results are ordered by **ETA, not distance** — a shuttle
80 m away that has just passed your stop is not the one to wait for.

Route geometry is returned in GeoJSON `[longitude, latitude]` order, which is
what MapLibre expects. Stops carry explicit `latitude` / `longitude` fields.

---

## Configuration

All settings come from the environment; see `.env.example`. No secret is ever
hard-coded, and `.env` is gitignored.

| Variable | Purpose |
| --- | --- |
| `CORS_ORIGINS` | Origins allowed to call the API |
| `SIMULATION_TICK_MS` | Simulation tick interval (250–1000 recommended) |
| `SIMULATION_SEED` | Seed making demo runs deterministic and repeatable |
| `SHUTTLES_PER_ROUTE` | Vehicles spawned on each route |
| `DWELL_SECONDS` | Seconds a shuttle waits at each stop |
| `ETA_DELAY_FACTOR` | Multiplier padding ETAs for traffic and boarding |
| `VITE_API_URL` | REST base URL for the browser |
| `VITE_WS_URL` | WebSocket URL for live telemetry |
| `AUTH_SECRET` | Signing key for session tokens |
| `SESSION_HOURS` | How long a sign-in lasts |
| `WALKING_SPEED_KMH` | Pace used to decide whether a stop is reachable in time |
| `DATABASE_URL` | Trip history (SQLite; the file is gitignored) |
| `HISTORY_ENABLED` | Turn history recording off entirely |
| `VITE_MAP_STYLE_URL` | MapLibre style (OpenFreeMap Liberty by default, no key) |

---

## Demo data

Three routes, all **inside the VIT Vellore campus**, defined in
`data/routes/`. Nothing leaves the gates:

| Route | Name | Stops | Serves | End of route |
| --- | --- | --- | --- | --- |
| `ROUTE-MH` | Main Gate - Men's Hostel | 13 | Mess and blocks M, A, B, D, J, K, Q — via the academic blocks | Reverses |
| `ROUTE-LH` | Main Gate - Ladies Hostel | 8 | Blocks G, A, F, S and the mess | Reverses |
| `ROUTE-AC` | Academic Block Circuit | 9 | Main Building, Library, SMV, Anna Auditorium, TT, Gandhi Block, PRP, MGR, SJT | Loops |

Thirty stops. Routes are named for the journey they make, so a shuttle
announces where it is going: *"Main Gate - Men's Hostel 2"*.

### The coordinates are estimates — here is how to make them exact

Every position is hand-placed from the campus layout, not surveyed. The
footprint is about **860 m east-west by 670 m north-south**, which is campus
scale, but individual buildings will be tens of metres out.

Correcting one takes about ten seconds:

1. Right-click the building in Google Maps and click the latitude/longitude to
   copy it.
2. Paste it into that stop's `latitude` and `longitude` in the route JSON.
3. Update the matching entry in `geometry` — **note the order is reversed
   there**, `[longitude, latitude]`, because that is what MapLibre expects.
4. Re-run the inspector below.

Nothing else needs touching. The map frames and fences itself to the data,
distances are computed from it, and the ETAs follow.

### Checking the network

From `backend/`:

```powershell
.venv\Scripts\python.exe scripts/inspect_network.py
```

It prints each route's length, the distance between consecutive stops, one lap
at the route's speed, and the network's footprint and centre — so the numbers
can be compared against Google Maps rather than trusted because they look
plausible. To check one place against every other:

```powershell
.venv\Scripts\python.exe scripts/inspect_network.py --stop "PRP Block"
```

## Signing in

The app opens on a sign-in page. Enter a registration number — for example
`24MID0159` — and any password.

> **This identifies you; it does not authenticate you.** Any registration
> number and any password are accepted. Sign-in exists so the app knows who to
> greet and whose settings to remember — it protects nothing, the shuttle data
> is the same for everyone, and the API endpoints are deliberately not gated
> behind it.

What is done properly, because it costs nothing: the registration number is
normalised, so `24mid0159` and `  24MID0159  ` are one identity; and the session
token is HMAC-signed with an expiry, so a session cannot be forged or extended
by editing browser storage. Set `AUTH_SECRET` anywhere that matters.

## Where you are standing

Every ETA on screen is relative to one point. By default that is the Main Gate,
but it can be moved:

- **Search** — type a campus place ("PRP", "hostel", "MGR") and pick it. There
  is no geocoder behind this and there does not need to be: a campus has a
  known list of places, and searching the stops the service actually calls at
  cannot return somewhere no shuttle goes.
- **Set on map** — tap anywhere on campus to stand there
- **Use my device location** — asks the browser, and refuses a fix outside
  campus rather than producing ETAs that cannot apply
- **Crosshair** — back to the Main Gate

The chosen spot is remembered across reloads, so a demo that has been set up
stays set up. Moving it recomputes the nearest stop, every ETA and the ranking.

Shuttles are then grouped by distance - **Nearby (within 400 m)** and **Further
away** - while staying ordered by arrival inside each group. Distance is what
you glance at; arrival is what decides the answer.

## Is it worth waiting?

Three things beyond the ETA go into the answer:

- **The walk.** A shuttle arriving in two minutes is no use if the stop is a
  five-minute walk away, and the app says so rather than telling you to run for
  something you cannot catch.
- **Confidence.** Every estimate carries a coarse band with its reason: close
  and direct is high, far away with several stops on the way is low, and a
  shuttle already running late is always low. It is a heuristic, not a
  probability, and the wording never pretends otherwise.
- **Measured error.** The app records every ETA it commits to and every actual
  arrival, then scores one against the other. The panel shows the running mean
  absolute error, labelled as measured against simulated arrivals.

## Tap a stop

Selecting a stop opens its departure board - what is due here, soonest first.
Only shuttles whose route calls at that stop can appear, however near anything
else happens to be.

## On a phone

The layout is map-first at every width. On a narrow screen the detail panel
becomes a sheet that collapses to a single line — *"Men's Hostel Shuttle 1 ·
arriving now"* — leaving the map the whole screen. Tap the line to bring the
detail back.

## How the demo behaves

The simulation starts running as soon as the API boots, so the map is alive the
moment the page opens. Shuttles travel along route geometry, dwell at stops,
loop or reverse at the end of a route, and report heading and speed. Positions
are broadcast twice a second and interpolated in the browser, so markers glide
rather than jump.

Given the same seed, every run is identical — which is what makes the pitch
repeatable. **Reset** returns to the exact starting state.
