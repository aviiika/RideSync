"""Geospatial engine.

Pure functions over coordinates and polylines. No I/O, no framework, no
knowledge of shuttles - which is what makes them cheap to test and safe to
reuse from the simulation engine, the ETA engine and the services alike.
"""

from app.geo.distance import (
    EARTH_RADIUS_M,
    calculate_bearing,
    cumulative_distances,
    haversine_distance,
    interpolate_coordinate,
    point_at_distance,
    route_distance,
)

__all__ = [
    "EARTH_RADIUS_M",
    "calculate_bearing",
    "cumulative_distances",
    "haversine_distance",
    "interpolate_coordinate",
    "point_at_distance",
    "route_distance",
]
