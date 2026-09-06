# Shuttle Mapping & ETA Simulation — Project Specification

**Project type:** Demo / pitch-ready real-time shuttle tracking simulation  
**Primary goal:** Build an Ola/Uber-style shuttle map experience where a user can see nearby shuttles, their direction, distance, estimated arrival time (ETA), route, and whether waiting is worthwhile.

**Important demo constraint:** This is a simulation-first system. No real GPS hardware or production fleet integration is required for the MVP. The architecture must, however, be designed so simulated telemetry can later be replaced by real GPS/vehicle data without rewriting the frontend.

---

## 1. Product Vision

A commuter should be able to open the app and immediately answer:

1. Where am I?
2. Which shuttle is nearest to me?
3. How far away is it?
4. How many minutes until it reaches my stop?
5. Is the shuttle approaching me or moving away?
6. Which shuttle should I wait for?
7. What is the route and where is the shuttle currently located?

The demo should visually communicate **live movement**, not just static map markers.

### Core user story

> "I am at a shuttle stop. I want to see the next available shuttle, its live position, distance from me, route, direction, and ETA so I can decide whether to wait or make another plan."

---

## 2. MVP Scope

### Must have

- Interactive map
- User/current simulated location
- Shuttle routes
- Multiple simulated shuttles
- Animated shuttle movement
- Shuttle markers with heading/direction
- Nearest shuttle detection
- Distance to shuttle
- ETA to selected stop
- ETA to user/nearest stop
- Route visualization
- Shuttle detail panel
- "Next shuttle" recommendation
- Live simulation controls
- Start/pause/reset simulation
- Configurable simulation speed
- Demo-friendly deterministic mode
- Responsive UI
- Clear loading/error/empty states

### Nice to have

- Stop markers
- Route progress percentage
- Shuttle occupancy status (simulated)
- Service status
- Arrival countdown
- Route filtering
- Shuttle filtering
- Multiple routes
- "Walking to stop" estimate
- Historical trip replay
- Basic ETA confidence indicator
- Admin/demo control panel

### Out of scope for MVP

- Real payment processing
- Driver authentication
- Production fleet management
- Real dispatching
- Real-world navigation for drivers
- Production-grade user accounts
- Complex ML training pipeline
- Hardware GPS integration
- Safety-critical operational decisions

---

# 3. Recommended Architecture

Use a modular architecture:

```text
┌─────────────────────────────┐
│        React Frontend       │
│                             │
│ Map + UI + Simulation View  │
└──────────────┬──────────────┘
               │ REST / WebSocket
               ▼
┌─────────────────────────────┐
│        Backend API          │
│                             │
│ Shuttle Service             │
│ Route Service               │
│ ETA Service                 │
│ Simulation Engine           │
│ Recommendation Service      │
└──────────────┬──────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
┌─────────────┐  ┌──────────────┐
│ PostgreSQL  │  │ Redis        │
│ + PostGIS   │  │ Live State   │
└─────────────┘  └──────────────┘
               │
               ▼
       Simulation Telemetry
```

For the first implementation, Redis can be optional. Keep the code structured so it can be introduced later.

---

# 4. Tech Stack

## Frontend

Recommended:

- React
- TypeScript
- Vite
- Tailwind CSS
- MapLibre GL JS
- TanStack Query
- Zustand
- WebSocket client
- Lucide React icons

### Why

React + TypeScript gives a maintainable component model.

Tailwind allows fast iteration on a pitch-quality interface.

MapLibre GL JS provides an interactive map without locking the architecture to a proprietary map vendor.

TanStack Query handles server state.

Zustand handles lightweight UI/simulation state.

WebSockets provide a path to real-time shuttle updates.

---

## Backend

Recommended:

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- PostgreSQL
- PostGIS
- Redis (optional initially)
- WebSockets
- Pytest

### Backend responsibilities

The backend owns:

- Shuttle state
- Routes
- Stops
- Simulation clock
- Position updates
- ETA calculation
- Distance calculations
- Recommendation logic
- WebSocket broadcasting
- API validation

The frontend should NOT be the authoritative source of shuttle state.

---

# 5. Data Model

## Shuttle

```text
id
route_id
name
status
latitude
longitude
heading
speed_kmh
current_stop_index
progress
last_updated
occupancy
```

Example:

