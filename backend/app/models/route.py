"""Route and stop domain models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.models.geo import Coordinate


class LoopMode(StrEnum):
    """What a shuttle does when it reaches the end of its route geometry."""

    LOOP = "LOOP"
    """Jump back to the first point - only valid for closed geometry."""

    REVERSE = "REVERSE"
    """Turn around and travel the same geometry backwards."""


@dataclass(frozen=True, slots=True)
class Stop:
    """A boarding point along a route."""

    id: str
    name: str
    route_id: str
    sequence: int
    position: Coordinate
    #: Index into the route's geometry where this stop sits.
    geometry_index: int


@dataclass(frozen=True, slots=True)
class Route:
    """A shuttle route: an ordered polyline plus the stops along it."""

    id: str
    name: str
    color: str
    average_speed_kmh: float
    loop_mode: LoopMode
    geometry: tuple[Coordinate, ...]
    stops: tuple[Stop, ...]

    def stop_by_id(self, stop_id: str) -> Stop | None:
        return next((stop for stop in self.stops if stop.id == stop_id), None)
