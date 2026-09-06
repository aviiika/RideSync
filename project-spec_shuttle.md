# ShuttleMap — Project Specification

**Document status:** Build-ready v1
**Primary goal:** Create a polished campus shuttle-tracking web app that lets a user see simulated shuttles on a live map, understand how far away each shuttle is, see an ETA to a selected stop/current location, and quickly decide whether to wait or use another option.
**Demo constraint:** No real GPS feed is required. The demo uses a deterministic server-side shuttle simulator that behaves like a live location feed.

---

## 1. Product definition

### 1.1 Core user story

> “I am at/near a campus shuttle stop. I want to know which shuttle is coming, how many minutes away it is, how far it is from me, and whether waiting makes sense.”

### 1.2 Primary experience

The main screen should feel like a modern ride-hailing map, inspired by the information hierarchy of Ola/Uber but **not a visual copy**:

- Full-screen interactive map.
- User/current location marker.
- Multiple shuttle markers moving along predefined routes.
- Route polylines on the map.
- Selected shuttle/stop bottom sheet or side panel.
- ETA in minutes as the primary value.
- Distance in metres/km as secondary information.
- Shuttle status: `Arriving`, `Nearby`, `On the way`, `Delayed`, `Out of service`.
- “Nearest shuttle” card.
- “Next 3 shuttles” list.
- Last-updated indicator.
- Demo controls hidden behind a clearly marked Demo/Simulator panel.

### 1.3 Demo decision

The demo should be convincing without falsely claiming live GPS. The UI may say:

`LIVE DEMO • SIMULATED LOCATION`

This keeps the experience credible and makes the architecture easy to upgrade to real GPS later.

---

## 2. Non-goals for v1

Do not overbuild these in the initial milestone:

- Real driver accounts.
- Driver navigation.
- Payments.
- Booking/reservations.
- Chat between rider and driver.
- Real-time crowd sensing.
- Complex route optimization for operators.
- Production-grade authentication unless required by deployment.
- Training a “real ML model” without sufficient historical data.

The first milestone must be a robust, beautiful, demoable simulator-backed product.

---

## 3. Recommended architecture

Use a modular monorepo-style structure while keeping deployment simple.

```text
Browser
  |
  | HTTPS / WebSocket
  v
Next.js Web App
  |
  | REST API + WebSocket client
  v
FastAPI Backend
  |\
  | \\-- Simulation Engine (authoritative shuttle state)
  |
  +---- ETA / Distance Service
  |
  +---- Route Service
  |
  +---- WebSocket Manager
  |
  +---- Optional ML ETA Service interface
  |
  v
PostgreSQL + PostGIS
  |
  +---- routes
  +---- stops
  +---- shuttles
  +---- simulator snapshots/events (optional)
```

### Why this architecture

- The frontend remains presentation-focused.
- The backend owns authoritative shuttle state.
- The simulator can later be replaced by a real GPS ingestion service without rewriting the UI.
- PostGIS provides proper geographic types and distance queries.
- WebSockets provide a natural live-feed interface.
- ETA calculation remains testable independently from the map UI.

---

## 4. Tech stack

### Frontend

- **Next.js + TypeScript**
- React
- Tailwind CSS
- shadcn/ui
- MapLibre GL JS for the interactive map
- TanStack Query for API/server-state management
- Zustand only for small client-only UI state where needed
- Zod for runtime validation of client-facing API payloads
- Lucide icons

MapLibre is preferred because it is an open-source TypeScript/WebGL mapping library designed for interactive web maps and supports markers, controls, GeoJSON, vector-tile sources and custom map layers. See the official documentation before implementation. 

### Backend

- **Python + FastAPI**
- Pydantic v2
- SQLAlchemy 2.x
- Alembic for migrations
- PostgreSQL
- PostGIS
- Redis is optional in v1; add only when it solves a demonstrated need
- WebSockets for live simulation updates

### Testing

- Pytest
- HTTPX for FastAPI tests
- Vitest for frontend unit tests
- Playwright for end-to-end flows
- TypeScript strict mode
- Ruff + Black for Python formatting/linting
- ESLint + Prettier for frontend

### DevOps

- Docker + Docker Compose for local development
- `.env.example` committed
- `.env` ignored
- GitHub Actions for CI

### Mapping provider