```json
{
  "id": "SH-101",
  "route_id": "ROUTE-A",
  "name": "Campus Shuttle 101",
  "status": "IN_SERVICE",
  "latitude": 12.9698,
  "longitude": 79.1552,
  "heading": 90,
  "speed_kmh": 28,
  "current_stop_index": 3,
  "progress": 0.42,
  "occupancy": 0.65
}
```

## Stop

```text
id
name
latitude
longitude
route_id
sequence
```

## Route

```text
id
name
color
geometry
stops
average_speed_kmh
```

## Telemetry

```text
shuttle_id
timestamp
latitude
longitude
speed
heading
```

---

# 6. Simulation Engine

The simulation engine is the heart of the demo.

Do NOT randomly teleport shuttle markers.

Instead, simulate movement along predefined route geometry.

### Simulation loop

```text
Load routes
   ↓
Load shuttle initial positions
   ↓
Start simulation clock
   ↓
For every simulation tick:
   ↓
Advance shuttle along route
   ↓
Calculate latitude/longitude
   ↓
Calculate heading
   ↓
Calculate speed
   ↓
Update current segment
   ↓
Calculate ETA
   ↓
Broadcast state
   ↓
Repeat
```

Recommended simulation tick:

```text
250–1000 ms
```

Frontend rendering should remain smooth even if backend updates are less frequent.

---

# 7. Route Simulation

Represent each route as a polyline.

A shuttle moves from point A to point B.

For each segment:

```text
segment_distance = haversine(A, B)

movement_distance =
    speed_meters_per_second * delta_time

new_position =
    interpolate(A, B, movement_distance)
```

When the shuttle reaches the next point:

```text
current_segment += 1
```

When the final point is reached:

```text
loop route
OR
reverse route
```

Make this configurable.

---

# 8. Geospatial Calculations

Use standard geospatial terminology correctly.

### Haversine distance

Use the Haversine formula for approximate great-circle distance between two latitude/longitude points.

Output:

```text
meters
kilometers
```

### Bearing

Calculate initial bearing between two coordinates to determine shuttle heading.

### Nearest shuttle

For every active shuttle:

```text
distance(user, shuttle)
```

Then:

```text
nearest_shuttle = min(distance)
```

### Important

Distance to the shuttle is NOT the same as ETA.

A shuttle can be physically close but still require a long route traversal.

---

# 9. ETA Engine

ETA should be treated as an estimate, not a guaranteed arrival time.

Basic MVP ETA:

```text
ETA = remaining_route_distance / estimated_speed
```

Better model:

```text
ETA =
    route travel time
    + stop delay
    + traffic factor
    + dwell time
```

For simulation:

```text
ETA = remaining_distance / simulated_speed
```

Add a small configurable stop dwell time.

Example:

```text
average_speed = 25 km/h
remaining_distance = 1.2 km

ETA = 1.2 / 25 hours
   ≈ 2.88 minutes
```

Display:

```text
Arriving in ~3 min
```

Avoid false precision such as:

```text
2 min 53 sec
```

unless the demo explicitly needs a countdown.

---

# 10. ETA Terminology

Use these terms consistently:

- **ETA:** Estimated Time of Arrival
- **ETD:** Estimated Time of Departure
- **Dwell time:** Time a shuttle remains at a stop
- **Headway:** Time gap between consecutive shuttles
- **Inter-stop distance:** Distance between two stops
- **Route progress:** Percentage of route completed
- **Telemetry:** Location/speed/heading updates
- **GPS/GNSS:** Positioning data source
- **Geofencing:** Geographic boundary detection
- **Map matching:** Matching noisy GPS coordinates to a road/route
- **Bearing:** Direction of travel
- **Trajectory:** Sequence of positions over time

---

# 11. ML / AI Roadmap

Do NOT introduce ML just for the sake of calling the project AI.

The MVP should use deterministic ETA calculations.

Later, the ETA engine can become ML-powered.

## Possible ML formulation

Input features:

```text
distance_to_stop
current_speed
average_speed
time_of_day
day_of_week
route_id
stop_id
traffic_factor
historical_trip_duration
dwell_time
headway
```

Target:

```text
actual_arrival_time - prediction_time
```

This becomes a supervised regression problem.

Possible models:

- Linear Regression
- Random Forest
- Gradient Boosting
- XGBoost
- LightGBM
- Neural Network

