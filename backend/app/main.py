"""FastAPI application factory."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.api.deps import (
    get_history_service,
    get_route_service,
    get_simulation_engine,
    get_simulation_runner,
)
from app.config import Settings, get_settings
from app.services.history_service import network_fingerprint

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger("shuttle")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application. Accepting settings keeps this testable."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # The simulation starts running immediately: a demo that needs a button
        # pressed before anything moves is a worse first five seconds.
        # History describing a different set of stops would poison the
        # measured ETA error, so it is discarded when the network changes.
        if settings.history_enabled:
            get_history_service().adopt_network(
                network_fingerprint(get_route_service().list_routes())
            )

        engine = get_simulation_engine()
        engine.start()

        runner = get_simulation_runner()
        await runner.start()
        logger.info(
            "API started - %d shuttles on %d routes",
            len(engine.shuttles),
            len(engine.shuttles) // max(1, settings.shuttles_per_route),
        )

        yield

        await runner.stop()
        logger.info("API stopped")

    app = FastAPI(
        lifespan=lifespan,
        title=settings.app_name,
        version=settings.api_version,
        description=(
            "Real-time shuttle tracking and ETA simulation platform. "
            "Telemetry is simulated, not real GPS."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    return app


app = create_app()