Use MapLibre as the rendering layer. Do not hard-code the application to one commercial map provider.

For demos, use a proper tile/style provider or self-hosted/approved infrastructure. Do not build a production dependency on public OpenStreetMap/Nominatim infrastructure in a way that violates its usage policies. OSM’s public tile and Nominatim services have usage restrictions and should not be treated as unlimited application APIs.

---

## 5. Repository structure

Preferred structure:

```text
shuttlemap/
├── apps/
│   ├── web/                    # Next.js app
│   └── api/                    # FastAPI app
├── packages/
│   ├── contracts/              # OpenAPI-generated or shared schemas/types
│   └── ui/                     # Optional shared UI primitives
├── simulator/
│   ├── routes/                 # Route definitions / fixtures
│   ├── engine/                 # Simulation logic
│   └── scenarios/              # Demo scenarios
├── infra/
│   ├── docker/
│   └── db/
├── tests/
│   ├── e2e/
│   └── fixtures/
├── docs/
├── .github/workflows/
├── docker-compose.yml
├── .env.example
├── project-spec.md
├── CLAUDE.md
└── README.md
```

If the existing repository already has a sensible structure, **do not reorganize it just for this specification**. Adapt to what exists and explain any structural decision.

---

## 6. Domain model

### Shuttle

```text
id
code/display_name
route_id
status
latitude
longitude
bearing
speed_kph
current_route_position
last_updated_at
simulation_state
```

### Route

```text
id
name
color
polyline/GeoJSON geometry
average_speed_kph
active
```

### Stop

```text
id
route_id
name
latitude
longitude
sequence
```

### Shuttle telemetry event

```text
shuttle_id
timestamp
latitude
longitude
speed_kph
bearing
route_position
source = SIMULATED | GPS
```

### ETA prediction

```text
shuttle_id
destination_type = STOP | USER_LOCATION
eta_seconds
eta_minutes_display
distance_meters
confidence
calculation_method
calculated_at
```

---

## 7. Simulation engine

The simulation engine is the heart of the demo.

### 7.1 Authoritative state

The backend must be authoritative. Do not have each browser independently simulate a shuttle because clients will drift apart.

### 7.2 Tick rate

Default simulation tick: **1 second**.

Broadcast meaningful state updates approximately every 1 second or at a configurable rate. The frontend may interpolate marker animation between updates for smoothness.

### 7.3 Route movement

Represent each route as an ordered geographic path.

For each shuttle:

1. Store route ID.
2. Store progress along the route.
3. Advance progress using speed and elapsed time.
4. Convert route progress to a coordinate.
5. Calculate bearing from consecutive route points.
6. Apply small deterministic location noise for realism.
7. Handle route looping or terminal turnaround.
8. Publish updated state.

### 7.4 Realistic behavior

Include configurable parameters:

- nominal speed
- speed variance
- stop dwell time
- acceleration/deceleration smoothing
- traffic multiplier
- occasional delay event
- GPS noise
- route direction

### 7.5 Demo scenarios

Implement at least:

**Scenario A — Normal traffic**
- Several shuttles moving normally.

**Scenario B — One shuttle arriving**
- One shuttle reaches the user’s selected stop in <2 minutes.

**Scenario C — Delayed shuttle**
- One shuttle receives a temporary delay and its ETA increases.

**Scenario D — Nearest is not fastest**
- A visually closer shuttle is on the wrong section/direction while another shuttle has the best stop ETA.

**Scenario E — Shuttle passes stop**
- Correctly transition to the next arrival.

These scenarios make the demo useful for showing why ETA matters instead of only distance.

---

## 8. Location handling

### Demo mode

Allow the user location to be selected from known campus locations/stops.

Example configuration:

```text
CAMPUS_CENTER
MAIN_GATE
HOSTEL_BLOCK_A
ACADEMIC_BLOCK
LIBRARY
CAFETERIA
```

### Real browser geolocation

Support `navigator.geolocation` behind a user permission flow, but make demo location selection the reliable fallback.

Never block the product because browser geolocation is unavailable or denied.

---

## 9. Routing and geospatial calculations

### Distance

Use geographic calculations consistently. Avoid “straight line means arrival time.”

Distinguish:

