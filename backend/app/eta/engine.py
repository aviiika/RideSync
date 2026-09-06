"""Estimated time of arrival.

The MVP estimator is deterministic arithmetic - remaining route distance over
an effective speed, plus dwell time at the stops in between. It is not a model
and is not presented as one.

:class:`EtaEngine` is the seam a learned estimator would slot into. A future
model would consume the same :class:`EtaFeatures` (distance, current and
average speed, route, stop, time of day, dwell, headway) and return the same
:class:`EtaEstimate`, so nothing above this module would change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.geo.route_geometry import RouteGeometry
from app.models import Shuttle, ShuttleStatus

SECONDS_PER_HOUR = 3600.0


@dataclass(frozen=True, slots=True)
class EtaConfig:
    """Tunable inputs to the deterministic estimator."""

    #: Seconds a shuttle waits at each stop it calls at on the way.
    dwell_seconds: float = 20.0
    #: Speeds below this are treated as a stop, not as crawling progress, so a
    #: shuttle waiting at a stop cannot produce an ETA of several hours.
    min_speed_kmh: float = 5.0
    #: Multiplier padding the estimate for traffic and boarding friction.
    delay_factor: float = 1.0


@dataclass(frozen=True, slots=True)
class EtaFeatures:
    """The inputs an estimate was made from.

    Returned alongside every estimate so the demo can show its working, and so
    the same fields can later become a feature vector for a trained model.
    """

    remaining_distance_m: float
    effective_speed_kmh: float
    intervening_stops: int
    dwell_seconds: float


@dataclass(frozen=True, slots=True)
class EtaEstimate:
    """An arrival estimate. Never a promise, and never false precision."""

    seconds: float
    distance_m: float
    features: EtaFeatures
    #: Which estimator produced this, so the UI can say so honestly.
    source: str = "deterministic"

    @property
    def minutes(self) -> int:
        """Whole minutes, for display as ``~N min``."""
        return max(0, round(self.seconds / 60))


class EtaEngine(Protocol):
    """Estimates arrival of a shuttle at a stop."""

    def estimate(
        self,
        shuttle: Shuttle,
        geometry: RouteGeometry,
        stop_id: str,
    ) -> EtaEstimate | None:
        """Return an estimate, or ``None`` when one cannot honestly be made."""
        ...


class DeterministicEtaEngine(EtaEngine):
    """``remaining route distance / effective speed``, plus dwell time.

    Returns ``None`` rather than a fabricated number when the shuttle is out of
    service or the stop is not on its route - the UI shows "ETA unavailable"
    instead of a plausible-looking lie.
    """

    def __init__(self, config: EtaConfig | None = None) -> None:
        self._config = config or EtaConfig()

    @property
    def config(self) -> EtaConfig:
        return self._config

    def estimate(
        self,
        shuttle: Shuttle,
        geometry: RouteGeometry,
        stop_id: str,
    ) -> EtaEstimate | None:
        if shuttle.status in (ShuttleStatus.OUT_OF_SERVICE, ShuttleStatus.STALE):
            return None

        target = geometry.stop_distance(stop_id)
        if target is None:
            return None

        remaining = geometry.distance_to(shuttle.distance_m, target, shuttle.direction)

        # A shuttle sitting at a stop reports ~0 km/h; fall back to the route's
        # scheduled speed so waiting does not inflate the estimate to infinity.
        speed = shuttle.speed_kmh
        if speed < self._config.min_speed_kmh:
            speed = geometry.route.average_speed_kmh
        speed = max(speed, self._config.min_speed_kmh)

        travel_seconds = (remaining / 1000.0) / speed * SECONDS_PER_HOUR

        intervening = geometry.stops_between(shuttle.distance_m, target, shuttle.direction)
        dwell_seconds = intervening * self._config.dwell_seconds + shuttle.dwell_remaining_s

        seconds = (travel_seconds + dwell_seconds) * self._config.delay_factor

        return EtaEstimate(
            seconds=seconds,
            distance_m=remaining,
            features=EtaFeatures(
                remaining_distance_m=remaining,
                effective_speed_kmh=speed,
                intervening_stops=intervening,
                dwell_seconds=dwell_seconds,
            ),
        )
