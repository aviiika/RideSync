"""The simulation loop.

Drives the engine on a fixed wall-clock tick and broadcasts the result. This is
the only place that sleeps or reads the clock, which is exactly why the engine
itself stays a pure, instantly testable state machine.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time

from app.realtime.manager import ConnectionManager
from app.schemas.shuttle import ShuttleResponse
from app.schemas.simulation import SimulationStateResponse
from app.schemas.ws import ShuttleUpdateMessage, SimulationStateMessage
from app.simulation import SimulationEngine

logger = logging.getLogger("shuttle.simulation")


class SimulationRunner:
    """Ticks the engine and pushes updates to connected clients."""

    def __init__(
        self,
        engine: SimulationEngine,
        manager: ConnectionManager,
        tick_ms: int,
    ) -> None:
        self._engine = engine
        self._manager = manager
        self._tick_seconds = tick_ms / 1000.0
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Begin ticking. Safe to call twice; the second call is a no-op."""
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop(), name="simulation-loop")
        logger.info("simulation loop started (tick %.0f ms)", self._tick_seconds * 1000)

    async def stop(self) -> None:
        """Cancel the loop and wait for it to unwind."""
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        logger.info("simulation loop stopped")

    async def broadcast_state(self) -> None:
        """Push the control state, so every client sees a start/pause at once."""
        message = SimulationStateMessage(
            state=SimulationStateResponse.from_domain(self._engine.state, self._engine)
        )
        await self._manager.broadcast(message.model_dump_json())

    async def _loop(self) -> None:
        previous = time.monotonic()

        while True:
            await asyncio.sleep(self._tick_seconds)

            now = time.monotonic()
            delta = now - previous
            previous = now

            try:
                self._engine.tick(delta)
            except Exception:
                # A modelling bug must not kill the loop and silently freeze
                # every client on a stale position.
                logger.exception("simulation tick failed")
                continue

            if not self._engine.state.running or self._manager.connection_count == 0:
                continue

            await self._broadcast_positions()

    async def _broadcast_positions(self) -> None:
        shuttles = []
        for shuttle in self._engine.shuttles:
            geometry = self._engine.geometry_for(shuttle.route_id)
            if geometry is None:
                continue
            shuttles.append(ShuttleResponse.from_shuttle(shuttle, geometry.route))

        message = ShuttleUpdateMessage(shuttles=shuttles)
        await self._manager.broadcast(message.model_dump_json())
