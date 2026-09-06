"""Stop departure boards, delay injection, the walking model and confidence."""

import pytest
from fastapi.testclient import TestClient

from app.eta import DeterministicEtaEngine, EtaConfig
from app.eta.confidence import ConfidenceLevel, assess
from app.geo.route_geometry import RouteGeometry
from app.models import ShuttleStatus
from app.services.recommendation import RecommendationLevel, recommend
from app.simulation import SimulationConfig, SimulationEngine
from tests.test_eta import make_shuttle

RIDER = {"latitude": 12.9692, "longitude": 79.1554}


class TestStopBoard:
    def test_lists_what_is_due_soonest_first(self, client: TestClient) -> None:
        stop = client.get("/stops").json()[0]
        response = client.get(f"/stops/{stop['id']}/arrivals")

        assert response.status_code == 200
        board = response.json()
        assert board, "a served stop should have something due"

        etas = [item["eta"]["seconds"] for item in board if item["eta"]]
        assert etas == sorted(etas)

    def test_only_shuttles_that_call_here_appear(self, client: TestClient) -> None:
        """Proximity is irrelevant: a shuttle on another route can never arrive."""
        stop = client.get("/stops").json()[0]
        board = client.get(f"/stops/{stop['id']}/arrivals").json()

        assert {item["shuttle"]["route_id"] for item in board} == {stop["route_id"]}

    def test_every_entry_is_estimated_for_this_stop(self, client: TestClient) -> None:
        stop = client.get("/stops").json()[0]
        board = client.get(f"/stops/{stop['id']}/arrivals").json()

        assert {item["target_stop_id"] for item in board} == {stop["id"]}

    def test_distances_are_measured_from_the_rider_when_given(self, client: TestClient) -> None:
        stop = client.get("/stops").json()[0]

        from_stop = client.get(f"/stops/{stop['id']}/arrivals").json()
        from_rider = client.get(f"/stops/{stop['id']}/arrivals", params=RIDER).json()

        assert [item["shuttle"]["id"] for item in from_stop] == [
            item["shuttle"]["id"] for item in from_rider
        ]
        assert from_rider[0]["walk_seconds"] is not None

    def test_unknown_stop_returns_404(self, client: TestClient) -> None:
        assert client.get("/stops/NOPE/arrivals").status_code == 404

    def test_invalid_rider_coordinates_are_rejected(self, client: TestClient) -> None:
        stop = client.get("/stops").json()[0]
        response = client.get(
            f"/stops/{stop['id']}/arrivals",
            params={"latitude": 999, "longitude": 0},
        )
        assert response.status_code == 422


class TestDelayInjection:
    def test_a_delayed_shuttle_reports_as_delayed(self, client: TestClient) -> None:
        shuttle_id = client.get("/shuttles").json()[0]["id"]
        response = client.post("/simulation/delay", json={"shuttle_id": shuttle_id, "seconds": 120})

        assert response.status_code == 200
        assert response.json()["status"] == "DELAYED"

    def test_delays_can_be_cleared(self, client: TestClient) -> None:
        shuttle_id = client.get("/shuttles").json()[0]["id"]
        client.post("/simulation/delay", json={"shuttle_id": shuttle_id, "seconds": 120})

        assert client.post("/simulation/clear-delays").status_code == 200
        statuses = {s["id"]: s["status"] for s in client.get("/shuttles").json()}
        assert statuses[shuttle_id] != "DELAYED"

    def test_unknown_shuttle_returns_404(self, client: TestClient) -> None:
        response = client.post("/simulation/delay", json={"shuttle_id": "NOPE", "seconds": 60})
        assert response.status_code == 404

    def test_a_non_positive_delay_is_rejected(self, client: TestClient) -> None:
        shuttle_id = client.get("/shuttles").json()[0]["id"]
        response = client.post("/simulation/delay", json={"shuttle_id": shuttle_id, "seconds": 0})
        assert response.status_code == 422

    def test_a_delayed_shuttle_actually_travels_slower(self, repository) -> None:
        def distance_after(delay: bool) -> float:
            engine = SimulationEngine(
                repository.list_routes(), SimulationConfig(shuttles_per_route=1, seed=5)
            )
            engine.start()
            shuttle_id = engine.shuttles[0].id
            if delay:
                engine.delay_shuttle(shuttle_id, 600)
            for _ in range(20):
                engine.tick(1.0)
            shuttle = engine.get_shuttle(shuttle_id)
            assert shuttle is not None
            return shuttle.distance_m

        assert distance_after(delay=True) < distance_after(delay=False)

    def test_a_delayed_shuttle_recovers(self, repository) -> None:
        engine = SimulationEngine(
            repository.list_routes(), SimulationConfig(shuttles_per_route=1, seed=5)
        )
        engine.start()
        shuttle_id = engine.shuttles[0].id
        engine.delay_shuttle(shuttle_id, 10)

        for _ in range(60):
            engine.tick(1.0)

        shuttle = engine.get_shuttle(shuttle_id)
        assert shuttle is not None
        assert shuttle.status is not ShuttleStatus.DELAYED

    def test_reset_clears_a_delay(self, repository) -> None:
        engine = SimulationEngine(
            repository.list_routes(), SimulationConfig(shuttles_per_route=1, seed=5)
        )
        engine.start()
        engine.delay_shuttle(engine.shuttles[0].id, 600)
        engine.reset()

        assert all(s.delay_remaining_s == 0 for s in engine.shuttles)


