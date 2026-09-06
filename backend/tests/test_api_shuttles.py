"""Shuttle, simulation and WebSocket endpoints."""

from fastapi.testclient import TestClient

# Main Gate, the busiest stop on the demo network.
RIDER = {"latitude": 12.9695, "longitude": 79.1559}


class TestShuttleEndpoints:
    def test_lists_every_shuttle(self, client: TestClient) -> None:
        response = client.get("/shuttles")
        assert response.status_code == 200

        shuttles = response.json()
        assert len(shuttles) >= 3, "the demo needs at least three shuttles"
        assert {"id", "route_id", "latitude", "longitude", "heading", "status"} <= set(shuttles[0])

    def test_filters_by_route(self, client: TestClient) -> None:
        route_id = client.get("/routes").json()[0]["id"]
        shuttles = client.get("/shuttles", params={"route_id": route_id}).json()
        assert shuttles
        assert {shuttle["route_id"] for shuttle in shuttles} == {route_id}

    def test_nearby_is_ranked_by_eta(self, client: TestClient) -> None:
        response = client.get("/shuttles/nearby", params=RIDER)
        assert response.status_code == 200

        etas = [item["eta"]["seconds"] for item in response.json() if item["eta"]]
        assert etas == sorted(etas), "nearby must be ordered by arrival, not by distance"

    def test_nearby_reports_distance_eta_and_advice(self, client: TestClient) -> None:
        first = client.get("/shuttles/nearby", params=RIDER).json()[0]

        assert first["direct_distance_m"] >= 0
        assert first["target_stop_name"]
        assert first["recommendation"]["label"]
        assert first["route_color"].startswith("#")

    def test_nearest_returns_a_single_shuttle(self, client: TestClient) -> None:
        response = client.get("/shuttles/nearest", params=RIDER)
        assert response.status_code == 200

        body = response.json()
        assert body["shuttle"]["id"]
        assert body["recommendation"]["level"]

    def test_nearest_matches_the_head_of_nearby(self, client: TestClient) -> None:
        nearest = client.get("/shuttles/nearest", params=RIDER).json()
        nearby = client.get("/shuttles/nearby", params=RIDER).json()
        assert nearest["shuttle"]["id"] == nearby[0]["shuttle"]["id"]

    def test_single_shuttle_by_id(self, client: TestClient) -> None:
        shuttle_id = client.get("/shuttles").json()[0]["id"]
        response = client.get(f"/shuttles/{shuttle_id}", params=RIDER)
        assert response.status_code == 200
        assert response.json()["shuttle"]["id"] == shuttle_id

    def test_unknown_shuttle_returns_404(self, client: TestClient) -> None:
        assert client.get("/shuttles/NOPE", params=RIDER).status_code == 404

    def test_unknown_route_filter_returns_404(self, client: TestClient) -> None:
        response = client.get("/shuttles/nearby", params={**RIDER, "route_id": "NOPE"})
        assert response.status_code == 404

    def test_invalid_coordinates_are_rejected(self, client: TestClient) -> None:
        response = client.get("/shuttles/nearby", params={"latitude": 99, "longitude": 0})
        assert response.status_code == 422

    def test_missing_coordinates_are_rejected(self, client: TestClient) -> None:
        assert client.get("/shuttles/nearby").status_code == 422


class TestSimulationEndpoints:
    def test_reports_initial_state(self, client: TestClient) -> None:
        state = client.get("/simulation").json()
        assert state["shuttle_count"] >= 3
        assert state["speed_multiplier"] == 1.0
        assert "seed" in state

    def test_start_and_pause(self, client: TestClient) -> None:
        assert client.post("/simulation/start").json()["running"] is True
        assert client.post("/simulation/pause").json()["running"] is False

    def test_reset_returns_to_a_paused_zeroed_clock(self, client: TestClient) -> None:
        client.post("/simulation/start")
        state = client.post("/simulation/reset").json()
        assert state["running"] is False
        assert state["tick_count"] == 0
        assert state["elapsed_seconds"] == 0.0

    def test_reset_restores_starting_positions(self, client: TestClient) -> None:
        before = {s["id"]: (s["latitude"], s["longitude"]) for s in client.get("/shuttles").json()}
        client.post("/simulation/start")
        client.post("/simulation/reset")
        after = {s["id"]: (s["latitude"], s["longitude"]) for s in client.get("/shuttles").json()}
        assert before == after

    def test_speed_can_be_changed(self, client: TestClient) -> None:
        assert (
            client.post("/simulation/speed", json={"multiplier": 5}).json()["speed_multiplier"]
            == 5.0
        )

    def test_unsupported_speed_is_rejected(self, client: TestClient) -> None:
        assert client.post("/simulation/speed", json={"multiplier": 3}).status_code == 422

    def test_malformed_speed_request_is_rejected(self, client: TestClient) -> None:
        assert client.post("/simulation/speed", json={}).status_code == 422


class TestWebSocket:
    def test_a_new_client_is_seeded_with_the_current_world(self, client: TestClient) -> None:
        """The map must never sit blank waiting for the first tick."""
        with client.websocket_connect("/ws/shuttles") as socket:
            first = socket.receive_json()

            assert first["type"] == "SHUTTLE_UPDATE"
            assert first["shuttles"], "the first frame carried no shuttles"
            assert "timestamp" in first

    def test_the_second_frame_carries_simulation_state(self, client: TestClient) -> None:
        with client.websocket_connect("/ws/shuttles") as socket:
            socket.receive_json()
            state = socket.receive_json()

            assert state["type"] == "SIMULATION_STATE"
            assert "running" in state["state"]

    def test_shuttle_frames_carry_everything_the_map_needs(self, client: TestClient) -> None:
        with client.websocket_connect("/ws/shuttles") as socket:
            shuttle = socket.receive_json()["shuttles"][0]

        assert {
            "id",
            "route_id",
            "name",
            "status",
            "latitude",
            "longitude",
            "heading",
            "speed_kmh",
            "progress",
            "next_stop_name",
            "updated_at",
        } <= set(shuttle)

    def test_coordinates_are_plausible(self, client: TestClient) -> None:
        with client.websocket_connect("/ws/shuttles") as socket:
            for shuttle in socket.receive_json()["shuttles"]:
                assert -90 <= shuttle["latitude"] <= 90
                assert -180 <= shuttle["longitude"] <= 180

    def test_disconnecting_releases_the_connection(self, client: TestClient) -> None:
        from app.api.deps import get_connection_manager

        manager = get_connection_manager()
        with client.websocket_connect("/ws/shuttles"):
            assert manager.connection_count == 1
        assert manager.connection_count == 0


def test_unknown_route_filter_on_list_returns_404(client: TestClient) -> None:
    """A typo must not be answered with a confident empty list."""
    assert client.get("/shuttles", params={"route_id": "NOPE"}).status_code == 404
