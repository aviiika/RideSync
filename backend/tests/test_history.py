"""Trip history and measured ETA error."""

from datetime import UTC, datetime, timedelta

import pytest

from app.db import Database
from app.eta import EtaEstimate
from app.eta.engine import EtaFeatures
from app.services.history_service import STALE_PREDICTION_SECONDS, HistoryService


def make_estimate(seconds: float) -> EtaEstimate:
    return EtaEstimate(
        seconds=seconds,
        distance_m=seconds * 5,
        features=EtaFeatures(
            remaining_distance_m=seconds * 5,
            effective_speed_kmh=18.0,
            intervening_stops=1,
            dwell_seconds=20.0,
        ),
    )


@pytest.fixture
def history(database: Database) -> HistoryService:
    return HistoryService(database)


class TestRecording:
    def test_an_arrival_with_no_prediction_resolves_nothing(self, history: HistoryService) -> None:
        resolved = history.record_arrival(
            shuttle_id="A-01",
            route_id="ROUTE-A",
            stop_id="STOP-A1",
            arrived_at=datetime.now(UTC),
        )

        assert resolved == 0
        assert history.accuracy().arrivals == 1

    def test_an_arrival_resolves_a_matching_prediction(self, history: HistoryService) -> None:
        history.record_prediction(
            shuttle_id="A-01",
            route_id="ROUTE-A",
            stop_id="STOP-A1",
            estimate=make_estimate(120),
        )

        resolved = history.record_arrival(
            shuttle_id="A-01",
            route_id="ROUTE-A",
            stop_id="STOP-A1",
            arrived_at=datetime.now(UTC) + timedelta(seconds=100),
        )

        assert resolved == 1

    def test_an_arrival_does_not_resolve_another_shuttle(self, history: HistoryService) -> None:
        history.record_prediction(
            shuttle_id="A-01",
            route_id="ROUTE-A",
            stop_id="STOP-A1",
            estimate=make_estimate(120),
        )

        resolved = history.record_arrival(
            shuttle_id="B-01",
            route_id="ROUTE-B",
            stop_id="STOP-A1",
            arrived_at=datetime.now(UTC) + timedelta(seconds=100),
        )

        assert resolved == 0

    def test_an_arrival_does_not_resolve_another_stop(self, history: HistoryService) -> None:
        history.record_prediction(
            shuttle_id="A-01",
            route_id="ROUTE-A",
            stop_id="STOP-A1",
            estimate=make_estimate(120),
        )

        resolved = history.record_arrival(
            shuttle_id="A-01",
            route_id="ROUTE-A",
            stop_id="STOP-A9",
            arrived_at=datetime.now(UTC) + timedelta(seconds=100),
        )

        assert resolved == 0

    def test_a_stale_prediction_is_abandoned_not_scored(self, history: HistoryService) -> None:
        """A shuttle that never turned up must not record a vast fake error."""
        history.record_prediction(
            shuttle_id="A-01",
            route_id="ROUTE-A",
            stop_id="STOP-A1",
            estimate=make_estimate(120),
        )

        resolved = history.record_arrival(
            shuttle_id="A-01",
            route_id="ROUTE-A",
            stop_id="STOP-A1",
            arrived_at=datetime.now(UTC) + timedelta(seconds=STALE_PREDICTION_SECONDS + 60),
        )

        assert resolved == 0
        assert history.accuracy().resolved == 0

    def test_a_resolved_prediction_is_not_resolved_twice(self, history: HistoryService) -> None:
        history.record_prediction(
            shuttle_id="A-01",
            route_id="ROUTE-A",
            stop_id="STOP-A1",
            estimate=make_estimate(120),
        )
        now = datetime.now(UTC)

        history.record_arrival(
            shuttle_id="A-01",
            route_id="ROUTE-A",
            stop_id="STOP-A1",
            arrived_at=now + timedelta(seconds=100),
        )
        second = history.record_arrival(
            shuttle_id="A-01",
            route_id="ROUTE-A",
            stop_id="STOP-A1",
            arrived_at=now + timedelta(seconds=200),
        )

        assert second == 0


