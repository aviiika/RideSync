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

from app.eta import EtaEngine
from app.realtime.manager import ConnectionManager
from app.schemas.shuttle import ShuttleResponse
from app.schemas.simulation import SimulationStateResponse
from app.schemas.ws import ShuttleUpdateMessage, SimulationStateMessage
from app.services.history_service import HistoryService
from app.simulation import SimulationEngine

logger = logging.getLogger("shuttle.simulation")

#: How often an ETA is written down so it can later be scored. Frequent enough
#: to build a history during a demo, sparse enough not to fill the database
#: with near-identical rows.
PREDICTION_INTERVAL_S = 15.0


class SimulationRunner:
    """Ticks the engine and pushes updates to connected clients."""

    def __init__(
        self,
        engine: SimulationEngine,
        manager: ConnectionManager,
        tick_ms: int,
        eta_engine: EtaEngine | None = None,
        history: HistoryService | None = None,
    ) -> None:
        self._engine = engine
        self._manager = manager
        self._tick_seconds = tick_ms / 1000.0
        self._eta_engine = eta_engine
        self._history = history
        self._since_prediction = 0.0
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

            if not self._engine.state.running:
                continue

            self._record_history(delta)

            if self._manager.connection_count > 0:
                await self._broadcast_positions()

    def _record_history(self, delta: float) -> None:
        """Write down arrivals, and periodically the ETAs being promised.

        Wrapped whole: history is observability, and a database problem must
        never stop the simulation or blank the map.
        """
        if self._history is None:
            return

        try:
            for event in self._engine.drain_arrivals():
                self._history.record_arrival(
                    shuttle_id=event.shuttle_id,
                    route_id=event.route_id,
                    stop_id=event.stop_id,
                    arrived_at=event.at,
                    delayed=event.delayed,
                )

            self._since_prediction += delta
            if self._eta_engine is None or self._since_prediction < PREDICTION_INTERVAL_S:
                return
            self._since_prediction = 0.0

            for shuttle in self._engine.shuttles:
                geometry = self._engine.geometry_for(shuttle.route_id)
                if geometry is None:
                    continue

                stops = geometry.route.stops
                if shuttle.next_stop_index >= len(stops):
                    continue

                stop = stops[shuttle.next_stop_index]
                estimate = self._eta_engine.estimate(shuttle, geometry, stop.id)
                if estimate is None:
                    continue

                self._history.record_prediction(
                    shuttle_id=shuttle.id,
                    route_id=shuttle.route_id,
                    stop_id=stop.id,
                    estimate=estimate,
                )
        except Exception:
            logger.exception("could not record history")

    async def _broadcast_positions(self) -> None:
        shuttles = []
        for shuttle in self._engine.shuttles:
            geometry = self._engine.geometry_for(shuttle.route_id)
            if geometry is None:
                continue
            shuttles.append(ShuttleResponse.from_shuttle(shuttle, geometry.route))

        message = ShuttleUpdateMessage(shuttles=shuttles)
        await self._manager.broadcast(message.model_dump_json())
