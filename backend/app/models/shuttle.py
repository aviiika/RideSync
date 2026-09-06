"""Shuttle domain model.

A shuttle's authoritative position is *how far along its route it is*, not a
latitude/longitude pair. Coordinates are derived from that distance every tick,
which is what stops markers from teleporting: a shuttle can only ever be
somewhere on its own route geometry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from app.models.geo import Coordinate


class ShuttleStatus(StrEnum):
    """Service state, as shown to the rider."""

    IN_SERVICE = "IN_SERVICE"
    ARRIVING = "ARRIVING"
    AT_STOP = "AT_STOP"
    DELAYED = "DELAYED"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"
    STALE = "STALE"
    """No fresh telemetry - never presented as a live position."""


@dataclass(slots=True)
class Shuttle:
    """Live state for one simulated vehicle."""

    id: str
    route_id: str
    name: str
    #: Metres travelled along the route polyline from its first point.
    distance_m: float
    #: ``+1`` travelling along the polyline, ``-1`` travelling back down it.
    direction: int
    position: Coordinate
    heading: float
    speed_kmh: float
    status: ShuttleStatus
    progress: float
    occupancy: float
    #: Seconds still to wait at the current stop, if any.
    dwell_remaining_s: float = 0.0
    #: Index of the stop the shuttle is heading for.
    next_stop_index: int = 0
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_moving(self) -> bool:
        return self.dwell_remaining_s <= 0 and self.status is not ShuttleStatus.OUT_OF_SERVICE
