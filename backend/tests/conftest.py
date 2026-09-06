"""Shared fixtures."""

import os

import pytest
from fastapi.testclient import TestClient

from app.api.deps import reset_dependencies
from app.config import get_settings
from app.data.repository import JsonRouteRepository
from app.db import Database
from app.main import create_app
from app.services import RouteService


@pytest.fixture(scope="session", autouse=True)
def _isolate_history(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Never let a test run write to the demo database."""
    database = tmp_path_factory.mktemp("history") / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{database.as_posix()}"
    get_settings.cache_clear()


@pytest.fixture
def database(tmp_path) -> Database:
    """A fresh, isolated database per test."""
    instance = Database(f"sqlite:///{(tmp_path / 'history.db').as_posix()}")
    instance.create_all()
    return instance


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
