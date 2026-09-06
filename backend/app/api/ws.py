"""Live telemetry socket.

Clients connect, immediately receive the current world so the map is never
blank while waiting for the first tick, and then receive one batched update per
tick. Inbound frames are ignored: the client is a viewer, and shuttle positions
are never taken from it.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.deps import get_connection_manager, get_simulation_engine
from app.schemas.shuttle import ShuttleResponse
from app.schemas.simulation import SimulationStateResponse
from app.schemas.ws import ShuttleUpdateMessage, SimulationStateMessage

router = APIRouter()
logger = logging.getLogger("shuttle.realtime")


@router.websocket("/ws/shuttles")
async def shuttle_socket(websocket: WebSocket) -> None:
    """Stream shuttle positions to one client until it goes away."""
    manager = get_connection_manager()
    engine = get_simulation_engine()

    await websocket.accept()
    manager.add(websocket)

    try:
        # Seed the client with the current world rather than making it wait a
        # tick, so a freshly opened map is populated immediately.
        shuttles = []
        for shuttle in engine.shuttles:
            geometry = engine.geometry_for(shuttle.route_id)
            if geometry is not None:
                shuttles.append(ShuttleResponse.from_shuttle(shuttle, geometry.route))

        await websocket.send_text(ShuttleUpdateMessage(shuttles=shuttles).model_dump_json())
        await websocket.send_text(
            SimulationStateMessage(
                state=SimulationStateResponse.from_domain(engine.state, engine)
            ).model_dump_json()
        )

        # Keep the connection open. The client sends nothing meaningful; this
        # read is how we notice it has disconnected.
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001 - never let one bad socket take down the app
        logger.exception("websocket closed unexpectedly")
    finally:
        manager.remove(websocket)
