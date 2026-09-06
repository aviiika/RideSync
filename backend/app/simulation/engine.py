"""Advancing shuttles along their routes.

The engine is a pure state machine: :meth:`SimulationEngine.tick` takes elapsed
wall-clock seconds and returns the new world. It never sleeps, never touches
the network and never reads the clock to decide anything, so tests can run an
hour of simulated service in milliseconds and get identical results every run.

Determinism matters here beyond tidiness: a pitch has to be repeatable. Given
the same seed, the same sequence of ticks always produces the same positions.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.geo.route_geometry import BACKWARD, FORWARD, RouteGeometry
from app.models import LoopMode, Route, Shuttle, ShuttleStatus

SECONDS_PER_HOUR = 3600.0

#: Within this distance of its next stop, a shuttle is shown as arriving.
ARRIVING_THRESHOLD_M = 120.0

#: Tolerance for "the shuttle is standing at this stop", in metres.
_AT_STOP_TOLERANCE_M = 0.5

#: Fraction of normal speed a delayed shuttle travels at.
DELAYED_SPEED_FACTOR = 0.4


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    """How the simulated service is shaped."""

    shuttles_per_route: int = 2
    #: Seconds a shuttle waits at each stop.
    dwell_seconds: float = 20.0
    #: Per-shuttle speed variation as a fraction of the route average speed.
    speed_jitter: float = 0.15
    #: Seed making every run reproducible.
    seed: int = 42


@dataclass(slots=True)
class SimulationState:
    """Control state of the simulation clock."""

    running: bool = False
    speed_multiplier: float = 1.0
    elapsed_seconds: float = 0.0
    tick_count: int = 0
    started_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ArrivalEvent:
    """A shuttle reached a stop. Drained by whoever wants to record it."""

    shuttle_id: str
    route_id: str
    stop_id: str
    at: datetime
    delayed: bool


@dataclass(slots=True)
class _Vehicle:
    """A shuttle plus the simulation-only bookkeeping the API never sees."""

    shuttle: Shuttle
    base_speed_kmh: float
    geometry: RouteGeometry = field(repr=False)


class SimulationEngine:
    """Moves every shuttle along its route, one tick at a time."""

    #: Speed multipliers the demo controls expose.
    ALLOWED_SPEEDS = (1.0, 2.0, 5.0)

    def __init__(self, routes: tuple[Route, ...], config: SimulationConfig | None = None) -> None:
        if not routes:
            raise ValueError("the simulation needs at least one route")

        self._config = config or SimulationConfig()
        self._geometries = {route.id: RouteGeometry.build(route) for route in routes}
        self._state = SimulationState()
        self._vehicles: dict[str, _Vehicle] = {}
        self._arrivals: list[ArrivalEvent] = []
        self.reset()

    # ------------------------------------------------------------------ state

    @property
    def config(self) -> SimulationConfig:
        return self._config

    @property
    def state(self) -> SimulationState:
        return self._state

    @property
    def shuttles(self) -> tuple[Shuttle, ...]:
        return tuple(vehicle.shuttle for vehicle in self._vehicles.values())

    def drain_arrivals(self) -> tuple[ArrivalEvent, ...]:
        """Take the arrivals recorded since the last call, and forget them."""
        events = tuple(self._arrivals)
        self._arrivals.clear()
        return events

    def get_shuttle(self, shuttle_id: str) -> Shuttle | None:
        vehicle = self._vehicles.get(shuttle_id)
        return vehicle.shuttle if vehicle else None

    def geometry_for(self, route_id: str) -> RouteGeometry | None:
        return self._geometries.get(route_id)

    # ---------------------------------------------------------------- control

    def start(self) -> SimulationState:
        self._state.running = True
        if self._state.started_at is None:
            self._state.started_at = datetime.now(UTC)
        return self._state

    def pause(self) -> SimulationState:
        self._state.running = False
        return self._state

    def set_speed(self, multiplier: float) -> SimulationState:
        if multiplier not in self.ALLOWED_SPEEDS:
            raise ValueError(f"speed must be one of {self.ALLOWED_SPEEDS}, got {multiplier}")
        self._state.speed_multiplier = multiplier
        return self._state

    def delay_shuttle(self, shuttle_id: str, seconds: float) -> Shuttle:
        """Slow one shuttle for a while.

        A demo control, not a model of traffic: it exists so the delayed and
        recovering paths can be shown on screen rather than explained.
        """
        if seconds <= 0:
            raise ValueError("a delay must be a positive number of seconds")

        vehicle = self._vehicles.get(shuttle_id)
        if vehicle is None:
            raise KeyError(shuttle_id)

        vehicle.shuttle.delay_remaining_s = seconds
        vehicle.shuttle.status = ShuttleStatus.DELAYED
        return vehicle.shuttle

    def clear_delays(self) -> None:
        """Return every delayed shuttle to normal service."""
        for vehicle in self._vehicles.values():
            vehicle.shuttle.delay_remaining_s = 0.0
            if vehicle.shuttle.status is ShuttleStatus.DELAYED:
                vehicle.shuttle.status = ShuttleStatus.IN_SERVICE

    def reset(self) -> SimulationState:
        """Rebuild the world from the seed.

        After a reset the simulation is paused and identical to a fresh engine,
        which is what makes a demo repeatable mid-pitch.
        """
        rng = random.Random(self._config.seed)
        self._state = SimulationState()
        self._vehicles = {}
        self._arrivals = []

        for route_id in sorted(self._geometries):
            geometry = self._geometries[route_id]
            for index in range(self._config.shuttles_per_route):
                vehicle = self._spawn(geometry, index, rng)
                self._vehicles[vehicle.shuttle.id] = vehicle

        return self._state

    # ------------------------------------------------------------------- tick

    def tick(self, delta_seconds: float) -> tuple[Shuttle, ...]:
        """Advance the world by ``delta_seconds`` of wall-clock time.

        Ticks while paused are no-ops rather than errors, so the caller's loop
        does not need to branch. The speed multiplier scales simulated time
        only - it never changes the tick rate or the broadcast rate.
        """
        if not self._state.running or delta_seconds <= 0:
            return self.shuttles

        simulated = delta_seconds * self._state.speed_multiplier
        self._state.elapsed_seconds += simulated
        self._state.tick_count += 1

        now = datetime.now(UTC)
        for vehicle in self._vehicles.values():
            self._advance(vehicle, simulated, now)

        return self.shuttles

    # --------------------------------------------------------------- internal

    def _spawn(self, geometry: RouteGeometry, index: int, rng: random.Random) -> _Vehicle:
        route = geometry.route
        total = geometry.total_distance_m

        # Space vehicles evenly so the demo opens with a plausible headway
        # rather than a clump of shuttles sitting on top of each other.
        offset = total * (index / max(1, self._config.shuttles_per_route))

        jitter = 1.0 + rng.uniform(-self._config.speed_jitter, self._config.speed_jitter)
        base_speed = max(5.0, route.average_speed_kmh * jitter)

        position, _, heading = geometry.locate(offset)
        shuttle = Shuttle(
            id=f"{route.id}-{index + 1:02d}",
            route_id=route.id,
            name=f"{route.name} {index + 1}",
            distance_m=offset,
            direction=FORWARD,
            position=position,
            heading=heading,
            speed_kmh=round(base_speed, 1),
            status=ShuttleStatus.IN_SERVICE,
            progress=geometry.progress(offset),
            occupancy=round(rng.uniform(0.15, 0.85), 2),
            next_stop_index=0,
        )
        vehicle = _Vehicle(shuttle=shuttle, base_speed_kmh=base_speed, geometry=geometry)
        self._update_next_stop(vehicle)
        return vehicle

    def _advance(self, vehicle: _Vehicle, simulated_seconds: float, now: datetime) -> None:
        shuttle = vehicle.shuttle
        geometry = vehicle.geometry
        shuttle.updated_at = now

        # Waiting at a stop: burn down the dwell timer, do not move.
        if shuttle.dwell_remaining_s > 0:
            shuttle.dwell_remaining_s = max(0.0, shuttle.dwell_remaining_s - simulated_seconds)
            shuttle.speed_kmh = 0.0
            shuttle.status = (
                ShuttleStatus.AT_STOP if shuttle.dwell_remaining_s > 0 else ShuttleStatus.IN_SERVICE
            )
            return

        # A delayed shuttle keeps moving, just badly.
        delayed = shuttle.delay_remaining_s > 0
        if delayed:
            shuttle.delay_remaining_s = max(0.0, shuttle.delay_remaining_s - simulated_seconds)

        speed_kmh = vehicle.base_speed_kmh * (DELAYED_SPEED_FACTOR if delayed else 1.0)

        travel_m = speed_kmh * 1000.0 / SECONDS_PER_HOUR * simulated_seconds
        if travel_m <= 0:
            return

        target = shuttle.distance_m + travel_m * shuttle.direction
        stop_hit = self._first_stop_crossed(vehicle, shuttle.distance_m, target)

        if stop_hit is not None:
            stop_index, stop_distance = stop_hit
            stops = geometry.route.stops
            if stop_index < len(stops):
                self._arrivals.append(
                    ArrivalEvent(
                        shuttle_id=shuttle.id,
                        route_id=shuttle.route_id,
                        stop_id=stops[stop_index].id,
                        at=now,
                        delayed=delayed,
                    )
                )

            shuttle.distance_m = stop_distance
            shuttle.dwell_remaining_s = self._config.dwell_seconds
            shuttle.status = ShuttleStatus.AT_STOP
            shuttle.speed_kmh = 0.0
            shuttle.next_stop_index = stop_index
        else:
            shuttle.distance_m = self._wrap(vehicle, target)
            shuttle.speed_kmh = round(speed_kmh, 1)
            shuttle.status = ShuttleStatus.DELAYED if delayed else ShuttleStatus.IN_SERVICE

        position, _, bearing = geometry.locate(shuttle.distance_m)
        shuttle.position = position
        # Travelling back down the polyline means facing the other way.
        shuttle.heading = bearing if shuttle.direction == FORWARD else (bearing + 180.0) % 360.0
        shuttle.progress = geometry.progress(shuttle.distance_m)

        if shuttle.status is not ShuttleStatus.AT_STOP:
            self._update_next_stop(vehicle)
            # A delayed shuttle stays labelled delayed even when it is close:
            # "arriving" would quietly undo the thing being demonstrated.
            if not delayed and self._distance_to_next_stop(vehicle) <= ARRIVING_THRESHOLD_M:
                shuttle.status = ShuttleStatus.ARRIVING

    def _first_stop_crossed(
        self, vehicle: _Vehicle, from_m: float, to_m: float
    ) -> tuple[int, float] | None:
        """Return the first stop passed between two distances, if any.

        Testing the interval each tick - rather than only comparing positions -
        is what stops a 5x demo speed from skipping stops entirely.
        """
        geometry = vehicle.geometry
        direction = vehicle.shuttle.direction
        total = geometry.total_distance_m
        crossed: list[tuple[int, float]] = []

        for index, stop_distance in enumerate(geometry.stop_distances):
            # Do not re-serve the stop the shuttle is standing on.
            if abs(from_m - stop_distance) <= _AT_STOP_TOLERANCE_M:
                continue

            if geometry.route.loop_mode is LoopMode.LOOP:
                travelled = (to_m - from_m) % total
                to_stop = (stop_distance - from_m) % total
                if 0 < to_stop <= travelled:
                    crossed.append((index, stop_distance))
                continue

            if (
                direction == FORWARD
                and from_m < stop_distance <= to_m
                or direction == BACKWARD
                and to_m <= stop_distance < from_m
            ):
                crossed.append((index, stop_distance))

        if not crossed:
            return None

        # Nearest first, so a long tick still calls at each stop in turn.
        return min(crossed, key=lambda item: abs(item[1] - from_m))

    def _wrap(self, vehicle: _Vehicle, distance_m: float) -> float:
        """Keep a distance on the route, looping or reversing at the ends."""
        geometry = vehicle.geometry
        total = geometry.total_distance_m

        if geometry.route.loop_mode is LoopMode.LOOP:
            return distance_m % total

        shuttle = vehicle.shuttle
        if distance_m > total:
            shuttle.direction = BACKWARD
            return max(0.0, total - (distance_m - total))
        if distance_m < 0:
            shuttle.direction = FORWARD
            return min(total, -distance_m)
        return distance_m

    def _update_next_stop(self, vehicle: _Vehicle) -> None:
        """Point the shuttle at the nearest stop still ahead of it."""
        geometry = vehicle.geometry
        shuttle = vehicle.shuttle

        ahead = [
            (geometry.distance_to(shuttle.distance_m, stop_distance, shuttle.direction), index)
            for index, stop_distance in enumerate(geometry.stop_distances)
        ]
        remaining = [(distance, index) for distance, index in ahead if distance > 1.0]
        if remaining:
            shuttle.next_stop_index = min(remaining)[1]

    def _distance_to_next_stop(self, vehicle: _Vehicle) -> float:
        geometry = vehicle.geometry
        shuttle = vehicle.shuttle
        stop_distance = geometry.stop_distances[shuttle.next_stop_index]
        return geometry.distance_to(shuttle.distance_m, stop_distance, shuttle.direction)
