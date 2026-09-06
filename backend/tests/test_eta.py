"""ETA engine and the recommendation policy."""

import pytest

from app.eta import DeterministicEtaEngine, EtaConfig
from app.geo.route_geometry import FORWARD, RouteGeometry
from app.models import Shuttle, ShuttleStatus
from app.services.recommendation import RecommendationLevel, recommend


@pytest.fixture
def geometry(repository) -> RouteGeometry:
    return RouteGeometry.build(repository.list_routes()[0])


def make_shuttle(geometry: RouteGeometry, distance_m: float, speed_kmh: float = 20.0) -> Shuttle:
    position, _, heading = geometry.locate(distance_m)
    return Shuttle(
        id="TEST-01",
        route_id=geometry.route.id,
        name="Test",
        distance_m=distance_m,
        direction=FORWARD,
        position=position,
        heading=heading,
        speed_kmh=speed_kmh,
        status=ShuttleStatus.IN_SERVICE,
        progress=geometry.progress(distance_m),
        occupancy=0.5,
    )


class TestDeterministicEta:
    def test_arithmetic_matches_distance_over_speed(self, geometry: RouteGeometry) -> None:
        engine = DeterministicEtaEngine(EtaConfig(dwell_seconds=0.0))
        stop = geometry.route.stops[1]
        shuttle = make_shuttle(geometry, 0.0, speed_kmh=20.0)

        estimate = engine.estimate(shuttle, geometry, stop.id)
        assert estimate is not None

        expected = (estimate.distance_m / 1000.0) / 20.0 * 3600.0
        assert estimate.seconds == pytest.approx(expected)

    def test_a_closer_stop_arrives_sooner(self, geometry: RouteGeometry) -> None:
        engine = DeterministicEtaEngine()
        shuttle = make_shuttle(geometry, 0.0)

        near = engine.estimate(shuttle, geometry, geometry.route.stops[1].id)
        far = engine.estimate(shuttle, geometry, geometry.route.stops[3].id)

        assert near is not None and far is not None
        assert near.seconds < far.seconds

    def test_dwell_time_is_added_for_intervening_stops(self, geometry: RouteGeometry) -> None:
        stop = geometry.route.stops[3]
        shuttle = make_shuttle(geometry, 0.0)

        without = DeterministicEtaEngine(EtaConfig(dwell_seconds=0.0)).estimate(
            shuttle, geometry, stop.id
        )
        with_dwell = DeterministicEtaEngine(EtaConfig(dwell_seconds=30.0)).estimate(
            shuttle, geometry, stop.id
        )

        assert without is not None and with_dwell is not None
        assert with_dwell.seconds > without.seconds
        assert with_dwell.features.intervening_stops >= 1

    def test_a_stopped_shuttle_falls_back_to_route_speed(self, geometry: RouteGeometry) -> None:
        """A shuttle reporting 0 km/h must not produce an ETA of hours."""
        engine = DeterministicEtaEngine()
        stopped = make_shuttle(geometry, 0.0, speed_kmh=0.0)

        estimate = engine.estimate(stopped, geometry, geometry.route.stops[2].id)
        assert estimate is not None
        assert estimate.features.effective_speed_kmh >= geometry.route.average_speed_kmh
        assert estimate.seconds < 3600

    def test_delay_factor_pads_the_estimate(self, geometry: RouteGeometry) -> None:
        shuttle = make_shuttle(geometry, 0.0)
        stop = geometry.route.stops[2].id

        base = DeterministicEtaEngine(EtaConfig(delay_factor=1.0)).estimate(shuttle, geometry, stop)
        padded = DeterministicEtaEngine(EtaConfig(delay_factor=1.5)).estimate(
            shuttle, geometry, stop
        )

        assert base is not None and padded is not None
        assert padded.seconds == pytest.approx(base.seconds * 1.5)

    def test_unknown_stop_yields_no_estimate(self, geometry: RouteGeometry) -> None:
        shuttle = make_shuttle(geometry, 0.0)
        assert DeterministicEtaEngine().estimate(shuttle, geometry, "NOPE") is None

    def test_out_of_service_yields_no_estimate(self, geometry: RouteGeometry) -> None:
        shuttle = make_shuttle(geometry, 0.0)
        shuttle.status = ShuttleStatus.OUT_OF_SERVICE
        assert DeterministicEtaEngine().estimate(shuttle, geometry, "STOP-A2") is None

    def test_stale_telemetry_yields_no_estimate(self, geometry: RouteGeometry) -> None:
        shuttle = make_shuttle(geometry, 0.0)
        shuttle.status = ShuttleStatus.STALE
        assert DeterministicEtaEngine().estimate(shuttle, geometry, "STOP-A2") is None

    def test_minutes_are_rounded_not_precise(self, geometry: RouteGeometry) -> None:
        shuttle = make_shuttle(geometry, 0.0)
        estimate = DeterministicEtaEngine().estimate(shuttle, geometry, "STOP-A2")
        assert estimate is not None
        assert isinstance(estimate.minutes, int)

    def test_an_estimate_reports_its_source(self, geometry: RouteGeometry) -> None:
        """The UI must be able to say the number is arithmetic, not a model."""
        shuttle = make_shuttle(geometry, 0.0)
        estimate = DeterministicEtaEngine().estimate(shuttle, geometry, "STOP-A2")
        assert estimate is not None
        assert estimate.source == "deterministic"

    def test_a_shuttle_that_just_passed_the_stop_gets_a_long_eta(
        self, geometry: RouteGeometry
    ) -> None:
        """Near in metres, far in minutes - the distinction the product rests on."""
        stop_distance = geometry.stop_distances[1]
        just_past = make_shuttle(geometry, stop_distance + 20.0)
        approaching = make_shuttle(geometry, stop_distance - 20.0)

        engine = DeterministicEtaEngine()
        passed_eta = engine.estimate(just_past, geometry, geometry.route.stops[1].id)
        approaching_eta = engine.estimate(approaching, geometry, geometry.route.stops[1].id)

        assert passed_eta is not None and approaching_eta is not None
        assert passed_eta.seconds > approaching_eta.seconds * 10


class TestRecommendation:
    @pytest.mark.parametrize(
        "minutes,expected",
        [
            (0, RecommendationLevel.ARRIVING_SOON),
            (3, RecommendationLevel.ARRIVING_SOON),
            (4, RecommendationLevel.WORTH_WAITING),
            (7, RecommendationLevel.WORTH_WAITING),
            (8, RecommendationLevel.CONSIDER_WAITING),
            (12, RecommendationLevel.CONSIDER_WAITING),
            (13, RecommendationLevel.LONG_WAIT),
            (60, RecommendationLevel.LONG_WAIT),
        ],
    )
    def test_thresholds(self, minutes: int, expected: RecommendationLevel) -> None:
        assert recommend(minutes).level is expected

    def test_missing_eta_is_reported_honestly(self) -> None:
        result = recommend(None)
        assert result.level is RecommendationLevel.UNAVAILABLE
        assert "unavailable" in result.label.lower()

    def test_every_level_carries_advice(self) -> None:
        for minutes in (1, 5, 10, 30, None):
            result = recommend(minutes)
            assert result.label
            assert result.detail
