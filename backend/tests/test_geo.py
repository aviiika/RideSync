"""Geospatial engine.

These are the numbers everything else is built on, so they are checked against
known values rather than against themselves.
"""

import math

import pytest

from app.geo import (
    calculate_bearing,
    cumulative_distances,
    haversine_distance,
    interpolate_coordinate,
    point_at_distance,
    route_distance,
)
from app.geo.route_geometry import BACKWARD, FORWARD, RouteGeometry
from app.models import Coordinate, LoopMode

# One degree of latitude is about 111.2 km anywhere on Earth.
DEGREE_OF_LATITUDE_M = 111_195.0


class TestHaversine:
    def test_zero_distance_to_itself(self) -> None:
        point = Coordinate(latitude=12.9695, longitude=79.1559)
        assert haversine_distance(point, point) == 0.0

    def test_one_degree_of_latitude(self) -> None:
        start = Coordinate(latitude=0.0, longitude=0.0)
        end = Coordinate(latitude=1.0, longitude=0.0)
        assert haversine_distance(start, end) == pytest.approx(DEGREE_OF_LATITUDE_M, rel=0.001)

    def test_is_symmetric(self) -> None:
        a = Coordinate(latitude=12.9695, longitude=79.1559)
        b = Coordinate(latitude=12.9712, longitude=79.1588)
        assert haversine_distance(a, b) == pytest.approx(haversine_distance(b, a))

    def test_campus_scale_distance_is_plausible(self) -> None:
        gate = Coordinate(latitude=12.96950, longitude=79.15590)
        library = Coordinate(latitude=12.96940, longitude=79.15980)
        distance = haversine_distance(gate, library)
        assert 400 < distance < 450


class TestBearing:
    @pytest.mark.parametrize(
        "delta_lat,delta_lng,expected",
        [(1, 0, 0), (0, 1, 90), (-1, 0, 180), (0, -1, 270)],
    )
    def test_cardinal_directions(self, delta_lat: float, delta_lng: float, expected: float) -> None:
        start = Coordinate(latitude=0.0, longitude=0.0)
        end = Coordinate(latitude=float(delta_lat), longitude=float(delta_lng))
        assert calculate_bearing(start, end) == pytest.approx(expected, abs=0.5)

    def test_is_always_in_range(self) -> None:
        start = Coordinate(latitude=12.9695, longitude=79.1559)
        for degrees in range(0, 360, 15):
            end = Coordinate(
                latitude=12.9695 + 0.01 * math.cos(math.radians(degrees)),
                longitude=79.1559 + 0.01 * math.sin(math.radians(degrees)),
            )
            assert 0 <= calculate_bearing(start, end) < 360


class TestInterpolation:
    def test_endpoints(self) -> None:
        start = Coordinate(latitude=12.0, longitude=79.0)
        end = Coordinate(latitude=13.0, longitude=80.0)
        assert interpolate_coordinate(start, end, 0.0) == start
        assert interpolate_coordinate(start, end, 1.0) == end

    def test_midpoint(self) -> None:
        start = Coordinate(latitude=12.0, longitude=79.0)
        end = Coordinate(latitude=13.0, longitude=80.0)
        middle = interpolate_coordinate(start, end, 0.5)
        assert middle.latitude == pytest.approx(12.5)
        assert middle.longitude == pytest.approx(79.5)

    def test_fraction_is_clamped(self) -> None:
        start = Coordinate(latitude=12.0, longitude=79.0)
        end = Coordinate(latitude=13.0, longitude=80.0)
        assert interpolate_coordinate(start, end, 5.0) == end
        assert interpolate_coordinate(start, end, -5.0) == start


class TestRouteDistance:
    def test_cumulative_is_monotonic_and_starts_at_zero(self) -> None:
        geometry = (
            Coordinate(latitude=12.0, longitude=79.0),
            Coordinate(latitude=12.01, longitude=79.0),
            Coordinate(latitude=12.02, longitude=79.0),
        )
        totals = cumulative_distances(geometry)
        assert totals[0] == 0.0
        assert totals == tuple(sorted(totals))
        assert len(totals) == len(geometry)

    def test_total_equals_sum_of_segments(self) -> None:
        geometry = (
            Coordinate(latitude=12.0, longitude=79.0),
            Coordinate(latitude=12.01, longitude=79.0),
            Coordinate(latitude=12.02, longitude=79.01),
        )
        expected = haversine_distance(geometry[0], geometry[1]) + haversine_distance(
            geometry[1], geometry[2]
        )
        assert route_distance(geometry) == pytest.approx(expected)

    def test_single_point_route_has_no_length(self) -> None:
        assert route_distance((Coordinate(latitude=12.0, longitude=79.0),)) == 0.0


