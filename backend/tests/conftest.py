"""Shared fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.api.deps import reset_dependencies
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
    # Dependencies are lru_cached singletons and the simulation is live state,
    # so each test gets a freshly seeded world.
    reset_dependencies()
    with TestClient(create_app()) as test_client:
        yield test_client
    reset_dependencies()
