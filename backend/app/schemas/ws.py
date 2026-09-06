"""WebSocket message contracts.

Every frame is a tagged object with a ``type`` field, so the frontend can
discriminate on it and TypeScript can narrow the union.

One deliberate departure from the specification's sketch: updates are batched -
a single ``SHUTTLE_UPDATE`` carries every shuttle that moved rather than one
frame per vehicle. At the 20-50 shuttle target that is one message and one
React state commit per tick instead of fifty, which is the difference between a
smooth map and a stuttering one.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.shuttle import ShuttleResponse
from app.schemas.simulation import SimulationStateResponse


def _now() -> datetime:
    return datetime.now(UTC)


class ShuttleUpdateMessage(BaseModel):
    """Live positions, broadcast once per simulation tick."""

    type: Literal["SHUTTLE_UPDATE"] = "SHUTTLE_UPDATE"
    timestamp: datetime = Field(default_factory=_now)
    shuttles: list[ShuttleResponse]


class SimulationStateMessage(BaseModel):
    """Sent when the simulation is started, paused, reset or re-sped."""

    type: Literal["SIMULATION_STATE"] = "SIMULATION_STATE"
    timestamp: datetime = Field(default_factory=_now)
    state: SimulationStateResponse


class ErrorMessage(BaseModel):
    """A problem the client should surface rather than swallow."""

    type: Literal["ERROR"] = "ERROR"
    timestamp: datetime = Field(default_factory=_now)
    detail: str