Start with a baseline.

### Baseline

```text
ETA_baseline =
    remaining_distance / rolling_average_speed
```

### ML model

```text
ETA_ML = f(
    distance,
    speed,
    route,
    stop,
    time,
    historical patterns
)
```

### Evaluation metrics

Use:

- MAE — Mean Absolute Error
- RMSE — Root Mean Squared Error
- MAPE — Mean Absolute Percentage Error (use carefully near zero)
- Median Absolute Error

For a pitch, MAE is easy to communicate:

> "Our ETA was off by an average of X minutes on the validation simulation."

Do not claim production accuracy from synthetic data.

---

# 12. Recommendation Logic

The app should answer:

> "Should I wait?"

Define a simple recommendation score.

Example:

```text
if ETA <= 3:
    "Arriving soon"

elif ETA <= 7:
    "Worth waiting"

elif ETA <= 12:
    "Consider waiting"

else:
    "Long wait"
```

This is a demo policy, not ML.

Later it can consider:

```text
user walking time
next shuttle ETA
current shuttle direction
headway
service frequency
```

Example:

```text
best_option =
    min(
      current_shuttle_eta,
      next_shuttle_eta
    )
```

---

# 13. Real-Time Communication

Preferred architecture:

```text
Frontend
   │
   │ WebSocket
   ▼
Backend
   │
   ▼
Simulation Engine
```

WebSocket message:

```json
{
  "type": "SHUTTLE_UPDATE",
  "timestamp": "2026-09-06T09:30:00Z",
  "shuttle": {
    "id": "SH-101",
    "lat": 12.9698,
    "lng": 79.1552,
    "speed": 27,
    "heading": 91,
    "eta_minutes": 4
  }
}
```

The frontend should smoothly animate between received positions.

---

# 14. API Design

Suggested endpoints:

```text
GET    /health
GET    /routes
GET    /routes/{route_id}
GET    /stops
GET    /shuttles
GET    /shuttles/{shuttle_id}
GET    /shuttles/nearby
GET    /eta
POST   /simulation/start
POST   /simulation/pause
POST   /simulation/reset
POST   /simulation/speed
WS     /ws/shuttles
```

API responses should use Pydantic schemas.

Never expose database models directly.

---

# 15. Frontend UX

The interface should feel similar to modern ride-hailing products without copying proprietary branding.

## Main screen

```text
┌──────────────────────────────────────┐
│ Search / Current Location            │
├──────────────────────────────────────┤
│                                      │
│             MAP                      │
│                                      │
│     🚌 →                             │
│              ● User                  │
│                    🚌 →              │
│                                      │
│ Route line + stops                   │
│                                      │
├──────────────────────────────────────┤
│ Nearest Shuttle                      │
│                                      │
│ Campus Shuttle 101                   │
│ Arriving in 4 min                    │
│ 1.2 km away                          │
│                                      │
│ [View Route]                         │
└──────────────────────────────────────┘
```

### Shuttle marker

Show:

- Shuttle icon
- Direction
- Route color
- Optional route number

### Selected shuttle card

Show:

```text
Campus Shuttle 101

4 min
1.2 km away

Heading toward:
Main Gate

Speed:
27 km/h

Route progress:
62%
```

---

# 16. Design Principles

Use these principles:

### 1. Map first

The map is the primary visual object.

### 2. ETA second

The user should understand the ETA within one glance.

### 3. Minimal cognitive load

Do not fill the screen with telemetry.

### 4. Progressive disclosure

Show basic information first.

Reveal technical details when a shuttle is selected.

### 5. Real-time feel

Markers move smoothly.

### 6. Strong visual hierarchy

Most important:

```text
ETA
↓
Distance
↓
Shuttle
↓
Route
↓
Telemetry
```

---

# 17. 21st.dev MCP Design Guidance

If the 21st.dev MCP server is available in Claude Code, use it for UI/component discovery and implementation inspiration.

Use it for:

- Cards
- Bottom sheets
- Command/search interfaces
- Navigation components
- Status badges
- Buttons
- Tabs
- Dashboard panels
- Loading states
- Empty states

Do NOT blindly copy generated components.

Every component must be adapted to the project's:

- spacing system
- typography
- accessibility requirements
- responsive behavior
- map-first layout

Suggested component architecture:

