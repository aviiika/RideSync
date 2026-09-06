"""Simulation engine.

Owns the authoritative position of every shuttle. It knows nothing about HTTP,
WebSockets or ETAs - it advances vehicles along route geometry and hands out
their state. That isolation is what makes it deterministic and testable, and
what lets a real GPS feed replace it later behind the same interface.
"""

from app.simulation.engine import SimulationConfig, SimulationEngine, SimulationState

__all__ = ["SimulationConfig", "SimulationEngine", "SimulationState"]
