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

    #: Vehicles spawned on each route.
    shuttles_per_route: int = Field(default=2, ge=1, le=20)

    #: Seconds a shuttle waits at each stop, used by both the simulation and
    #: the ETA estimate so the two agree.
    dwell_seconds: float = Field(default=20.0, ge=0, le=300)

    #: Multiplier padding ETAs for traffic and boarding friction.
    eta_delay_factor: float = Field(default=1.0, ge=0.5, le=3.0)

    #: Where trip history lives. SQLite by default: append-only, local, and
    #: no container to start before a demo.
    database_url: str = "sqlite:///./data/ridesync.db"

    #: History is observability; turn it off and nothing user-facing changes.
    history_enabled: bool = True

    #: Signing key for session tokens. The default is obviously not a secret
    #: and is fine for a local demo; set AUTH_SECRET anywhere it matters.
    auth_secret: str = "dev-only-not-a-secret"

    #: How long a sign-in lasts.
    session_hours: int = Field(default=12, ge=1, le=720)

    #: Average walking speed, used to decide whether a rider can reach a stop
    #: before the shuttle does. 4.8 km/h is a normal adult pace.
    walking_speed_kmh: float = Field(default=4.8, gt=0, le=15)

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
