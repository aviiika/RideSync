"""Coordinate primitive shared by the geo, simulation and ETA engines."""

from __future__ import annotations

from dataclasses import dataclass

MIN_LATITUDE = -90.0
MAX_LATITUDE = 90.0
MIN_LONGITUDE = -180.0
MAX_LONGITUDE = 180.0


class InvalidCoordinateError(ValueError):
    """Raised when a latitude/longitude pair is outside the valid range."""


@dataclass(frozen=True, slots=True)
class Coordinate:
    """A WGS84 point.

    Stored as ``(latitude, longitude)``. Note that GeoJSON - and therefore the
    seed data and every MapLibre payload - uses the opposite ``[lng, lat]``
    order, so conversions go through :meth:`from_geojson` rather than being
    written out by hand at each call site.
    """

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not MIN_LATITUDE <= self.latitude <= MAX_LATITUDE:
            raise InvalidCoordinateError(f"latitude out of range: {self.latitude}")
        if not MIN_LONGITUDE <= self.longitude <= MAX_LONGITUDE:
            raise InvalidCoordinateError(f"longitude out of range: {self.longitude}")

    @classmethod
    def from_geojson(cls, position: object) -> Coordinate:
        """Build a coordinate from a GeoJSON ``[longitude, latitude]`` pair."""
        if not isinstance(position, (list, tuple)) or len(position) != 2:
            raise InvalidCoordinateError(f"expected a [lng, lat] pair, got: {position!r}")
        longitude, latitude = position
        try:
            return cls(latitude=float(latitude), longitude=float(longitude))
        except (TypeError, ValueError) as exc:
            raise InvalidCoordinateError(f"non-numeric coordinate: {position!r}") from exc

    def to_geojson(self) -> list[float]:
        """Return this coordinate as a GeoJSON ``[longitude, latitude]`` pair."""
        return [self.longitude, self.latitude]
