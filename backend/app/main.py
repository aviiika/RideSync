"""FastAPI application factory."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import Settings, get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger("shuttle")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application. Accepting settings keeps this testable."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("API started - data dir: %s", settings.data_dir)
        yield
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
