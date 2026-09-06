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

## 2:00 — Under the hood (40 seconds)

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

## 2:40 — Where it goes (20 seconds)

> "Today the ETA is honest arithmetic: remaining route distance over speed, plus
> dwell time. It's behind an interface, so once there's real trip history, a
> trained model drops into the same seam and everything above it is untouched."

> "What I won't do is train a model on my own simulation and call it accuracy.
> That number would be meaningless."

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
Unanswerable honestly today, and I'd rather say so. Against real arrivals you'd
measure MAE and median absolute error. What I can show is that it's consistent
and that it correctly handles the case everyone gets wrong — a nearby shuttle
heading away from you.

**"Does it scale?"**
Designed for 20–50 vehicles. Positions are drawn as map-native layers, not DOM
markers, and telemetry updates the map outside React entirely, so a moving
shuttle re-renders nothing. Raise `SHUTTLES_PER_ROUTE` in `.env` and show them.

**"Why no database?"**
Three routes and eighteen stops don't need one. It's behind a repository
interface, so PostGIS is one class and one line when there's a reason.

**"How long did this take?"**
122 backend tests and 76 frontend tests, CI on every push. Answer with that.

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

Rehearse the reset. It is the single most useful key on the screen: whatever
happens, you are one click from a known-good state.