class TestPointAtDistance:
    @pytest.fixture
    def geometry(self) -> tuple[Coordinate, ...]:
        return (
            Coordinate(latitude=12.0, longitude=79.0),
            Coordinate(latitude=12.01, longitude=79.0),
            Coordinate(latitude=12.02, longitude=79.0),
        )

    def test_start_and_end(self, geometry: tuple[Coordinate, ...]) -> None:
        cumulative = cumulative_distances(geometry)

        start, _, _ = point_at_distance(geometry, cumulative, 0.0)
        assert start.latitude == pytest.approx(12.0)

        end, _, _ = point_at_distance(geometry, cumulative, cumulative[-1])
        assert end.latitude == pytest.approx(12.02)

    def test_overshoot_is_clamped_to_the_end(self, geometry: tuple[Coordinate, ...]) -> None:
        cumulative = cumulative_distances(geometry)
        point, _, _ = point_at_distance(geometry, cumulative, cumulative[-1] * 10)
        assert point.latitude == pytest.approx(12.02)

    def test_position_advances_with_distance(self, geometry: tuple[Coordinate, ...]) -> None:
        cumulative = cumulative_distances(geometry)
        latitudes = [
            point_at_distance(geometry, cumulative, cumulative[-1] * fraction)[0].latitude
            for fraction in (0.0, 0.25, 0.5, 0.75, 1.0)
        ]
        assert latitudes == sorted(latitudes)


class TestRouteGeometry:
    def test_stop_distances_match_geometry_indices(self, repository) -> None:
        for route in repository.list_routes():
            geometry = RouteGeometry.build(route)
            for stop, distance in zip(route.stops, geometry.stop_distances, strict=True):
                assert distance == pytest.approx(geometry.cumulative[stop.geometry_index])

    def test_progress_is_bounded(self, repository) -> None:
        geometry = RouteGeometry.build(repository.list_routes()[0])
        assert geometry.progress(-100) == 0.0
        assert geometry.progress(geometry.total_distance_m * 2) == 1.0
        assert 0 < geometry.progress(geometry.total_distance_m / 2) < 1

    def test_looping_route_never_travels_backwards(self, repository) -> None:
        route = next(r for r in repository.list_routes() if r.loop_mode is LoopMode.LOOP)
        geometry = RouteGeometry.build(route)
        total = geometry.total_distance_m

        # A point just behind the shuttle requires almost a full lap.
        travel = geometry.distance_to(total * 0.5, total * 0.4, FORWARD)
        assert travel == pytest.approx(total * 0.9, rel=0.01)

    def test_reversing_route_turns_around_at_the_end(self, repository) -> None:
        route = next(r for r in repository.list_routes() if r.loop_mode is LoopMode.REVERSE)
        geometry = RouteGeometry.build(route)
        total = geometry.total_distance_m

        forward = geometry.distance_to(total * 0.2, total * 0.8, FORWARD)
        assert forward == pytest.approx(total * 0.6, rel=0.01)

        # Heading the other way, the same target means running to the end first.
        backward = geometry.distance_to(total * 0.2, total * 0.8, BACKWARD)
        assert backward == pytest.approx(total * 1.0, rel=0.01)

    def test_distance_to_a_stop_just_passed_is_not_the_straight_line(self, repository) -> None:
        """The point of the whole exercise: near is not the same as soon."""
        route = next(r for r in repository.list_routes() if r.loop_mode is LoopMode.LOOP)
        geometry = RouteGeometry.build(route)
        stop_distance = geometry.stop_distances[1]

        just_past = stop_distance + 20.0
        travel = geometry.distance_to(just_past, stop_distance, FORWARD)

        assert travel > geometry.total_distance_m * 0.9

    def test_stops_between_counts_only_intervening_stops(self, repository) -> None:
        route = next(r for r in repository.list_routes() if r.loop_mode is LoopMode.LOOP)
        geometry = RouteGeometry.build(route)

        first = geometry.stop_distances[0]
        third = geometry.stop_distances[2]

        assert geometry.stops_between(first, third, FORWARD) == 1

    def test_unknown_stop_has_no_distance(self, repository) -> None:
        geometry = RouteGeometry.build(repository.list_routes()[0])
        assert geometry.stop_distance("NOPE") is None
