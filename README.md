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
| 3 | Map: routes, stops, user location | Next |
| 4 | Simulation engine | Planned |
| 5 | Geospatial + ETA engines | Planned |
| 6 | WebSocket + live updates | Planned |
| 7 | UX polish, recommendation | Planned |
| 8 | Testing | Planned |
| 9 | Pitch/demo mode | Planned |

---

## Architecture

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
npm run build
```

---

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness plus the number of routes loaded |
| GET | `/routes` | Every route with geometry and stops |
| GET | `/routes/{route_id}` | One route |
| GET | `/stops` | Every stop, optional `?route_id=` filter |

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
| `VITE_API_URL` | REST base URL for the browser |
| `VITE_WS_URL` | WebSocket URL for live telemetry |
| `VITE_MAP_STYLE_URL` | MapLibre style (OpenFreeMap Liberty by default, no key) |

---

## Demo data

Three routes around the VIT Vellore campus, defined in `data/routes/`:

| Route | Name | Stops | Behaviour at the end |
| --- | --- | --- | --- |
| `ROUTE-A` | Main Campus Loop | 6 | Loops |
| `ROUTE-B` | North Hostel Shuttle | 5 | Reverses |
| `ROUTE-C` | Katpadi Station Express | 4 | Reverses |

To change the network, edit or add a JSON file in `data/routes/` — the loader
validates geometry, stop ordering and coordinate ranges on startup.
