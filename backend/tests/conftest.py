"""Shared fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_route_repository, get_route_service
from app.config import get_settings
from app.data.repository import JsonRouteRepository
from app.main import create_app
from app.services import RouteService


@pytest.fixture
def repository() -> JsonRouteRepository:
    return JsonRouteRepository(routes_dir=get_settings().routes_dir)


@pytest.fixture
def route_service(repository: JsonRouteRepository) -> RouteService:
    return RouteService(repository=repository)


@pytest.fixture
def client() -> TestClient:
    # Dependencies are lru_cached singletons; clear them so each test builds
    # its own instances from the current settings.
    get_route_repository.cache_clear()
    get_route_service.cache_clear()
    return TestClient(create_app())
