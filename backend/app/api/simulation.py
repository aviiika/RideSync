"""Demo controls: start, pause, reset, speed.

These are a first-class feature, not a debug hatch - a pitch depends on being
able to start, speed up and reset the simulation on demand.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_simulation_engine, get_simulation_runner
from app.realtime import SimulationRunner
from app.schemas.shuttle import ShuttleResponse
from app.schemas.simulation import DelayRequest, SimulationStateResponse, SpeedRequest
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


@router.post("/delay", response_model=ShuttleResponse)
async def inject_delay(
    request: DelayRequest,
    engine: SimulationEngine = Depends(get_simulation_engine),
) -> ShuttleResponse:
    """Slow one shuttle for a while, so the delayed path is demonstrable."""
    try:
        shuttle = engine.delay_shuttle(request.shuttle_id, request.seconds)
    except KeyError as exc:
        raise HTTPException(404, detail=f"unknown shuttle: {request.shuttle_id}") from exc
    except ValueError as exc:
        raise HTTPException(HTTP_422_UNPROCESSABLE, detail=str(exc)) from exc

    geometry = engine.geometry_for(shuttle.route_id)
    if geometry is None:
        raise HTTPException(404, detail=f"unknown route: {shuttle.route_id}")

    return ShuttleResponse.from_shuttle(shuttle, geometry.route)


@router.post("/clear-delays", response_model=SimulationStateResponse)
async def clear_delays(
    engine: SimulationEngine = Depends(get_simulation_engine),
    runner: SimulationRunner = Depends(get_simulation_runner),
) -> SimulationStateResponse:
    """Return every delayed shuttle to normal service."""
    engine.clear_delays()
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
