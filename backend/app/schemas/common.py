"""Shared response schemas."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Liveness payload for ``GET /health``."""

    status: str = Field(examples=["ok"])
    version: str = Field(examples=["0.1.0"])
    routes_loaded: int = Field(description="Number of routes read from seed data.")
