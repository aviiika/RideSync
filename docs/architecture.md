# Architecture

How RideSync is put together, and why. This is a living document: when a
decision changes, it changes here.

> Telemetry in this system is **simulated**. Nothing reads a real vehicle. The
> architecture is shaped so a real fleet feed can replace the simulation
> without the frontend changing, and section 12 says exactly where that seam
> is — but the current numbers come from a state machine, not from GPS.

---

## 1. Shape of the system

```text
        MapLibre (GeoJSON layers, rAF interpolation)
                          ▲
        Zustand store ────┘        TanStack Query
        (live positions)           (routes, ETAs, controls)
                 ▲                          ▲
          WebSocket /ws/shuttles      REST /routes /shuttles /simulation
                 ▲                          ▲
        ┌────────┴──────────────────────────┴────────┐
        │                FastAPI                     │
        │   routers → services → repository          │
        └────────┬───────────────────────────────────┘
                 │
        ShuttleService  ── composes ──┬── SimulationEngine  (where)
                                      ├── EtaEngine         (when)
                                      └── recommend()       (so what)
                                              │
                                        RouteGeometry
                                              │
                                          geo/distance
```

Dependencies point one way: `api → services → data → models`. Nothing below the
API layer imports FastAPI, which is why every service can be constructed
directly in a test with no HTTP anywhere.

---

## 2. The three questions

The product answers three questions, and the code keeps them apart because they
have different failure modes and different futures.

| Question | Owner | Nature |
| --- | --- | --- |
| Where is the shuttle? | `SimulationEngine` | Deterministic state machine |
| When does it arrive? | `EtaEngine` | Estimate; will become a model |
| Should I wait? | `recommend()` | Policy; a business decision |

Collapsing any two would be the obvious shortcut and the expensive mistake. The
ETA becomes a learned model later; the policy thresholds change on a product
whim; the simulation gets replaced by real telemetry. Each of those is a change
to one file today.

---

## 3. Module boundaries

```text
backend/app/
├── models/       Framework-free dataclasses. No I/O, no Pydantic.
├── geo/          Pure functions over coordinates and polylines.
├── simulation/   Advances vehicles. Never sleeps, never reads the network.
├── eta/          Estimates arrival. Protocol + deterministic implementation.
├── services/     Business logic. Composes the above. Knows nothing of HTTP.
├── data/         RouteRepository protocol + JSON implementation.
├── schemas/      Pydantic wire contracts. The API's only vocabulary.
├── realtime/     Connection manager + the loop that ticks and broadcasts.
└── api/          Routers. Translate services ↔ schemas. No logic.
```

Domain models are never serialised directly. `app.schemas` exists so the wire
format and the internal model can move independently — renaming a field for the
UI must not force a rename through the simulation engine.

---

## 4. Coordinates

Two orderings exist in the world and both appear in this system:

- Internally, `Coordinate(latitude, longitude)` — a frozen dataclass that
  **validates its range on construction**. An out-of-range value cannot exist as
  a `Coordinate`, so no service needs a defensive check.
- On the wire and on the map, GeoJSON `[longitude, latitude]` — the order
  MapLibre requires.

Conversion happens only in `Coordinate.from_geojson` / `to_geojson`. Nowhere
else in the codebase is a pair unpacked by hand. A test asserts the wire order
explicitly, because a silent lat/lng swap puts every shuttle in the Indian Ocean
and looks like a data problem rather than a bug.

---

## 5. Position is a distance, not a point

A shuttle's authoritative state is **how far along its route it is** —
`distance_m` plus a direction — not a latitude/longitude pair. Coordinates are
derived from that distance every tick:

```text
distance_m ──► RouteGeometry.locate() ──► (position, segment, bearing)
```

This is what makes teleporting structurally impossible. A shuttle cannot be
somewhere its route does not go, because its position is only ever a projection
of a distance onto its own polyline. The test suite asserts it directly: over
400 ticks, every reported position is within one metre of
`geometry.locate(shuttle.distance_m)`.

`RouteGeometry` precomputes a cumulative distance table per route, so "where is
a vehicle 1,840 m along" and "how far is the next stop" are arithmetic rather
than a walk of the geometry on every tick.

---

## 6. Distance is not ETA

The distinction the product rests on.

A shuttle 20 m away that has just passed your stop is not arriving in seconds —
on a loop it must travel nearly the entire route to come back. So:

- `direct_distance_m` — straight-line haversine. **Displayed, never ranked on.**
- `RouteGeometry.distance_to(from, to, direction)` — travel distance along the
  route in the direction of travel. **What the ETA is computed from.**

`GET /shuttles/nearby` therefore sorts by ETA, not by proximity. Two tests pin
this: one asserts a shuttle just past a stop reports nearly a full lap of
travel, another asserts its ETA is more than ten times that of an identical
shuttle approaching the same stop.

---

