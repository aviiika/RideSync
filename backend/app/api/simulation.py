"""Demo controls: start, pause, reset, speed.

These are a first-class feature, not a debug hatch - a pitch depends on being
able to start, speed up and reset the simulation on demand.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_simulation_engine, get_simulation_runner
from app.realtime import SimulationRunner
from app.schemas.simulation import SimulationStateResponse, SpeedRequest
from app.simulation import SimulationEngine

HTTP_422_UNPROCESSABLE = 422

router = APIRouter(prefix="/simulation", tags=["simulation"])


async def _respond(
    engine: SimulationEngine,
    runner: SimulationRunner,
) -> SimulationStateResponse:
    """Return the control state and push it to every connected client."""
    await runner.broadcast_state()
    return SimulationStateResponse.from_domain(engine.state, engine)


@router.get("", response_model=SimulationStateResponse)
def get_state(
    engine: SimulationEngine = Depends(get_simulation_engine),
) -> SimulationStateResponse:
    """Current simulation clock state."""
    return SimulationStateResponse.from_domain(engine.state, engine)


@router.post("/start", response_model=SimulationStateResponse)
async def start(
    engine: SimulationEngine = Depends(get_simulation_engine),
    runner: SimulationRunner = Depends(get_simulation_runner),
) -> SimulationStateResponse:
    """Begin moving shuttles."""
    engine.start()
    return await _respond(engine, runner)


@router.post("/pause", response_model=SimulationStateResponse)
async def pause(
    engine: SimulationEngine = Depends(get_simulation_engine),
    runner: SimulationRunner = Depends(get_simulation_runner),
) -> SimulationStateResponse:
    """Freeze every shuttle where it is."""
    engine.pause()
    return await _respond(engine, runner)


@router.post("/reset", response_model=SimulationStateResponse)
async def reset(
    engine: SimulationEngine = Depends(get_simulation_engine),
    runner: SimulationRunner = Depends(get_simulation_runner),
) -> SimulationStateResponse:
    """Return to the seeded starting state, paused."""
    engine.reset()
    return await _respond(engine, runner)


@router.post("/speed", response_model=SimulationStateResponse)
async def set_speed(
    request: SpeedRequest,
    engine: SimulationEngine = Depends(get_simulation_engine),
    runner: SimulationRunner = Depends(get_simulation_runner),
) -> SimulationStateResponse:
    """Change how fast simulated time runs."""
    try:
        engine.set_speed(request.multiplier)
    except ValueError as exc:
        raise HTTPException(HTTP_422_UNPROCESSABLE, detail=str(exc)) from exc
    return await _respond(engine, runner)
