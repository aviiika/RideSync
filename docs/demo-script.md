# Demo script

A 3-minute run-through. Timings are a guide, not a straitjacket — the point is
the shape: **problem → open the app → the answer → how it works → where it
goes.**

The demo is deterministic. Seed 42, and **Reset** returns to the exact starting
state, so you can rehearse it and get the same run every time.

---

## Before you start

Two terminals, both from `C:\Users\avika\OneDrive\Desktop\SHUTTLE`.

**Terminal 1 — API:**

```powershell
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

Wait for `API started - 6 shuttles on 3 routes`.

**Terminal 2 — web app:**

```powershell
cd frontend
npm run dev
```

Open **http://localhost:5173** and leave it running. The simulation starts on
its own — you should see vehicles already moving before you say a word.

**Checklist, thirty seconds before you present:**

- Header reads *6 shuttles in service* with a pulsing green dot
- Three coloured lines on the map, stop circles along them
- Blue dot at the Main Gate — that is "you"
- The card on the right names a shuttle and an ETA
- Press **Reset**, then **Start**. You are at a known state.

---

## 0:00 — The problem (20 seconds)

> "I'm standing at the VIT main gate. There's a campus shuttle. I have no idea
> when it's coming, or whether it's already gone past. So I stand there — or I
> give up and walk, and it arrives thirty seconds later."

Do not show the app yet. Let the problem land first.

---

## 0:20 — Open the app (30 seconds)

Show the screen. Say nothing for two or three seconds — let them look.

> "This is the whole product. One screen."

Point at the card, top right:

> "Nearest shuttle. Four minutes. Two hundred metres away. Heading toward Anna
> Auditorium. And — *worth waiting*."

> "That's the five-second answer. Everything else on this screen is optional."

**The point to make:** they understood it before you explained it.

---

## 0:50 — It is actually live (30 seconds)

Point at a moving marker.

> "These aren't refreshing every ten seconds. Positions stream over a WebSocket
> twice a second, and the markers are interpolated between updates — so they
> glide, like a ride-hailing app, instead of hopping."

Point at the arrows.

> "Each one shows heading. You can see which way it's going, which is half the
> question — a shuttle fifty metres away that's just left your stop is no use
> to you."

Click **2×**.

> "And because it's a simulation, I can speed up time to show you a full
> service cycle."

Leave it at 2× — it makes the rest of the demo livelier. Drop back to 1× if
anyone looks lost.

---

## 1:20 — The insight (40 seconds)

This is the part that separates it from a map with dots on it.

Click a shuttle that has just passed the Main Gate.

> "Look at this one. Eighty metres away — the closest vehicle on the screen.
> But it's just gone past my stop, so it has to travel the entire ring to come
> back. Eleven minutes."

Point at the list.

> "And here's one six hundred metres away that arrives in three, because it's
> heading toward me."

> "So we never rank by distance. We rank by **when it actually reaches you**.
> Nearest on a map is not the same as soonest, and getting that wrong is how
> you miss your bus."

**If nothing has conveniently just passed the gate:** use the "Other shuttles"
list instead — it is ordered by ETA, so the distances in it are usually out of
order. Point at that. It makes the same point in one sentence.

---

## 2:00 - Three things a map with dots cannot do (40 seconds)

Tap a stop on the map.

> "Tap a stop and you get a departure board - what is due here, soonest first.
> Only shuttles that actually call at this stop, however close anything else
> happens to be."

Point at a card that says the shuttle cannot be reached in time.

> "And it knows how long it takes *you* to get to the stop. This one arrives in
> two minutes, but the stop is a five-minute walk - so it says wait for the next
> one, instead of telling you to run for something you cannot catch."

Open a shuttle and press **Delay this shuttle**.

> "I can inject a delay. Watch it drop to a crawl, the status change, and the
> confidence on its ETA fall to low - because a late shuttle is an
> unpredictable one."

---

## 2:40 - Under the hood (40 seconds)

Click the route chips on the map, top left — isolate the Men's Hostel Shuttle.

> "Three routes, all inside campus: a ring, the men's hostels, the ladies'
> hostels — connecting both to the academic blocks."

Click a shuttle to open the detail panel.

> "Speed, heading, route progress, next stop. And the ETA shows its working:
> four hundred metres of route left at eighteen km/h, calling at one stop on the
> way."

Be straight about what it is:

> "The telemetry is simulated. I'm not going to pretend a GPS box on a bus is
> feeding this. What's real is the architecture — the geospatial maths, the ETA
> engine, the ranking. Swapping the simulation for a live GPS feed is one
> component, and nothing above it changes."

**This candour is a feature.** Judges have seen a lot of demos that overclaim.

---

## 3:20 - Where it goes (25 seconds)

Point at the accuracy line under the simulation controls.

> "Every ETA the system promises is written down, and every actual arrival is
> written down. That line is the two scored against each other - we are off by
> about half a minute on average."

> "And I have labelled it precisely: measured against *simulated* arrivals. It
> tells you the estimator is consistent. It does not tell you anything about
> real buses, and I am not going to pretend it does."

> "That is also the training set. Once real telemetry replaces the simulation,
> those same rows - distance, speed, stops on the way, time of day - become what
> a model learns from, and it drops into the same interface."

Close on the problem you opened with:

> "Right now, a student at that gate is guessing. This is them not guessing."

---

## Questions you should expect

**"Is this real GPS?"**
No, and the UI says so on screen. Simulated telemetry, production-shaped
architecture. Section 13 of `docs/architecture.md` is exactly where a real feed
attaches.

**"Where's the AI?"**
There isn't one, deliberately. The ETA is deterministic arithmetic. A model
trained on synthetic data would be learning my own simulation's formula. The
seam is built and documented; the data has to come first.

**"How accurate is the ETA?"**
Against its own simulated arrivals: mean absolute error of roughly half a
minute over several hundred scored predictions. The app measures and displays
that, and labels what it was measured against. Against real buses: unknown, and
nothing here can tell you. The measurement is real; the world it measures is
synthetic.

**"Does it scale?"**
Designed for 20–50 vehicles. Positions are drawn as map-native layers, not DOM
markers, and telemetry updates the map outside React entirely, so a moving
shuttle re-renders nothing. Raise `SHUTTLES_PER_ROUTE` in `.env` and show them.

**"Why SQLite and not Postgres?"**
There is a database - two append-only tables of predictions and arrivals, which
is what the accuracy number is computed from. Routes and stops stay in JSON
behind a repository interface, because three routes and eighteen stops do not
need a server. PostGIS is one class and one line when there is a reason.

**"How long did this take?"**
159 backend tests and 109 frontend tests, CI on every push. Answer with that.

---

## If something goes wrong

| Symptom | What to do |
| --- | --- |
| *Live connection lost · Reconnecting…* | Nothing. It reconnects on its own — say "and that's the reconnect handling" and carry on. |
| Shuttles frozen | The simulation is paused. Press **Start**. |
| *Shuttle service unavailable* | Terminal 1 died. Restart uvicorn; the frontend reconnects by itself. |
| Map blank, panel fine | Basemap tiles aren't loading — a network issue, not the app. The panel still answers the question; present from it. |
| Lost on the map | Press the crosshair, top left. It reframes the campus. |
| Demo drifted somewhere odd | **Reset**, then **Start**. Exact same starting state, every time. |
| A shuttle stuck on "Running late" | Delays expire on their own; **Reset** clears them instantly. |
| Accuracy line missing | Nothing has been scored yet. Run at 5x for a minute and it appears. |

Rehearse the reset. It is the single most useful key on the screen: whatever
happens, you are one click from a known-good state.