## 7. The simulation clock

The engine is a pure state machine. `tick(delta_seconds)` takes elapsed
wall-clock time and returns the new world. It never sleeps, never calls
`time.monotonic()` to decide anything, and never touches the network.

`SimulationRunner` is the only component that sleeps. It measures elapsed time,
calls `tick`, and broadcasts. That split is why the test suite can run an hour
of simulated service in milliseconds.

**Determinism is a product requirement, not tidiness.** A pitch has to be
repeatable, so the same seed always produces the same run, and `reset` restores
the exact starting state mid-demo. A test asserts that two engines with seed 42
agree on every position and heading after 250 ticks, and that seed 99 diverges.

The speed multiplier (1× / 2× / 5×) scales **simulated time only**. It never
changes the tick rate or the broadcast rate, so a fast demo does not become a
network flood. It does mean a tick can cover more ground than the gap between
two stops, which is why stop detection tests the whole travelled interval rather
than comparing positions — otherwise 5× would sail straight past every stop.

---

## 8. ETA

```text
ETA = remaining_route_distance / effective_speed
      + dwell_seconds × intervening_stops
      × delay_factor
```

`effective_speed` falls back to the route's scheduled speed when a vehicle
reports below 5 km/h. Without that floor, a shuttle waiting at a stop reports
0 km/h and the estimate diverges to hours.

Two rules about honesty:

- The engine returns `None` — never a plausible-looking number — when the
  shuttle is out of service or stale, or the stop is not on its route. The UI
  renders "ETA unavailable".
- Minutes are rounded. "~4 min", never "3 min 47 sec". The estimate is not that
  precise and displaying it as though it were is a lie the user catches the
  first time a shuttle is late.

Every estimate carries the `EtaFeatures` it was made from and a `source` string,
so the UI can show its working and never has to overclaim.

---

## 9. Real-time delivery

One WebSocket per client, opened once for the life of the page.

**Updates are batched.** One `SHUTTLE_UPDATE` frame carries every shuttle, not
one frame per vehicle. At the 20–50 shuttle target that is one message and one
state commit per tick instead of fifty. This is a deliberate departure from the
specification's sketch, taken to meet its own performance requirement.

A new client is seeded with the current world immediately on connect, so a
freshly opened map is populated rather than blank until the next tick.

Inbound frames are ignored. The client is a viewer; shuttle positions are never
taken from it.

---

## 10. Why movement never re-renders React

Telemetry arrives twice a second. If that drove React state, every frame would
reconcile the tree and the map would stutter under load.

Instead:

1. Frames land in a Zustand store, normalised by id.
2. `ShuttleMap` subscribes to the store **imperatively** — outside React.
3. A `requestAnimationFrame` loop eases each vehicle from its previous position
   to its reported one and writes the result straight into a GeoJSON source.

React renders zero times while shuttles move. Markers are drawn as map-native
GeoJSON layers rather than DOM markers: fifty absolutely positioned elements
repositioned each frame versus one source update and one GPU draw.

Interpolation runs over 500 ms, matched to the broadcast interval — shorter and
the marker arrives early then waits, longer and it visibly lags the reported
position. Easing is smoothstep, so there is no acceleration jolt at either end
of a tick.

---

## 11. Failing loudly

The application must never present stale telemetry as live.

| Failure | Behaviour |
| --- | --- |
| Backend unreachable | "Shuttle service unavailable", retrying in background |
| Socket dropped | "Live connection lost · Reconnecting…" |
| No frame for 10 s | "No recent telemetry · Positions may be out of date" |
| ETA cannot be computed | "ETA unavailable" — never a fabricated number |
| Unknown route or shuttle | 404, not an empty list |
| Invalid coordinates | 422, rejected at the type |
| Map overlay fails to build | Logged to the console; the basemap still renders |

Reconnection uses exponential backoff with jitter and a 10-second ceiling, so a
dead backend does not become a tight reconnect loop, and a recovered one is
picked up within seconds. The backoff resets after a successful connection.

An unknown `route_id` returning an empty list was a real bug found in review:
answering a typo with a confident "no shuttles" hides the mistake from the
caller. It now 404s, with a regression test.

---

## 12. Where the ML model goes

The MVP uses arithmetic and says so. There is no model, and none is claimed.

`EtaEngine` is a `Protocol`. A learned estimator implements the same method,
consumes the same `EtaFeatures`, returns the same `EtaEstimate` with a different
`source`, and is swapped in one line of `api/deps.py`. Nothing above that line
changes.

The features already computed on every request are the ones such a model would
train on: remaining distance, current and effective speed, intervening stops,
dwell, route and stop identity. Adding time-of-day, day-of-week, historical trip
duration and headway is additive.

The target would be `actual_arrival_time − prediction_time`, evaluated with MAE,
RMSE and median absolute error.