- **air distance**: direct great-circle/Haversine distance
- **route distance**: distance remaining along the shuttle route to the target stop
- **ETA**: predicted travel time considering route progress, speed and delays

For shuttle arrival, route distance + route state is the primary signal.

### Nearby classification

Example thresholds (configurable):

```text
< 100 m      = Arriving
100–300 m    = Very Near
300–800 m    = Nearby
> 800 m      = On the way
```

Do not expose these as hard-coded business assumptions throughout the code. Put them in configuration/constants.

---

## 10. ETA engine

### v1: deterministic ETA

Use a transparent, testable ETA formula:

```text
remaining_route_distance
÷
expected_effective_speed
+
expected_stop_dwell
+
known_delay_seconds
=
ETA
```

Where effective speed can be influenced by:

```text
base_speed
× traffic_multiplier
× scenario_multiplier
```

### Why not pretend to have ML?

A demo with no historical GPS dataset should not claim that ETA is ML-predicted. The first version should expose the architecture for ML while using a strong baseline.

### ML-ready interface

Create an abstraction such as:

```python
class ETAPredictor(Protocol):
    def predict(self, features: ETAFeatures) -> ETAPrediction:
        ...
```

Implement:

```text
BaselineETAPredictor
MLResidualETAPredictor (future)
```

The production/demo baseline should remain usable even when the ML model is unavailable.

---

## 11. ML terminology and future plan

The implementation must use these terms correctly and document them in `docs/ml.md`.

### Relevant concepts

**ETA prediction** — estimating time until a shuttle reaches a destination.

**Regression** — predicts a continuous value such as ETA in seconds.

**Time-series data** — telemetry ordered by time: latitude, longitude, speed, timestamp, route position, etc.

**Feature engineering** — transforming raw telemetry into predictive inputs.

Possible ETA features:

```text
route_remaining_meters
current_speed_kph
rolling_speed_mean
rolling_speed_std
stop_count_remaining
stop_dwell_mean
traffic_multiplier
hour_of_day
day_of_week
historical_route_eta
recent_delay_seconds
```

**Baseline model** — a simple approach used as a reference point. In this project the deterministic formula is the baseline.

**Residual learning** — predict the difference between baseline ETA and observed ETA rather than learning ETA from scratch.

**Gradient boosting** — a strong candidate for tabular ETA data (for example LightGBM/XGBoost), but only introduce it after collecting sufficient historical telemetry.

**Online inference** — generate a prediction from the latest shuttle state without retraining the model.

**Concept drift** — model performance can degrade when route/traffic patterns change.

**MAE** — Mean Absolute Error; intuitive average absolute ETA error.

**RMSE** — Root Mean Squared Error; penalizes large errors more strongly.

**MAPE** — percentage error, but be careful near zero ETA values.

**Prediction interval / uncertainty** — communicate that an ETA is an estimate rather than a promise.

### Future ML pipeline

```text
GPS telemetry
    ↓
cleaning + map matching
    ↓
feature engineering
    ↓
baseline ETA
    ↓
ML residual model
    ↓
calibration / uncertainty
    ↓
ETA API
    ↓
UI
```

### ML quality gate

Do not ship an ML model merely because it exists. Compare against the deterministic baseline. The ML version must demonstrate lower validation MAE before it becomes the default predictor.

---

## 12. Map UX

### Map layers

1. Base map.
2. Shuttle routes.
3. Shuttle markers.
4. User marker.
5. Selected stop.
6. Optional highlighted “best shuttle” route segment.

### Marker behavior

Every marker should show:

```text
shuttle icon
route/line label
optional ETA badge
```

Selected shuttle gets a clearly distinct visual state.

Do not overload the map with huge cards or excessive labels.

### Camera behavior

- On first load: fit active route network + user location.
- “Locate me”: center on user.
- Selecting shuttle: optionally fit user + shuttle with padding.
- Selecting stop: focus on stop and relevant approaching shuttles.

---

## 13. Main UI layout

### Desktop

```text
┌───────────────────────────────────────────────────────────┐
│ Header: ShuttleMap   Demo: ON   Last updated              │
├───────────────────────┬───────────────────────────────────┤
│                       │                                   │
│                       │  Nearest shuttle                 │
│        MAP            │  SH-03 • 2 min • 420 m           │
│                       │                                   │
│     🚌    🚌          │  Next arrivals                   │
│          📍            │  SH-01  5 min                    │
│                       │  SH-02  8 min                    │
│                       │                                   │
│                       │  Selected stop                   │
│                       │  Main Gate                       │
└───────────────────────┴───────────────────────────────────┘
```

