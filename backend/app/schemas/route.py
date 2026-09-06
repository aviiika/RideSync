"""Route and stop wire schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models import Route, Stop


class StopResponse(BaseModel):
    """A boarding point."""

    id: str
    name: str
    route_id: str
    sequence: int
    latitude: float
    longitude: float

    @classmethod
    def from_domain(cls, stop: Stop) -> StopResponse:
        return cls(
            id=stop.id,
            name=stop.name,
            route_id=stop.route_id,
            sequence=stop.sequence,
            latitude=stop.position.latitude,
            longitude=stop.position.longitude,
        )


class RouteResponse(BaseModel):
    """A route, with geometry in GeoJSON ``[lng, lat]`` order for MapLibre."""

    id: str
    name: str
    color: str
    average_speed_kmh: float
    loop_mode: str
    geometry: list[list[float]] = Field(description="Polyline as [longitude, latitude] pairs.")
    stops: list[StopResponse]

    @classmethod
    def from_domain(cls, route: Route) -> RouteResponse:
        return cls(
            id=route.id,
            name=route.name,
            color=route.color,
            average_speed_kmh=route.average_speed_kmh,
            loop_mode=route.loop_mode.value,
            geometry=[point.to_geojson() for point in route.geometry],
            stops=[StopResponse.from_domain(stop) for stop in route.stops],
        )