class TestAccuracy:
    def test_reports_nothing_before_anything_happens(self, history: HistoryService) -> None:
        accuracy = history.accuracy()

        assert accuracy.resolved == 0
        assert accuracy.mean_absolute_error_seconds is None
        assert accuracy.mean_absolute_error_minutes is None

    def test_error_is_the_gap_between_promise_and_reality(self, history: HistoryService) -> None:
        history.record_prediction(
            shuttle_id="A-01",
            route_id="ROUTE-A",
            stop_id="STOP-A1",
            estimate=make_estimate(120),
        )
        history.record_arrival(
            shuttle_id="A-01",
            route_id="ROUTE-A",
            stop_id="STOP-A1",
            arrived_at=datetime.now(UTC) + timedelta(seconds=90),
        )

        accuracy = history.accuracy()
        assert accuracy.resolved == 1
        # Promised 120 s, took about 90: roughly half a minute long.
        assert accuracy.mean_absolute_error_seconds == pytest.approx(30, abs=2)
        assert accuracy.bias_seconds is not None
        assert accuracy.bias_seconds > 0

    def test_bias_is_signed_so_a_habit_is_visible(self, history: HistoryService) -> None:
        """An estimator that always runs short should say so, not average out."""
        now = datetime.now(UTC)
        for index in range(4):
            history.record_prediction(
                shuttle_id=f"A-0{index}",
                route_id="ROUTE-A",
                stop_id="STOP-A1",
                estimate=make_estimate(60),
            )
            history.record_arrival(
                shuttle_id=f"A-0{index}",
                route_id="ROUTE-A",
                stop_id="STOP-A1",
                arrived_at=now + timedelta(seconds=100),
            )

        accuracy = history.accuracy()
        assert accuracy.bias_seconds is not None
        assert accuracy.bias_seconds < 0

    def test_counts_pending_predictions_separately(self, history: HistoryService) -> None:
        history.record_prediction(
            shuttle_id="A-01",
            route_id="ROUTE-A",
            stop_id="STOP-A1",
            estimate=make_estimate(120),
        )

        accuracy = history.accuracy()
        assert accuracy.pending == 1
        assert accuracy.resolved == 0

    def test_a_broken_database_does_not_raise(self, tmp_path) -> None:
        """History is observability; it must never take the simulation down."""
        broken = HistoryService(Database(f"sqlite:///{(tmp_path / 'never-created.db').as_posix()}"))

        # Tables were never created, so every call fails internally.
        broken.record_prediction(
            shuttle_id="A", route_id="R", stop_id="S", estimate=make_estimate(60)
        )

        assert (
            broken.record_arrival(
                shuttle_id="A", route_id="R", stop_id="S", arrived_at=datetime.now(UTC)
            )
            == 0
        )
        assert broken.accuracy().resolved == 0


class TestNetworkFingerprint:
    def test_changing_a_stop_changes_the_fingerprint(self, repository) -> None:
        from dataclasses import replace

        from app.models import Coordinate
        from app.services.history_service import network_fingerprint

        routes = repository.list_routes()
        before = network_fingerprint(routes)

        first, *rest = routes
        moved_stop = replace(
            first.stops[0], position=Coordinate(latitude=12.9800, longitude=79.1700)
        )
        moved = replace(first, stops=(moved_stop, *first.stops[1:]))

        assert network_fingerprint((moved, *rest)) != before

    def test_the_same_network_gives_the_same_fingerprint(self, repository) -> None:
        from app.services.history_service import network_fingerprint

        routes = repository.list_routes()
        assert network_fingerprint(routes) == network_fingerprint(routes)

    def test_first_run_records_the_network_without_clearing(self, history: HistoryService) -> None:
        assert history.adopt_network("fingerprint-a") is False

    def test_an_unchanged_network_keeps_its_history(self, history: HistoryService) -> None:
        history.adopt_network("fingerprint-a")
        history.record_prediction(
            shuttle_id="A-01", route_id="R", stop_id="S", estimate=make_estimate(60)
        )

        assert history.adopt_network("fingerprint-a") is False
        assert history.accuracy().pending == 1

    def test_a_changed_network_discards_the_old_history(self, history: HistoryService) -> None:
        """Scoring predictions for one campus against arrivals at another is meaningless."""
        history.adopt_network("fingerprint-a")
        history.record_prediction(
            shuttle_id="A-01", route_id="R", stop_id="S", estimate=make_estimate(60)
        )
        history.record_arrival(
            shuttle_id="A-01", route_id="R", stop_id="S", arrived_at=datetime.now(UTC)
        )

        assert history.adopt_network("fingerprint-b") is True

        accuracy = history.accuracy()
        assert accuracy.arrivals == 0
        assert accuracy.pending == 0
        assert accuracy.resolved == 0