### Mobile

Use a map-first layout with a draggable/expandable bottom sheet.

Primary mobile actions:

- Search/select stop
- Show nearest shuttle
- Center on me
- View arrivals
- Open demo controls

---

## 14. Information hierarchy

The user should understand the situation in this order:

1. **How long until the shuttle?**
2. **Which shuttle/route?**
3. **Where is it?**
4. **How far away?**
5. **Is it approaching or delayed?**
6. **When are the next shuttles?**

Do not make distance larger/more prominent than ETA.

---

## 15. Design principles

The design should feel like a serious mobility product, not an academic dashboard.

Principles:

- Map is the visual hero.
- One dominant ETA value.
- Minimal, high-signal status colors.
- Strong typography hierarchy.
- Soft surfaces, modest radius, restrained shadows.
- Avoid excessive gradients, glassmorphism and decorative animation.
- Loading states should look intentional.
- Every live number needs a timestamp or freshness indicator.
- Responsive by default.
- Accessible contrast and keyboard interaction.
- Motion is useful for map state changes, not decoration.

Use **21st.dev MCP** as a UI component discovery/design aid. Prefer components that fit the project's established visual language rather than mechanically importing unrelated components. 21st currently provides an MCP workflow for agentic component search/install and UI generation; its site documents catalog search, component installation, generation, and design review workflows. citeturn949559view0turn949559search9

21st components should be treated as building blocks, not permission to hand over design decisions to an AI. The final visual system remains controlled by the project spec and repository owner.

---

## 16. 21st.dev MCP usage rules

Use 21st for:

- map-side panels
- bottom sheets
- arrival cards
- status pills
- headers/navigation
- filters
- drawers
- responsive cards
- dashboard/supporting UI

Do **not** use 21st to decide:

- domain architecture
- database schema
- ETA logic
- simulator truth
- security decisions
- Git history
- deployment credentials

Suggested agent workflow:

```text
1. Search 21st catalog for a suitable pattern.
2. Inspect the component and its dependencies.
3. Compare against the existing project style.
4. Adapt rather than blindly copy.
5. Keep business logic outside presentation components.
6. Run typecheck/lint/tests after integration.
```

Current 21st documentation says its MCP can search the component catalog and bring component code/dependencies into the agent workflow. citeturn949559view0

---

## 17. API design

### REST

```text
GET  /health
GET  /api/v1/routes
GET  /api/v1/stops
GET  /api/v1/shuttles
GET  /api/v1/shuttles/{id}
GET  /api/v1/arrivals?stop_id=...
GET  /api/v1/eta?shuttle_id=...&stop_id=...
GET  /api/v1/demo/scenarios
POST /api/v1/demo/scenario
POST /api/v1/demo/reset
```

### WebSocket

```text
WS /api/v1/ws
```

Example event:

```json
{
  "type": "shuttle.position.updated",
  "timestamp": "2026-09-06T10:00:00Z",
  "data": {
    "shuttle_id": "SH-03",
    "lat": 12.9698,
    "lng": 79.1552,
    "bearing": 142,
    "speed_kph": 23.4,
    "status": "NEARBY"
  }
}
```

### Contract rule

All API response models must be explicitly typed and validated. Do not return arbitrary dictionaries throughout the codebase.

---

## 18. Reliability rules

The app must tolerate:

- WebSocket disconnects.
- Slow API responses.
- Missing route data.
- Invalid simulator scenario.
- Browser geolocation denial.
- Empty shuttle list.
- Stale telemetry.
- ETA calculation failure.
- ML predictor unavailable.

Fallback behavior:

```text
ML failure -> deterministic ETA
WebSocket failure -> REST polling fallback
Geolocation failure -> selected demo location
Missing live state -> last known state + stale indicator
```

Never show a confident live-looking ETA when the data is stale.

---

## 19. Frontend state rules

Separate:

### Server state

- routes
- stops
- shuttles
- arrivals
- ETA responses

Use TanStack Query.

### Real-time state

