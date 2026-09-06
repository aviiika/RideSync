"""Dependency wiring.

Composition happens here so services stay unaware of FastAPI and remain
directly constructible in tests. Everything is an ``lru_cache`` singleton
because the simulation is live state: a second engine would mean a second,
divergent set of shuttles.
"""

from functools import lru_cache

from app.config import get_settings
from app.data.repository import JsonRouteRepository, RouteRepository
from app.db import Database
from app.eta import DeterministicEtaEngine, EtaConfig, EtaEngine
from app.realtime import ConnectionManager, SimulationRunner
from app.services import RouteService
from app.services.auth_service import AuthService
from app.services.history_service import HistoryService
from app.services.shuttle_service import ShuttleService
from app.simulation import SimulationConfig, SimulationEngine


@lru_cache
def get_route_repository() -> RouteRepository:
    return JsonRouteRepository(routes_dir=get_settings().routes_dir)


@lru_cache
def get_route_service() -> RouteService:
    return RouteService(repository=get_route_repository())


@lru_cache
def get_simulation_engine() -> SimulationEngine:
    settings = get_settings()
    return SimulationEngine(
        routes=get_route_service().list_routes(),
        config=SimulationConfig(
            shuttles_per_route=settings.shuttles_per_route,
            dwell_seconds=settings.dwell_seconds,
            seed=settings.simulation_seed,
        ),
    )


@lru_cache
def get_eta_engine() -> EtaEngine:
    settings = get_settings()
    return DeterministicEtaEngine(
        EtaConfig(
            dwell_seconds=settings.dwell_seconds,
            delay_factor=settings.eta_delay_factor,
        )
    )


@lru_cache
def get_shuttle_service() -> ShuttleService:
    return ShuttleService(
        engine=get_simulation_engine(),
        eta_engine=get_eta_engine(),
        route_service=get_route_service(),
        walking_speed_kmh=get_settings().walking_speed_kmh,
    )


@lru_cache
def get_auth_service() -> AuthService:
    settings = get_settings()
    return AuthService(secret=settings.auth_secret, session_hours=settings.session_hours)


@lru_cache
def get_database() -> Database:
    database = Database(get_settings().database_url)
    database.create_all()
    return database


@lru_cache
def get_history_service() -> HistoryService:
    return HistoryService(database=get_database())


@lru_cache
def get_connection_manager() -> ConnectionManager:
    return ConnectionManager()


@lru_cache
def get_simulation_runner() -> SimulationRunner:
    settings = get_settings()
    return SimulationRunner(
        engine=get_simulation_engine(),
        manager=get_connection_manager(),
        tick_ms=settings.simulation_tick_ms,
        eta_engine=get_eta_engine(),
        history=get_history_service() if settings.history_enabled else None,
    )


def reset_dependencies() -> None:
    """Drop every singleton. Used by tests so each gets a fresh world."""
    for provider in (
        get_route_repository,
        get_route_service,
        get_simulation_engine,
        get_eta_engine,
        get_shuttle_service,
        get_auth_service,
        get_database,
        get_history_service,
        get_connection_manager,
        get_simulation_runner,
    ):
        provider.cache_clear()
