"""Tracking connected WebSocket clients.

Deliberately small: register, drop, broadcast. A client that has gone away is
removed rather than retried, because the frontend reconnects on its own and a
server-side retry would only duplicate that.
"""

from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger("shuttle.realtime")


class Sender(Protocol):
    """The part of a WebSocket this module actually needs.

    Narrowing to this keeps the manager testable without a live socket, and
    keeps Starlette out of the broadcast path's type signature.
    """

    async def send_text(self, data: str) -> None: ...


class ConnectionManager:
    """Fan-out to every connected client."""

    def __init__(self) -> None:
        self._connections: set[Sender] = set()

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    def add(self, connection: Sender) -> None:
        self._connections.add(connection)
        logger.info("websocket connected (%d open)", len(self._connections))

    def remove(self, connection: Sender) -> None:
        self._connections.discard(connection)
        logger.info("websocket disconnected (%d open)", len(self._connections))

    async def broadcast(self, payload: str) -> None:
        """Send one frame to everyone, dropping clients that have gone away.

        Iterating a copy matters: a failing send mutates the set, and doing
        that mid-iteration would raise and abort the rest of the broadcast.
        """
        if not self._connections:
            return

        for connection in list(self._connections):
            try:
                await connection.send_text(payload)
            except Exception:  # noqa: BLE001 - any failure means the client is gone
                self.remove(connection)
