"""Pre-computed geometry for one route.

Building this once per route turns the questions the simulation and ETA
engines ask on every tick - "where is a shuttle 1,840 m along?", "how far is
the next stop?" - into arithmetic instead of repeated polyline walks.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.geo.distance import cumulative_distances, point_at_distance
from app.models import Coordinate, LoopMode, Route

#: Direction of travel along the polyline: forward, or back towards the start.
FORWARD = 1
BACKWARD = -1


@dataclass(frozen=True, slots=True)
class RouteGeometry:
    """A route with its distance table and stop offsets resolved."""

    route: Route
    cumulative: tuple[float, ...]
    #: Distance along the polyline at which each stop sits, in stop order.
    stop_distances: tuple[float, ...]

    @classmethod
    def build(cls, route: Route) -> RouteGeometry:
        cumulative = cumulative_distances(route.geometry)
        stop_distances = tuple(cumulative[stop.geometry_index] for stop in route.stops)
        return cls(route=route, cumulative=cumulative, stop_distances=stop_distances)

    @property
    def total_distance_m(self) -> float:
        return self.cumulative[-1]

    def locate(self, distance_m: float) -> tuple[Coordinate, int, float]:
        """Return position, segment index and bearing at a distance along the route."""
        return point_at_distance(self.route.geometry, self.cumulative, distance_m)

    def stop_distance(self, stop_id: str) -> float | None:
        """Distance along the route at which a stop sits, or ``None`` if unknown."""
        for stop, distance in zip(self.route.stops, self.stop_distances, strict=True):
            if stop.id == stop_id:
                return distance
        return None

    def progress(self, distance_m: float) -> float:
        """Fraction of the route covered, in ``[0, 1]``."""
        if self.total_distance_m <= 0:
            return 0.0
        return min(1.0, max(0.0, distance_m / self.total_distance_m))

    def distance_to(self, from_m: float, to_m: float, direction: int) -> float:
        """Distance a shuttle must still travel to reach a point on the route.

        This is the calculation that makes "distance to the shuttle" and "time
        until it reaches me" different numbers. A shuttle 50 m away that has
        just passed your stop must travel almost the whole route to come back,
        and this returns that longer distance - never the straight line.
        """
        total = self.total_distance_m
        if total <= 0:
            return 0.0

        if self.route.loop_mode is LoopMode.LOOP:
            # A looping route only ever moves forward, wrapping at the end.
            return (to_m - from_m) % total

        if direction == FORWARD:
            if to_m >= from_m:
                return to_m - from_m
            # Overshot: run to the far end, turn around, come back.
            return (total - from_m) + (total - to_m)

        if to_m <= from_m:
            return from_m - to_m
        return from_m + to_m

    def stops_between(self, from_m: float, to_m: float, direction: int) -> int:
        """How many stops a shuttle calls at before reaching a target point.

        Used to add dwell time to an ETA: each intervening stop costs the
        shuttle time it is not spending moving.
        """
        travel = self.distance_to(from_m, to_m, direction)
        if travel <= 0:
            return 0

        return sum(
            1
            for stop_distance in self.stop_distances
            if 0 < self.distance_to(from_m, stop_distance, direction) < travel
        )
