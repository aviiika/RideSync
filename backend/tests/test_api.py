"""API contract tests."""

from fastapi.testclient import TestClient


def test_health_reports_loaded_routes(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["routes_loaded"] >= 3


def test_list_routes_returns_geojson_geometry(client: TestClient) -> None:
    response = client.get("/routes")
    assert response.status_code == 200
    routes = response.json()
    assert routes

    first = routes[0]
    assert set(first) == {
        "id",
        "name",
        "color",
        "average_speed_kmh",
        "loop_mode",
        "geometry",
        "stops",
    }
    longitude, latitude = first["geometry"][0]
    assert 79 < longitude < 80, "geometry must be [lng, lat], not [lat, lng]"
    assert 12 < latitude < 13


def test_get_route_by_id(client: TestClient) -> None:
    known_id = client.get("/routes").json()[0]["id"]
    response = client.get(f"/routes/{known_id}")
    assert response.status_code == 200
    assert response.json()["id"] == known_id


def test_unknown_route_returns_404(client: TestClient) -> None:
    assert client.get("/routes/NOPE").status_code == 404


def test_list_stops(client: TestClient) -> None:
    response = client.get("/stops")
    assert response.status_code == 200
    assert len(response.json()) >= 3


def test_stops_filtered_by_route(client: TestClient) -> None:
    route_id = client.get("/routes").json()[0]["id"]
    stops = client.get("/stops", params={"route_id": route_id}).json()
    assert stops
    assert {stop["route_id"] for stop in stops} == {route_id}


def test_stops_for_unknown_route_returns_404(client: TestClient) -> None:
    assert client.get("/stops", params={"route_id": "NOPE"}).status_code == 404