WebSocket shuttle position events update a normalized client store/query cache.

### UI state

- selected shuttle
- selected stop
- map viewport
- open/closed panels
- demo scenario controls

Avoid putting everything into one global Zustand store.

---

## 20. Backend service boundaries

Preferred modules:

```text
api/
  routes.py
  shuttles.py
  arrivals.py
  demo.py
  websocket.py

domain/
  models.py
  enums.py

services/
  simulation_service.py
  eta_service.py
  route_service.py
  location_service.py

ml/
  predictor.py
  baseline.py
  features.py

repositories/
  route_repository.py
  shuttle_repository.py
```

Do not create a service layer with no meaningful responsibility just for architectural ceremony.

---

## 21. Database strategy

PostgreSQL/PostGIS is the target database.

Use spatial columns for:

- stop location
- route geometry
- shuttle current location

For a purely local demo, fixture data can seed the database automatically.

Do not require an operator to manually enter every shuttle/route through the UI in v1.

---

## 22. Security and secrets

The repository owner controls all credentials.

Never commit:

- API keys
- database passwords
- Map provider secrets
- 21st API keys
- Anthropic credentials
- cloud credentials
- `.env` files containing secrets

Commit only `.env.example` with placeholder names.

---

## 23. Git and Claude Code control policy

This is mandatory.

### Claude MAY

- inspect repository files
- create/edit source files
- create tests
- run local commands needed to validate the project
- run formatters/linters/typecheckers
- run tests
- inspect `git status`, `git diff`, `git log`
- prepare commits when explicitly asked
- prepare exact commands for the repository owner

### Claude MUST NOT

- `git push`
- force push
- change GitHub repository permissions
- create/delete GitHub credentials
- expose secrets
- rewrite history without explicit instruction
- run destructive database commands against an unknown environment
- delete large portions of the project without approval
- deploy to production without explicit approval
- merge branches without explicit approval

### Git checkpoint rule

Before substantial changes:

```bash
git status
git diff --stat
```

After substantial changes:

```bash
git status
git diff --stat
git diff
```

Claude should show the owner the result and provide the exact commands required for the owner to commit/push.

### Owner-controlled push workflow

Claude should end a completed milestone with something like:

```bash
git status
git add .
git commit -m "feat: build shuttle live map demo"
git push origin main
```

But Claude must **not execute `git push`** unless the owner changes this policy explicitly.

---

## 24. Claude Code permissions / MCP posture

Use least privilege.

Claude Code supports MCP servers for external tools/context, and its CLI includes `claude mcp` configuration commands. The user should retain control over which tools are connected and what permissions Claude receives. citeturn327127search0turn327127search3

Recommended approach:

- 21st MCP: allowed for component/design work.
- GitHub MCP: not required for core coding; repository is already local.
- Database tools: only add if genuinely needed.
- Deployment tools: do not connect for v1.
- Never use `--dangerously-skip-permissions` as a default workflow.

---

## 25. Observability

At minimum log:

- simulation start/stop
- active scenario
- shuttle state update errors
- WebSocket connect/disconnect
- ETA calculation errors
- stale-data conditions

Keep logs structured enough to debug a demo.

---

## 26. Performance targets

Target, not absolute SLA:

- First useful UI render: fast on a normal laptop/network.
- Map should remain interactive while shuttle markers update.
- Avoid React re-rendering the entire application for every telemetry tick.
- Only update changed shuttle data.
- Use marker/layer strategies suitable for the number of demo shuttles.

For a demo, assume roughly 5–30 active shuttles and design so that scaling this number does not require rewriting the rendering model.

---

## 27. Accessibility

Required:

- keyboard accessible controls
- visible focus states
- semantic buttons
- aria-labels for icon-only controls
- status updates announced where appropriate
- color must not be the only way to identify shuttle status
- map controls have accessible names

---

## 28. Testing strategy

### Unit tests

Test:

- route progression
- coordinate interpolation
- distance calculations
- bearing calculation
- nearby status classification
- deterministic ETA
- delay handling
- scenario switching

### API tests

Test:

- health
- routes
- stops
- shuttle list
- arrivals
- ETA endpoint
- demo reset
- invalid scenario

### WebSocket tests

Test:

- connection
- initial snapshot
- update events
- disconnect/reconnect behavior

### E2E

