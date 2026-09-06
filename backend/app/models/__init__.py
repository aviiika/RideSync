"""Domain models.

These are plain, framework-free dataclasses owned by the services. They are
never serialised directly onto the wire - ``app.schemas`` holds the API
contract so the two can evolve independently.
"""

from app.models.geo import Coordinate, InvalidCoordinateError
from app.models.route import LoopMode, Route, Stop
from app.models.shuttle import Shuttle, ShuttleStatus

__all__ = [
    "Coordinate",
    "InvalidCoordinateError",
    "LoopMode",
    "Route",
    "Shuttle",
    "ShuttleStatus",
    "Stop",
]