class TestWalkingModel:
    def test_the_reachable_flag_is_reported(self, client: TestClient) -> None:
        first = client.get("/shuttles/nearby", params=RIDER).json()[0]

        assert "walk_minutes" in first
        assert first["reachable"] in (True, False)

    def test_a_shuttle_you_cannot_reach_in_time_says_so(self) -> None:
        """Telling someone to run for a bus they cannot catch is worse than silence."""
        result = recommend(eta_minutes=2, walk_minutes=9)

        assert result.level is RecommendationLevel.TOO_TIGHT
        assert "won't make it" in result.label.lower()

    def test_a_comfortable_walk_keeps_the_normal_advice(self) -> None:
        assert recommend(eta_minutes=6, walk_minutes=2).level is RecommendationLevel.WORTH_WAITING

    def test_a_marginal_walk_is_allowed(self) -> None:
        """Nobody times a walk to the second, and the shuttle dwells too."""
        assert recommend(eta_minutes=5, walk_minutes=5.5).level is not (
            RecommendationLevel.TOO_TIGHT
        )

    def test_the_walk_is_ignored_when_unknown(self) -> None:
        assert recommend(eta_minutes=2, walk_minutes=None).level is (
            RecommendationLevel.ARRIVING_SOON
        )

    def test_no_eta_still_wins_over_the_walk(self) -> None:
        assert recommend(eta_minutes=None, walk_minutes=30).level is (
            RecommendationLevel.UNAVAILABLE
        )


class TestConfidence:
    @pytest.fixture
    def geometry(self, repository) -> RouteGeometry:
        return RouteGeometry.build(repository.list_routes()[0])

    def test_a_delayed_shuttle_is_never_high_confidence(self, geometry: RouteGeometry) -> None:
        shuttle = make_shuttle(geometry, 0.0)
        shuttle.status = ShuttleStatus.DELAYED

        estimate = DeterministicEtaEngine(EtaConfig()).estimate(
            shuttle, geometry, geometry.route.stops[1].id
        )
        assert estimate is not None
        assert assess(estimate, shuttle).level is ConfidenceLevel.LOW

    def test_close_and_direct_is_high_confidence(self, geometry: RouteGeometry) -> None:
        stop = geometry.route.stops[1]
        stop_distance = geometry.stop_distances[1]
        shuttle = make_shuttle(geometry, max(0.0, stop_distance - 200.0))

        estimate = DeterministicEtaEngine(EtaConfig()).estimate(shuttle, geometry, stop.id)
        assert estimate is not None
        assert assess(estimate, shuttle).level is ConfidenceLevel.HIGH

    def test_far_away_is_low_confidence(self, geometry: RouteGeometry) -> None:
        stop = geometry.route.stops[1]
        stop_distance = geometry.stop_distances[1]
        # Just past the stop, so it has to go most of the way round.
        shuttle = make_shuttle(geometry, stop_distance + 50.0)

        estimate = DeterministicEtaEngine(EtaConfig()).estimate(shuttle, geometry, stop.id)
        assert estimate is not None
        assert assess(estimate, shuttle).level is ConfidenceLevel.LOW

    def test_every_band_explains_itself(self, geometry: RouteGeometry) -> None:
        shuttle = make_shuttle(geometry, 0.0)
        estimate = DeterministicEtaEngine(EtaConfig()).estimate(
            shuttle, geometry, geometry.route.stops[2].id
        )
        assert estimate is not None

        confidence = assess(estimate, shuttle)
        assert confidence.label
        assert confidence.reason.endswith(".")

    def test_the_api_reports_confidence_with_the_estimate(self, client: TestClient) -> None:
        first = client.get("/shuttles/nearby", params=RIDER).json()[0]

        assert first["eta"] is not None
        assert first["eta"]["confidence"]["level"] in {"HIGH", "MEDIUM", "LOW"}


class TestAccuracyEndpoint:
    def test_reports_an_honest_empty_state(self, client: TestClient) -> None:
        body = client.get("/metrics/eta").json()

        assert body["resolved_predictions"] >= 0
        assert body["measured_against"] == "simulated arrivals"

    def test_never_presents_itself_as_real_world_accuracy(self, client: TestClient) -> None:
        assert "simulat" in client.get("/metrics/eta").json()["measured_against"]