Critical journey:

```text
Open app
→ choose/demo location
→ see map
→ see moving shuttles
→ select stop
→ see ETA list
→ select shuttle
→ watch location update
→ trigger delay scenario
→ ETA changes
→ restore normal scenario
```

---

## 29. Acceptance criteria for v1

The project is “demo ready” only when all are true:

1. The map renders reliably.
2. At least 3 simulated shuttles move continuously.
3. Routes and shuttle positions are visually synchronized.
4. User/demo location is visible.
5. A selected stop shows upcoming shuttles.
6. ETA is displayed in minutes.
7. Distance is displayed.
8. Shuttle status changes as it approaches.
9. At least one delay scenario changes ETA in a visible way.
10. WebSocket reconnect/fallback works.
11. No secret is committed.
12. Unit/API/E2E critical-path tests pass.
13. README explains setup and demo commands.
14. Claude provides owner-run Git commands and does not push.

---

## 30. Milestones

### Milestone 0 — Repository inspection

Claude first inspects the existing repo and reports:

- current framework
- existing files
- package manager
- current branch/status
- existing architecture
- existing scripts
- anything that conflicts with this spec

Do not rewrite the repo blindly.

### Milestone 1 — Foundation

- frontend shell
- backend shell
- database
- health endpoint
- local dev environment

### Milestone 2 — Map

- MapLibre integration
- routes
- stops
- user/demo location
- shuttle markers

### Milestone 3 — Simulation

- server-side simulator
- movement
- WebSocket broadcast
- reconnect/fallback

### Milestone 4 — ETA

- route-aware distance
- deterministic ETA
- status classification
- arrivals panel

### Milestone 5 — Product polish

- 21st-assisted components
- responsive mobile bottom sheet
- loading/error/empty states
- animation polish
- accessibility

### Milestone 6 — Demo scenarios

- normal
- arriving
- delayed
- nearest-is-not-fastest
- reset

### Milestone 7 — Hardening

- tests
- lint/typecheck
- performance pass
- documentation
- production build validation

### Milestone 8 — Optional ML

Only after there is a meaningful telemetry dataset.

---

## 31. Demo script

A strong 2–3 minute demonstration:

1. Open ShuttleMap.
2. Show current/demo location.
3. Point out 3 moving shuttle markers.
4. Select “Main Gate”.
5. Show “SH-03 — 2 min — 420 m”.
6. Select SH-03 and show its live marker.
7. Trigger “Delayed” scenario.
8. Explain that ETA increases because effective speed/delay changed.
9. Point out another shuttle that may be geographically closer but has a worse stop ETA.
10. Reset scenario.
11. Explain that the simulator can later be replaced with real GPS telemetry and the ETA interface can later use a validated ML model.

---

## 32. Design language

Suggested visual direction:

- clean mobility-tech aesthetic
- neutral background
- high-contrast map
- compact floating cards
- large numerical ETA
- subtle route colors
- meaningful status indicators
- premium but restrained motion

Do not clone Ola/Uber branding, logos, exact layouts, or proprietary visual assets. Use them only as product-category inspiration.

---

## 33. Engineering principles

1. **Correctness over cleverness.**
2. **Server is source of truth for simulated movement.**
3. **ETA is an estimate, never a promise.**
4. **Use deterministic fallbacks.**
5. **Do not introduce ML without data/evaluation.**
6. **Business logic belongs outside UI components.**
7. **Every external dependency should have a reason.**
8. **Prefer boring, testable code over abstraction for abstraction’s sake.**
9. **No silent destructive operations.**
10. **The repository owner remains in control of GitHub, secrets and deployment.**

---

## 34. External references to verify during implementation

- MapLibre GL JS official docs: https://maplibre.org/maplibre-gl-js/docs/
- OpenStreetMap tile usage policy: https://operations.osmfoundation.org/policies/tiles/
- OpenStreetMap Nominatim usage policy: https://operations.osmfoundation.org/policies/nominatim/
- Anthropic Claude Code docs: https://docs.anthropic.com/en/docs/claude-code/
- Anthropic MCP docs: https://docs.anthropic.com/en/docs/mcp
- 21st MCP: https://21st.dev/mcp

Implementation agents should verify current versions and current setup commands from official sources rather than assuming this document’s examples are permanent.
