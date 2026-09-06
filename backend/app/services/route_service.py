"""Route and stop queries."""

from __future__ import annotations

from app.data.repository import RouteRepository
from app.models import Route, Stop


class RouteNotFoundError(LookupError):
    """Raised when a caller asks for a route id that does not exist."""

    def __init__(self, route_id: str) -> None:
        super().__init__(f"unknown route: {route_id}")
        self.route_id = route_id


class RouteService:
    """Reads the route network. The repository is injected so the storage
    backend can change without touching this class."""

    def __init__(self, repository: RouteRepository) -> None:
        self._repository = repository

    def list_routes(self) -> tuple[Route, ...]:
        return self._repository.list_routes()

    def get_route(self, route_id: str) -> Route:
        route = self._repository.get_route(route_id)
        if route is None:
            raise RouteNotFoundError(route_id)
        return route

    def list_stops(self, route_id: str | None = None) -> tuple[Stop, ...]:
        if route_id is not None:
            # Surface a 404 for an unknown route rather than an empty list.
            self.get_route(route_id)
        return self._repository.list_stops(route_id)
