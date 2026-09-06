"""Dependency wiring.

Composition happens here so services stay unaware of FastAPI and remain
directly constructible in tests.
"""

from functools import lru_cache

from app.config import get_settings
from app.data.repository import JsonRouteRepository, RouteRepository
from app.services import RouteService


@lru_cache
def get_route_repository() -> RouteRepository:
    return JsonRouteRepository(routes_dir=get_settings().routes_dir)


@lru_cache
def get_route_service() -> RouteService:
    return RouteService(repository=get_route_repository())
