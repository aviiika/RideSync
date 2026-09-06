"""Shuttle, ETA and recommendation wire schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models import Route, Shuttle
from app.services.recommendation import Recommendation
from app.services.shuttle_service import ShuttleSnapshot


class RecommendationResponse(BaseModel):
    """Should the rider wait?"""

    level: str
    label: str
    detail: str

    @classmethod
    def from_domain(cls, recommendation: Recommendation) -> RecommendationResponse:
        return cls(
            level=recommendation.level.value,
            label=recommendation.label,
            detail=recommendation.detail,
        )


class ConfidenceResponse(BaseModel):
    """A heuristic band, deliberately not presented as a probability."""

    level: str
    label: str
    reason: str


class EtaResponse(BaseModel):
    """An arrival estimate, with the inputs it came from."""

    minutes: int = Field(description="Whole minutes, for display as ~N min.")
    seconds: float
    remaining_distance_m: float
    effective_speed_kmh: float
    intervening_stops: int
    source: str = Field(description="Which estimator produced this.")
    confidence: ConfidenceResponse | None = None


class ShuttleResponse(BaseModel):
    """Live state for one vehicle. Telemetry is simulated, not real GPS."""

    id: str
    route_id: str
    name: str
    status: str
    latitude: float
    longitude: float
    heading: float
    speed_kmh: float
    progress: float
    occupancy: float
    next_stop_id: str | None
    next_stop_name: str | None
    updated_at: datetime

    @classmethod
    def from_domain(cls, snapshot: ShuttleSnapshot) -> ShuttleResponse:
        return cls.from_shuttle(snapshot.shuttle, snapshot.route)

    @classmethod
    def from_shuttle(cls, shuttle: Shuttle, route: Route) -> ShuttleResponse:
        stops = route.stops
        next_stop = stops[shuttle.next_stop_index] if shuttle.next_stop_index < len(stops) else None

        return cls(
            id=shuttle.id,
            route_id=shuttle.route_id,
            name=shuttle.name,
            status=shuttle.status.value,
            latitude=shuttle.position.latitude,
            longitude=shuttle.position.longitude,
            heading=round(shuttle.heading, 1),
            speed_kmh=shuttle.speed_kmh,
            progress=round(shuttle.progress, 4),
            occupancy=shuttle.occupancy,
            next_stop_id=next_stop.id if next_stop else None,
            next_stop_name=next_stop.name if next_stop else None,
            updated_at=shuttle.updated_at,
        )


class ShuttleSnapshotResponse(BaseModel):
    """A shuttle described relative to a rider: distance, ETA and advice."""

    shuttle: ShuttleResponse
    route_name: str
    route_color: str
    direct_distance_m: float = Field(
        description="Straight-line distance from the rider - not the travel distance."
    )
    target_stop_id: str | None
    target_stop_name: str | None
    eta: EtaResponse | None
    recommendation: RecommendationResponse
    walk_seconds: float | None = Field(
        default=None, description="Time on foot from the rider to the target stop."
    )
    walk_minutes: int | None = None
    reachable: bool | None = Field(
        default=None, description="False when the shuttle arrives before the rider can."
    )

    @classmethod
    def from_domain(cls, snapshot: ShuttleSnapshot) -> ShuttleSnapshotResponse:
        eta = None
        if snapshot.eta is not None:
            eta = EtaResponse(
                minutes=snapshot.eta.minutes,
                seconds=round(snapshot.eta.seconds, 1),
                remaining_distance_m=round(snapshot.eta.features.remaining_distance_m, 1),
                effective_speed_kmh=round(snapshot.eta.features.effective_speed_kmh, 1),
                intervening_stops=snapshot.eta.features.intervening_stops,
                source=snapshot.eta.source,
                confidence=(
                    ConfidenceResponse(
                        level=snapshot.confidence.level.value,
                        label=snapshot.confidence.label,
                        reason=snapshot.confidence.reason,
                    )
                    if snapshot.confidence
                    else None
                ),
            )

        return cls(
            shuttle=ShuttleResponse.from_domain(snapshot),
            route_name=snapshot.route.name,
            route_color=snapshot.route.color,
            direct_distance_m=round(snapshot.direct_distance_m, 1),
            target_stop_id=snapshot.target_stop.id if snapshot.target_stop else None,
            target_stop_name=snapshot.target_stop.name if snapshot.target_stop else None,
            eta=eta,
            recommendation=RecommendationResponse.from_domain(snapshot.recommendation),
            walk_seconds=(
                None if snapshot.walk_seconds is None else round(snapshot.walk_seconds, 1)
            ),
            walk_minutes=snapshot.walk_minutes,
            reachable=(
                None
                if snapshot.recommendation.level.value == "UNAVAILABLE"
                else snapshot.recommendation.level.value != "TOO_TIGHT"
            ),
        )