```text
components/
├── map/
│   ├── ShuttleMap
│   ├── ShuttleMarker
│   ├── RouteLayer
│   └── StopMarker
│
├── shuttle/
│   ├── ShuttleCard
│   ├── ShuttleDetails
│   ├── EtaBadge
│   └── ShuttleList
│
├── simulation/
│   ├── SimulationControls
│   └── SimulationStatus
│
└── common/
    ├── Button
    ├── Card
    ├── Badge
    └── LoadingState
```

---

# 18. Design System

Keep the UI consistent.

Define:

```text
Typography
Spacing scale
Border radius
Elevation/shadows
Icon sizing
Button variants
Status states
Map marker states
```

Suggested status vocabulary:

```text
IN_SERVICE
ARRIVING
AT_STOP
DELAYED
OUT_OF_SERVICE
```

Avoid excessive colors.

Use color primarily to communicate:

- active route
- warning
- selected shuttle
- service status

---

# 19. Repository Structure

Recommended monorepo:

```text
shuttle-mapping/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── stores/
│   │   ├── services/
│   │   ├── types/
│   │   └── map/
│   ├── package.json
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── simulation/
│   │   ├── geo/
│   │   ├── eta/
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
│
├── data/
│   ├── routes/
│   └── simulation/
│
├── docs/
│
├── .env.example
├── docker-compose.yml
├── README.md
└── project-spec_shuttle.md
```

---

# 20. Configuration

Never hard-code environment-specific values.

Use:

```text
.env
.env.example
```

Examples:

```text
VITE_API_URL=
VITE_WS_URL=
DATABASE_URL=
REDIS_URL=
MAP_STYLE_URL=
```

Never commit:

- API keys
- passwords
- tokens
- private credentials
- production secrets

---

# 21. Demo Mode

The demo is a first-class feature.

Include:

```text
Demo Mode ON
```

Capabilities:

- Start
- Pause
- Reset
- Speed x1
- Speed x2
- Speed x5
- Select shuttle
- Select stop
- Simulate user location
- Optional inject delay

The demo must be deterministic when a seed is provided.

This makes the pitch repeatable.

---

# 22. Testing Strategy

## Backend

Test:

- Haversine distance
- Bearing
- Route interpolation
- Shuttle movement
- ETA calculation
- Stop arrival
- Route looping
- Simulation pause/resume
- API validation
- WebSocket payloads

## Frontend

Test:

- Shuttle list
- Selected shuttle
- ETA display
- Simulation controls
- Error state
- Loading state
- WebSocket reconnect behavior

## Integration

Verify:

```text
Simulation
→ Backend
→ WebSocket
→ Frontend
→ Map marker
→ ETA
```

---

# 23. Reliability Requirements

The system should handle:

### WebSocket disconnect

Frontend reconnects automatically.

### Stale telemetry

If a shuttle update is too old:

```text
status = STALE
```

Do not present stale data as live.

### Backend restart

Simulation state should safely reset/reinitialize.

### Invalid coordinates

Reject invalid latitude/longitude.

### ETA failure

Fallback to:

```text
ETA unavailable
```

instead of displaying a fake number.

---

# 24. Performance

Avoid unnecessary map rerenders.

Use:

- memoized components
- efficient state updates
- throttled UI updates where appropriate
- map-native layers when practical
- WebSocket connection reuse

The frontend should remain responsive with at least:

```text
20–50 simulated shuttles
```

as an MVP performance target.

---

# 25. Security

Even though this is a demo:

- Validate API inputs
- Keep secrets in environment variables
- Configure CORS deliberately
- Do not expose database credentials
- Avoid unsafe dynamic SQL
- Validate WebSocket messages
- Do not trust frontend shuttle positions

---

# 26. Observability

Include useful development logs:

```text
simulation started
simulation paused
shuttle updated
ETA calculated
websocket connected
websocket disconnected
```

Avoid noisy production-style logging of every coordinate unless debugging is enabled.

---

# 27. Git Workflow and User Control

The user owns the GitHub repository.

Claude Code MUST NOT assume it can push.

Default workflow:

```text
Claude Code:
- inspect repository
- modify files
- run tests
- run lint/type checks
- show git diff
- explain changes
- provide exact commands
```

User performs:

```bash
git status
git add .
git commit -m "feat: build shuttle tracking simulation"
git push origin main
```

Claude should never silently:

```text
git push
git reset --hard
git force push
delete branches
rewrite history
```

without explicit user authorization.

Before destructive operations, stop and ask.

---

# 28. Definition of Done

The MVP is complete when:

- The application starts locally.
- A map renders.
- At least 3 simulated shuttles move.
- Shuttles follow routes instead of teleporting.
- User location is visible.
- Distance is calculated.
- ETA is calculated.
- Nearest shuttle is identified.
- Shuttle direction is visible.
- Selecting a shuttle shows details.
- Simulation can start/pause/reset.
- Simulation speed can change.
- WebSocket updates work.
- Reconnection works.
- Loading/error states exist.
- Backend tests pass.
- Frontend type/lint checks pass.
- README contains setup instructions.
- `.env.example` exists.
- No secrets are committed.
- `git diff` is reviewed before the user commits.

---

# 29. Implementation Order

Do NOT attempt everything simultaneously.

### Phase 1 — Repository discovery

Inspect the existing repository before changing anything.

Identify:

- existing framework
- package manager
- existing frontend
- existing backend
- current dependencies
- current README
- existing environment files
- existing architecture

Reuse existing work where sensible.

### Phase 2 — Skeleton

Create/complete:

```text
frontend
backend
data
docs
```

Make both applications boot.

### Phase 3 — Static map

Render:

- map
- route
- stops
- simulated user

### Phase 4 — Simulation

Implement:

- route interpolation
- shuttle movement
- speed
- heading
- simulation controls

### Phase 5 — ETA

Implement:

- distance
- route remaining distance
- ETA
- nearest shuttle

### Phase 6 — Real-time

Add:

- WebSocket
- frontend live updates
- reconnection

### Phase 7 — UX polish

Add:

- shuttle card
- bottom panel
- route details
- recommendation
- loading/error states

### Phase 8 — Testing

Run all tests and fix failures.

### Phase 9 — Pitch mode

Optimize the experience for a 2–5 minute demo.

---

# 30. Pitch Narrative

The demo should communicate:

```text
Problem
↓
"I don't know when my shuttle will arrive."
↓
Solution
↓
"See every nearby shuttle in real time."
↓
Decision
↓
"Know the ETA before deciding whether to wait."
↓
Technology
↓
"Real-time telemetry + geospatial calculations + ETA engine."
↓
Future
↓
"Replace simulation telemetry with real fleet GPS and improve ETA with historical ML."
```

Do not claim the simulation is real GPS.

Call it:

> "A real-time shuttle tracking and ETA simulation platform."

---

# 31. Engineering Rules for Claude Code

1. Read this specification before implementation.
2. Inspect the existing GitHub repository before modifying files.
3. Preserve useful existing code.
4. Do not rewrite the project unnecessarily.
5. Prefer small, testable modules.
6. Use TypeScript strictly on the frontend.
7. Use Pydantic models for API contracts.
8. Keep business logic out of UI components.
9. Keep simulation logic independent from the API layer.
10. Keep ETA logic independent from the simulation engine.
11. Keep map rendering independent from ETA calculations.
12. Write tests for geospatial and ETA logic.
13. Never hard-code secrets.
14. Never silently push to GitHub.
15. Never use destructive Git commands without approval.
16. Before finishing, show:
    - changed files
    - architecture changes
    - tests run
    - commands run
    - known limitations
    - exact Git commands for the user
17. If a requirement conflicts with this specification, explain the conflict before making a major architectural decision.
18. Favor reliability and clarity over unnecessary complexity.

---

# 32. Future Production Architecture

When moving from simulation to real fleet data:

```text
GPS/GNSS devices
      ↓
Telemetry ingestion
      ↓
Message broker
      ↓
Stream processing
      ↓
Location service
      ↓
ETA service
      ↓
WebSocket/API
      ↓
Mobile/Web clients
```

Potential technologies later:

- MQTT
- Kafka
- Redis Streams
- PostGIS
- TimescaleDB
- Map matching
- Traffic APIs
- ML ETA service
- Feature store
- Model monitoring

Do not add these technologies to the MVP unless there is a concrete requirement.

---

# 33. Success Metric for the Demo

The most important demo metric is not model accuracy.

It is:

> **Can a user understand which shuttle to take and how long they need to wait within 5 seconds of opening the app?**

The UI should make that answer obvious.