**Accuracy from synthetic data would be meaningless and will not be claimed.**
A model trained on this simulation would be learning the simulation's own
arithmetic. Real telemetry has to come first.

---

## 13. Where the real GPS feed goes

`SimulationEngine` owns position. Replacing it means an ingestion component that
writes the same `Shuttle` state, and everything downstream — services, ETA,
recommendation, API, WebSocket, map — is untouched.

The parts that would then become real problems, and are deliberately absent
today: map matching noisy fixes onto route geometry, out-of-order and duplicate
telemetry, vehicles off-route, stop arrival detection by geofence rather than by
interval crossing, and persistence of historical trips.

---

## 14. Storage

Routes and stops are static, so they load from `data/routes/*.json` at startup
and live in memory. Live shuttle state is in-memory by nature.

Access goes through the `RouteRepository` protocol. A PostgreSQL/PostGIS
implementation is a new class plus one line in `api/deps.py` — no service,
router or engine changes.

This was a deliberate choice against the specification's suggested stack. For
three routes and eighteen stops, a database is ceremony: it adds Docker to every
run and a migration step to every demo, in exchange for nothing the JSON does
not already do. The seam is what matters, and the seam is there.

---

## 15. Configuration

Everything environment-specific comes from the environment; see `.env.example`.
`.env` is gitignored and no secret is hard-coded. One `.env` at the repository
root serves both applications — Vite is pointed at it with `envDir: '..'`,
because by default it reads only `frontend/` and silently falls back to
defaults, which is a bug that looks like a network problem.

`CORS_ORIGINS` is annotated `NoDecode` so a plain comma-separated value works.
Without it, pydantic-settings tries to JSON-decode the value and the app crashes
on first run against a `.env` copied from the template — which is exactly how it
was found.

---

## 16. Testing strategy

122 backend tests, 61 frontend tests. The properties worth stating:

**Geospatial** — checked against known values, not against themselves. One
degree of latitude is 111.2 km; the cardinal bearings are 0/90/180/270.

**Simulation** — tests assert what a viewer would notice: no position leaves its
route, no inter-tick jump exceeds 60 m, 5× speed still calls at stops, loops
never reverse, reversing routes do, reset restores exact positions, and the same
seed reproduces the same run.

**Campus containment** — every route point, every stop and every shuttle across
1,200 ticks must sit inside the campus bounding box. The service is a closed
campus network; a route to the railway station is a bug and the suite will say
so.

**Honesty** — that a stale or out-of-service shuttle yields no ETA, that
"unavailable" is rendered rather than a number, and that the UI never claims the
simulated feed is real GPS.

**Frontend** — reconnection backoff with faked timers, store normalisation,
loading/error/empty states, and the demo controls. The map itself needs WebGL
and is stubbed; its logic lives in pure functions that are tested directly.

---

## 17. Decisions taken, with reasons

| Decision | Reason |
| --- | --- |
| Position stored as distance along route, not lat/lng | Makes teleporting structurally impossible |
| Sort "nearby" by ETA, not distance | Nearest on the map is often not the one to wait for |
| Batched WebSocket frames | One state commit per tick instead of fifty |
| Map updated outside React | Movement must not reconcile the component tree |
| Map-native layers, not DOM markers | Scales to the 20–50 vehicle target |
| Client-side interpolation | 2 Hz telemetry, 60 fps expectation |
| JSON seed data, no database | Three routes do not need Postgres; the seam is kept |
| ETA returns `None` rather than a guess | A plausible wrong number is worse than an honest gap |
| Minutes, not seconds | The estimate is not that precise |
| ETA behind a `Protocol` | The model swap is one line, later |
| Deterministic seed | The pitch has to be repeatable |
| Speed multiplier scales simulated time only | A fast demo must not become a network flood |
| Map bounds derived from route data | Editing the network moves the map with it |
| `optimizeDeps.exclude: ['maplibre-gl']` | Vite's optimizer breaks MapLibre's worker; the map fetches a style but never a tile |
| Overlay setup runs on `load` *and* `styledata`, and skips what exists | With a warm cache the style can be ready before the listener attaches; relying on `load` alone left a basemap with no routes on it |

---

## 18. Known gaps

Stated plainly rather than discovered later.

- Rider position is fixed at the Main Gate. No browser geolocation.
- Route geometry is hand-placed approximation of campus roads, not surveyed and
  not road-matched.
- No persistence. A backend restart reseeds the world; no trip history exists,
  which is also why no model can be trained yet.
- No authentication, no rate limiting. The API is open by design for a local
  demo and is not deployable as-is.
- Occupancy is a seeded random value with no dynamics. It is decoration.
- `DELAYED` exists in the status vocabulary but nothing ever sets it.
- Bundle is ~1.2 MB (332 kB gzipped), dominated by MapLibre. No code splitting.
- Frontend tests stub the map, so map interaction — click to select, bounds
  fencing — is not covered by an automated test.
