"""Route repository: the protocol plus its JSON-backed implementation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from app.models import Coordinate, InvalidCoordinateError, LoopMode, Route, Stop


class RouteDataError(RuntimeError):
    """Raised when seed data is missing or malformed."""


class RouteRepository(Protocol):
    """Read access to the routes and stops that make up the network."""

    def list_routes(self) -> tuple[Route, ...]:
        """Return every route, ordered by id."""
        ...

    def get_route(self, route_id: str) -> Route | None:
        """Return one route, or ``None`` when the id is unknown."""
        ...

    def list_stops(self, route_id: str | None = None) -> tuple[Stop, ...]:
        """Return every stop, optionally filtered to a single route."""
        ...


class JsonRouteRepository(RouteRepository):
    """Loads routes from ``data/routes/*.json`` once and caches them in memory."""

    def __init__(self, routes_dir: Path) -> None:
        self._routes_dir = routes_dir
        self._routes: tuple[Route, ...] | None = None

    def _load(self) -> tuple[Route, ...]:
        if self._routes is not None:
            return self._routes

        if not self._routes_dir.is_dir():
            raise RouteDataError(f"route data directory not found: {self._routes_dir}")

        files = sorted(self._routes_dir.glob("*.json"))
        if not files:
            raise RouteDataError(f"no route JSON files in {self._routes_dir}")

        routes = tuple(_parse_route(path) for path in files)

        seen: set[str] = set()
        for route in routes:
            if route.id in seen:
                raise RouteDataError(f"duplicate route id: {route.id}")
            seen.add(route.id)

        self._routes = routes
        return routes

    def list_routes(self) -> tuple[Route, ...]:
        return self._load()

    def get_route(self, route_id: str) -> Route | None:
        return next((route for route in self._load() if route.id == route_id), None)

    def list_stops(self, route_id: str | None = None) -> tuple[Stop, ...]:
        return tuple(
            stop
            for route in self._load()
            if route_id is None or route.id == route_id
            for stop in route.stops
        )


def _parse_route(path: Path) -> Route:
    """Parse and validate one route JSON file."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RouteDataError(f"could not read route file {path.name}: {exc}") from exc

    try:
        route_id = str(raw["id"])
        geometry_raw = raw["geometry"]
        stops_raw = raw["stops"]
    except (KeyError, TypeError) as exc:
        raise RouteDataError(f"{path.name} is missing a required field: {exc}") from exc

    if not isinstance(geometry_raw, list) or len(geometry_raw) < 2:
        raise RouteDataError(f"{path.name}: geometry needs at least two points")

    try:
        geometry = tuple(Coordinate.from_geojson(point) for point in geometry_raw)
    except InvalidCoordinateError as exc:
        raise RouteDataError(f"{path.name}: {exc}") from exc

    try:
        loop_mode = LoopMode(raw.get("loop_mode", LoopMode.LOOP.value))
    except ValueError as exc:
        raise RouteDataError(f"{path.name}: unknown loop_mode {raw.get('loop_mode')!r}") from exc

    stops = tuple(
        _parse_stop(stop_raw, route_id=route_id, geometry_length=len(geometry), source=path.name)
        for stop_raw in sorted(stops_raw, key=lambda item: item.get("sequence", 0))
    )
    if not stops:
        raise RouteDataError(f"{path.name}: route has no stops")

    return Route(
        id=route_id,
        name=str(raw.get("name", route_id)),
        color=str(raw.get("color", "#2563eb")),
        average_speed_kmh=float(raw.get("average_speed_kmh", 20)),
        loop_mode=loop_mode,
        geometry=geometry,
        stops=stops,
    )


def _parse_stop(raw: object, *, route_id: str, geometry_length: int, source: str) -> Stop:
    if not isinstance(raw, dict):
        raise RouteDataError(f"{source}: each stop must be an object")

    try:
        position = Coordinate(
            latitude=float(raw["latitude"]),
            longitude=float(raw["longitude"]),
        )
    except (KeyError, TypeError, ValueError, InvalidCoordinateError) as exc:
        raise RouteDataError(f"{source}: invalid stop coordinate: {exc}") from exc

    geometry_index = int(raw.get("geometry_index", 0))
    if not 0 <= geometry_index < geometry_length:
        raise RouteDataError(
            f"{source}: stop {raw.get('id')!r} has geometry_index {geometry_index} "
            f"outside 0..{geometry_length - 1}"
        )

    return Stop(
        id=str(raw["id"]),
        name=str(raw.get("name", raw["id"])),
        route_id=route_id,
        sequence=int(raw.get("sequence", 0)),
        position=position,
        geometry_index=geometry_index,
    )
