"""Great-circle distance, bearing and polyline interpolation.

Distances are metres and bearings are degrees clockwise from true north, both
throughout. Every function here is pure and total: given valid coordinates it
returns a value rather than raising.
"""

from __future__ import annotations

import math

from app.models import Coordinate

#: Mean Earth radius (IUGG), in metres.
EARTH_RADIUS_M = 6_371_008.8

#: Distances below this are treated as zero, so that repeated points in route
#: geometry cannot produce a divide-by-zero or a meaningless bearing.
_EPSILON_M = 1e-9


def haversine_distance(start: Coordinate, end: Coordinate) -> float:
    """Return the great-circle distance between two points, in metres.

    The haversine formula assumes a spherical Earth. Over the few kilometres a
    campus shuttle route spans, the error against a geodesic solution is well
    under a metre - far below the precision the ETA is displayed at.
    """
    lat1 = math.radians(start.latitude)
    lat2 = math.radians(end.latitude)
    delta_lat = lat2 - lat1
    delta_lon = math.radians(end.longitude - start.longitude)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def calculate_bearing(start: Coordinate, end: Coordinate) -> float:
    """Return the initial bearing from ``start`` to ``end``.

    Degrees clockwise from true north, normalised to ``[0, 360)``. This is the
    *initial* bearing: on a sphere the bearing changes along a great circle,
    but over route-segment distances the difference is negligible.
    """
    lat1 = math.radians(start.latitude)
    lat2 = math.radians(end.latitude)
    delta_lon = math.radians(end.longitude - start.longitude)

    x = math.sin(delta_lon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)

    return math.degrees(math.atan2(x, y)) % 360.0


def interpolate_coordinate(start: Coordinate, end: Coordinate, fraction: float) -> Coordinate:
    """Return the point ``fraction`` of the way from ``start`` to ``end``.

    Linear interpolation in latitude/longitude. Over segment-length distances
    at these latitudes the divergence from a great-circle path is far smaller
    than a map pixel, and it keeps marker movement perfectly smooth.

    ``fraction`` is clamped to ``[0, 1]`` so a caller that overshoots a segment
    lands exactly on its end point instead of past it.
    """
    t = min(1.0, max(0.0, fraction))
    return Coordinate(
        latitude=start.latitude + (end.latitude - start.latitude) * t,
        longitude=start.longitude + (end.longitude - start.longitude) * t,
    )


def cumulative_distances(geometry: tuple[Coordinate, ...]) -> tuple[float, ...]:
    """Return the distance from the first point to each point of a polyline.

    The result is one longer than the number of segments: element ``i`` is the
    distance travelled to reach ``geometry[i]``, so the last element is the
    total route length. Computing this once per route turns "how far along is
    this shuttle" into arithmetic rather than a walk of the geometry.
    """
    totals = [0.0]
    for previous, current in zip(geometry, geometry[1:], strict=False):
        totals.append(totals[-1] + haversine_distance(previous, current))
    return tuple(totals)


def route_distance(geometry: tuple[Coordinate, ...]) -> float:
    """Return the total length of a polyline, in metres."""
    if len(geometry) < 2:
        return 0.0
    return cumulative_distances(geometry)[-1]


def point_at_distance(
    geometry: tuple[Coordinate, ...],
    cumulative: tuple[float, ...],
    distance_m: float,
) -> tuple[Coordinate, int, float]:
    """Locate a point a given distance along a polyline.

    Returns the interpolated coordinate, the index of the segment it falls in,
    and the bearing along that segment. ``distance_m`` is clamped to the
    polyline, so callers get the terminal point rather than an error when they
    run past the end.
    """
    if len(geometry) < 2:
        return geometry[0], 0, 0.0

    total = cumulative[-1]
    target = min(max(0.0, distance_m), total)

    # Find the segment containing the target distance. Routes have tens of
    # points, so a linear scan is faster in practice than a bisect and easier
    # to read.
    segment = 0
    for index in range(len(cumulative) - 1):
        if cumulative[index + 1] >= target:
            segment = index
            break
    else:
        segment = len(geometry) - 2

    start = geometry[segment]
    end = geometry[segment + 1]
    segment_length = cumulative[segment + 1] - cumulative[segment]

    if segment_length <= _EPSILON_M:
        return start, segment, calculate_bearing(start, end)

    fraction = (target - cumulative[segment]) / segment_length
    return (
        interpolate_coordinate(start, end, fraction),
        segment,
        calculate_bearing(start, end),
    )
