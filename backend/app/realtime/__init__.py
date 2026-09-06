"""Real-time delivery.

The connection manager and the simulation runner. Neither knows how a shuttle
moves - they take whatever the simulation engine produces and get it to
connected clients.
"""

from app.realtime.manager import ConnectionManager
from app.realtime.runner import SimulationRunner

__all__ = ["ConnectionManager", "SimulationRunner"]
