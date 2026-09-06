"""Seed-data loading and validation."""

import json

import pytest

from app.data.repository import JsonRouteRepository, RouteDataError
from app.models import Coordinate, InvalidCoordinateError, LoopMode


def test_loads_every_seed_route(repository: JsonRouteRepository) -> None:
    routes = repository.list_routes()
    assert len(routes) >= 3, "the demo needs at least three routes"
    assert all(len(route.geometry) >= 2 for route in routes)
    assert all(route.stops for route in routes)


def test_route_ids_are_unique(repository: JsonRouteRepository) -> None:
    ids = [route.id for route in repository.list_routes()]
    assert len(ids) == len(set(ids))


def test_stops_are_ordered_by_sequence(repository: JsonRouteRepository) -> None:
    for route in repository.list_routes():
        sequences = [stop.sequence for stop in route.stops]
        assert sequences == sorted(sequences)


def test_stop_geometry_index_is_in_range(repository: JsonRouteRepository) -> None:
    for route in repository.list_routes():
        for stop in route.stops:
            assert 0 <= stop.geometry_index < len(route.geometry)


def test_loop_route_geometry_is_closed(repository: JsonRouteRepository) -> None:
    for route in repository.list_routes():
        if route.loop_mode is LoopMode.LOOP:
            assert route.geometry[0] == route.geometry[-1], (
                f"{route.id} loops, so its geometry must return to its first point"
            )


def test_get_route_returns_none_for_unknown_id(repository: JsonRouteRepository) -> None:
    assert repository.get_route("NOPE") is None


def test_list_stops_can_filter_by_route(repository: JsonRouteRepository) -> None:
    route = repository.list_routes()[0]
    stops = repository.list_stops(route.id)
    assert stops
    assert {stop.route_id for stop in stops} == {route.id}


def test_missing_directory_is_reported(tmp_path) -> None:
    with pytest.raises(RouteDataError, match="not found"):
        JsonRouteRepository(routes_dir=tmp_path / "absent").list_routes()


def test_empty_directory_is_reported(tmp_path) -> None:
    with pytest.raises(RouteDataError, match="no route JSON"):
        JsonRouteRepository(routes_dir=tmp_path).list_routes()


def test_out_of_range_stop_index_is_rejected(tmp_path) -> None:
    (tmp_path / "bad.json").write_text(
        json.dumps(
            {
                "id": "R",
                "geometry": [[79.0, 12.0], [79.1, 12.1]],
                "stops": [
                    {
                        "id": "S",
                        "sequence": 0,
                        "geometry_index": 9,
                        "latitude": 12.0,
                        "longitude": 79.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(RouteDataError, match="geometry_index"):
        JsonRouteRepository(routes_dir=tmp_path).list_routes()


def test_short_geometry_is_rejected(tmp_path) -> None:
    (tmp_path / "bad.json").write_text(
        json.dumps({"id": "R", "geometry": [[79.0, 12.0]], "stops": []}), encoding="utf-8"
    )
    with pytest.raises(RouteDataError, match="at least two points"):
        JsonRouteRepository(routes_dir=tmp_path).list_routes()


@pytest.mark.parametrize("latitude,longitude", [(91.0, 0.0), (-91.0, 0.0), (0.0, 181.0)])
def test_invalid_coordinates_are_rejected(latitude: float, longitude: float) -> None:
    with pytest.raises(InvalidCoordinateError):
        Coordinate(latitude=latitude, longitude=longitude)


def test_geojson_round_trip() -> None:
    point = Coordinate.from_geojson([79.1552, 12.9698])
    assert point.latitude == 12.9698
    assert point.longitude == 79.1552
    assert point.to_geojson() == [79.1552, 12.9698]


# The VIT Vellore campus, generously bounded. The service is a closed campus
# network: a route or a shuttle outside this box is a bug, not a feature.
CAMPUS_SOUTH, CAMPUS_NORTH = 12.9650, 12.9760
CAMPUS_WEST, CAMPUS_EAST = 79.1540, 79.1650


def test_every_route_stays_inside_campus(repository: JsonRouteRepository) -> None:
    for route in repository.list_routes():
        for point in route.geometry:
            assert CAMPUS_SOUTH <= point.latitude <= CAMPUS_NORTH, (
                f"{route.id} leaves campus at latitude {point.latitude}"
            )
            assert CAMPUS_WEST <= point.longitude <= CAMPUS_EAST, (
                f"{route.id} leaves campus at longitude {point.longitude}"
            )


def test_every_stop_is_inside_campus(repository: JsonRouteRepository) -> None:
    for stop in repository.list_stops():
        assert CAMPUS_SOUTH <= stop.position.latitude <= CAMPUS_NORTH
        assert CAMPUS_WEST <= stop.position.longitude <= CAMPUS_EAST


def test_the_network_serves_academic_blocks_and_both_hostel_zones(
    repository: JsonRouteRepository,
) -> None:
    """The service exists to connect hostels to classes; assert it does."""
    names = " | ".join(stop.name.lower() for stop in repository.list_stops())

    assert "men's hostel" in names
    assert "ladies hostel" in names
    for academic in (
        "main building",
        "technology tower",
        "sjt block",
        "smv block",
        "prp block",
        "mgr block",
        "anna auditorium",
        "central library",
    ):
        assert academic in names, f"no stop serves {academic}"


def test_the_hostel_blocks_the_service_exists_for_are_all_served(
    repository: JsonRouteRepository,
) -> None:
    """Named explicitly, because these are the blocks students actually live in."""
    names = " | ".join(stop.name.lower() for stop in repository.list_stops())

    for block in ("a block", "f block", "g block", "s block"):
        assert f"ladies hostel {block}" in names, f"no stop at ladies hostel {block}"

    for block in ("a", "b", "c", "d", "j", "k", "l", "m", "q"):
        assert f"men's hostel {block} block" in names, f"no stop at men's hostel {block} block"
