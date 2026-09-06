"""Simulation control schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.simulation import SimulationEngine, SimulationState


class SimulationStateResponse(BaseModel):
    """Current state of the simulation clock."""

    running: bool
    speed_multiplier: float
    elapsed_seconds: float
    tick_count: int
    started_at: datetime | None
    shuttle_count: int
    seed: int = Field(description="Runs with the same seed are identical.")

    @classmethod
    def from_domain(
        cls, state: SimulationState, engine: SimulationEngine
    ) -> SimulationStateResponse:
        return cls(
            running=state.running,
            speed_multiplier=state.speed_multiplier,
            elapsed_seconds=round(state.elapsed_seconds, 1),
            tick_count=state.tick_count,
            started_at=state.started_at,
            shuttle_count=len(engine.shuttles),
            seed=engine.config.seed,
        )


class SpeedRequest(BaseModel):
    """Demo speed control. Only the values the UI offers are accepted."""

    multiplier: float = Field(description="One of 1, 2 or 5.")
