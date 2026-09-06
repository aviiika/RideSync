"""Shuttle queries: what is nearby, when does it arrive, is it worth waiting.

This service composes the simulation engine (where shuttles are), the ETA
engine (when they arrive) and the recommendation policy (what to do about it).
It owns none of that logic itself, which is what keeps each of those three
replaceable on its own.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.eta import EtaEngine, EtaEstimate
from app.geo import haversine_distance
from app.geo.route_geometry import RouteGeometry
from app.models import Coordinate, Route, Shuttle, Stop
from app.services.recommendation import Recommendation, recommend
from app.services.route_service import RouteService
from app.simulation import SimulationEngine


@dataclass(frozen=True, slots=True)
class ShuttleSnapshot:
    """Everything the UI needs about one shuttle, relative to one rider."""

    shuttle: Shuttle
    route: Route
    #: Straight-line distance from the rider. Shown, never used to rank.
    direct_distance_m: float
    #: The stop this estimate is for.
    target_stop: Stop | None
    eta: EtaEstimate | None
    recommendation: Recommendation

    @property
    def eta_minutes(self) -> int | None:
        return self.eta.minutes if self.eta else None


class ShuttleService:
    """Reads live shuttle state and answers rider-facing questions."""

    def __init__(
        self,
        engine: SimulationEngine,
        eta_engine: EtaEngine,
        route_service: RouteService,
    ) -> None:
        self._engine = engine
        self._eta_engine = eta_engine
        self._route_service = route_service

    # ------------------------------------------------------------------ reads

    def list_shuttles(self, route_id: str | None = None) -> tuple[Shuttle, ...]:
        """Live shuttles, optionally filtered to one route.

        An unknown route raises rather than returning an empty tuple: silently
        answering "no shuttles" to a typo hides the mistake from the caller.
        """
        if route_id is None:
            return self._engine.shuttles

        self._route_service.get_route(route_id)
        return tuple(shuttle for shuttle in self._engine.shuttles if shuttle.route_id == route_id)

    def get_shuttle(self, shuttle_id: str) -> Shuttle | None:
        return self._engine.get_shuttle(shuttle_id)

    def geometry_for(self, route_id: str) -> RouteGeometry | None:
        return self._engine.geometry_for(route_id)

    # --------------------------------------------------------------- analysis

    def nearest_stop(self, user: Coordinate, route_id: str | None = None) -> Stop | None:
        """The stop a rider would walk to: nearest in a straight line."""
        stops = self._route_service.list_stops(route_id)
        if not stops:
            return None
        return min(stops, key=lambda stop: haversine_distance(user, stop.position))

    def snapshot(self, shuttle: Shuttle, user: Coordinate, stop: Stop | None) -> ShuttleSnapshot:
        """Describe one shuttle from a rider's point of view."""
        route = self._route_service.get_route(shuttle.route_id)
        geometry = self._engine.geometry_for(shuttle.route_id)

        eta: EtaEstimate | None = None
        target = stop if stop is not None and stop.route_id == shuttle.route_id else None
        if geometry is not None and target is not None:
            eta = self._eta_engine.estimate(shuttle, geometry, target.id)

        return ShuttleSnapshot(
            shuttle=shuttle,
            route=route,
            direct_distance_m=haversine_distance(user, shuttle.position),
            target_stop=target,
            eta=eta,
            recommendation=recommend(eta.minutes if eta else None),
        )

    def snapshots(
        self, user: Coordinate, route_id: str | None = None
    ) -> tuple[ShuttleSnapshot, ...]:
        """Every shuttle, described for this rider and sorted most useful first.

        Ordering is by ETA, not by distance. A shuttle parked 80 m away that
        has just passed the rider's stop is less useful than one 900 m away
        heading towards it, and sorting by distance would get that backwards.
        Shuttles with no usable estimate sort last rather than being dropped.
        """
        shuttles = self.list_shuttles(route_id)

        results = []
        for shuttle in shuttles:
            stop = self.nearest_stop(user, shuttle.route_id)
            results.append(self.snapshot(shuttle, user, stop))

        return tuple(
            sorted(
                results,
                key=lambda snap: (snap.eta is None, snap.eta.seconds if snap.eta else 0.0),
            )
        )

    def nearest(self, user: Coordinate, route_id: str | None = None) -> ShuttleSnapshot | None:
        """The shuttle a rider should actually wait for, or ``None`` if there is none."""
        snapshots = self.snapshots(user, route_id)
        return snapshots[0] if snapshots else None
