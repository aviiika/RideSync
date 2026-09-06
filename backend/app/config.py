"""Application settings.

All environment-specific values are read from the environment (or a local
``.env`` file). Nothing here may contain a secret literal.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# backend/app/config.py -> backend/app -> backend -> repository root
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration for the API and simulation engine."""

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Shuttle Tracking & ETA Simulation"
    api_version: str = "0.1.0"

    #: Directory holding the seed route/stop JSON files.
    data_dir: Path = REPO_ROOT / "data"

    #: Origins permitted to call the API and open the WebSocket.
    #:
    #: ``NoDecode`` stops pydantic-settings from trying to JSON-decode the raw
    #: value, so a plain comma-separated ``CORS_ORIGINS=a,b`` in .env reaches
    #: the validator below instead of raising a JSON error.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    #: Simulation tick interval in milliseconds (spec recommends 250-1000).
    simulation_tick_ms: int = Field(default=500, ge=100, le=5000)

    #: Seed making demo runs deterministic and therefore repeatable.
    simulation_seed: int = 42

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Accept ``CORS_ORIGINS=a,b`` as well as a JSON list."""
        if isinstance(value, str) and not value.strip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def routes_dir(self) -> Path:
        return self.data_dir / "routes"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
