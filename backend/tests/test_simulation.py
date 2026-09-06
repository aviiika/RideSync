"""Simulation engine.

The engine is the heart of the demo, so these tests cover the properties a
viewer would actually notice: shuttles stay on their route, they do not
teleport, they stop at stops, and the same seed produces the same run.
"""

import pytest

from app.geo import haversine_distance
from app.geo.route_geometry import BACKWARD, FORWARD
from app.models import LoopMode, ShuttleStatus
from app.simulation import SimulationConfig, SimulationEngine


@pytest.fixture
def engine(repository) -> SimulationEngine:
    return SimulationEngine(
        repository.list_routes(),
        SimulationConfig(shuttles_per_route=2, dwell_seconds=20.0, seed=42),
    )


class TestSpawning:
    def test_spawns_shuttles_on_every_route(self, engine: SimulationEngine, repository) -> None:
        assert len(engine.shuttles) == len(repository.list_routes()) * 2

    def test_ids_are_unique_and_stable(self, engine: SimulationEngine) -> None:
        ids = [shuttle.id for shuttle in engine.shuttles]
        assert len(ids) == len(set(ids))
        assert all(shuttle_id.count("-") >= 1 for shuttle_id in ids)

    def test_vehicles_on_a_route_do_not_start_on_top_of_each_other(
        self, engine: SimulationEngine
    ) -> None:
        by_route: dict[str, list[float]] = {}
        for shuttle in engine.shuttles:
            by_route.setdefault(shuttle.route_id, []).append(shuttle.distance_m)

        for distances in by_route.values():
            assert len(set(distances)) == len(distances)

    def test_starts_paused(self, engine: SimulationEngine) -> None:
        assert engine.state.running is False


class TestMovement:
    def test_paused_shuttles_do_not_move(self, engine: SimulationEngine) -> None:
        before = [shuttle.distance_m for shuttle in engine.shuttles]
        engine.tick(10.0)
        assert [shuttle.distance_m for shuttle in engine.shuttles] == before

    def test_running_shuttles_advance(self, engine: SimulationEngine) -> None:
        engine.start()
        before = {shuttle.id: shuttle.distance_m for shuttle in engine.shuttles}
        engine.tick(5.0)
        moved = [s for s in engine.shuttles if s.distance_m != before[s.id]]
        assert moved, "no shuttle moved after a tick"

    def test_shuttles_never_leave_their_route(self, engine: SimulationEngine) -> None:
        """The anti-teleport guarantee, checked position by position."""
        engine.start()
        for _ in range(400):
            engine.tick(1.0)
            for shuttle in engine.shuttles:
                geometry = engine.geometry_for(shuttle.route_id)
                assert geometry is not None
                expected, _, _ = geometry.locate(shuttle.distance_m)
                assert haversine_distance(shuttle.position, expected) < 1.0

    def test_steps_are_small_enough_to_animate(self, engine: SimulationEngine) -> None:
        """No jump between consecutive ticks may look like a teleport."""
        engine.start()
        previous = {shuttle.id: shuttle.position for shuttle in engine.shuttles}

        for _ in range(120):
            engine.tick(1.0)
            for shuttle in engine.shuttles:
                jump = haversine_distance(previous[shuttle.id], shuttle.position)
                # 32 km/h for one second is under 9 m; allow generous headroom
                # but far less than the distance between stops.
                assert jump < 60.0, f"{shuttle.id} jumped {jump:.0f} m in one tick"
                previous[shuttle.id] = shuttle.position

    def test_progress_stays_bounded(self, engine: SimulationEngine) -> None:
        engine.start()
        for _ in range(300):
            engine.tick(2.0)
            for shuttle in engine.shuttles:
                assert 0.0 <= shuttle.progress <= 1.0

    def test_heading_stays_in_range(self, engine: SimulationEngine) -> None:
        engine.start()
        for _ in range(100):
            engine.tick(2.0)
            for shuttle in engine.shuttles:
                assert 0.0 <= shuttle.heading < 360.0


class TestStopsAndDwell:
    def test_shuttles_wait_at_stops(self, engine: SimulationEngine) -> None:
        engine.start()
        saw_dwell = False
        for _ in range(600):
            engine.tick(1.0)
            if any(s.status is ShuttleStatus.AT_STOP for s in engine.shuttles):
                saw_dwell = True
                break
        assert saw_dwell, "no shuttle ever stopped at a stop"

    def test_a_dwelling_shuttle_reports_zero_speed(self, engine: SimulationEngine) -> None:
        engine.start()
        for _ in range(600):
            engine.tick(1.0)
            for shuttle in engine.shuttles:
                if shuttle.status is ShuttleStatus.AT_STOP:
                    assert shuttle.speed_kmh == 0.0
                    return
        pytest.fail("no shuttle dwelled within the test window")

    def test_fast_ticks_still_call_at_stops(self, repository) -> None:
        """At 5x, a naive implementation skips straight past stops."""
        engine = SimulationEngine(
            repository.list_routes(), SimulationConfig(shuttles_per_route=1, seed=7)
        )
        engine.start()
        engine.set_speed(5.0)

        stopped = 0
        for _ in range(400):
            engine.tick(1.0)
            stopped += sum(1 for s in engine.shuttles if s.status is ShuttleStatus.AT_STOP)

        assert stopped > 0


class TestRouteEnds:
    def test_looping_routes_wrap_without_reversing(self, repository) -> None:
        route = next(r for r in repository.list_routes() if r.loop_mode is LoopMode.LOOP)
        engine = SimulationEngine((route,), SimulationConfig(shuttles_per_route=1, seed=1))
        engine.start()

        for _ in range(2000):
            engine.tick(1.0)
            assert engine.shuttles[0].direction == FORWARD

    def test_reversing_routes_turn_around(self, repository) -> None:
        route = next(r for r in repository.list_routes() if r.loop_mode is LoopMode.REVERSE)
        engine = SimulationEngine((route,), SimulationConfig(shuttles_per_route=1, seed=1))
        engine.start()

        directions = set()
        for _ in range(2000):
            engine.tick(1.0)
            directions.add(engine.shuttles[0].direction)

        assert directions == {FORWARD, BACKWARD}

    def test_distance_never_leaves_the_route(self, repository) -> None:
        engine = SimulationEngine(
            repository.list_routes(), SimulationConfig(shuttles_per_route=1, seed=3)
        )
        engine.start()

        for _ in range(1500):
            engine.tick(2.0)
            for shuttle in engine.shuttles:
                geometry = engine.geometry_for(shuttle.route_id)
                assert geometry is not None
                assert -0.001 <= shuttle.distance_m <= geometry.total_distance_m + 0.001


class TestControls:
    def test_pause_freezes_and_start_resumes(self, engine: SimulationEngine) -> None:
        engine.start()
        engine.tick(5.0)

        engine.pause()
        frozen = [s.distance_m for s in engine.shuttles]
        engine.tick(60.0)
        assert [s.distance_m for s in engine.shuttles] == frozen

        engine.start()
        engine.tick(5.0)
        assert [s.distance_m for s in engine.shuttles] != frozen

    def test_reset_restores_the_starting_world(self, engine: SimulationEngine) -> None:
        start_positions = [s.distance_m for s in engine.shuttles]

        engine.start()
        for _ in range(50):
            engine.tick(1.0)
        assert [s.distance_m for s in engine.shuttles] != start_positions

        engine.reset()
        assert [s.distance_m for s in engine.shuttles] == start_positions
        assert engine.state.running is False
        assert engine.state.tick_count == 0

    def test_speed_multiplier_scales_travel(self, repository) -> None:
        def run(multiplier: float) -> float:
            engine = SimulationEngine(
                repository.list_routes(), SimulationConfig(shuttles_per_route=1, seed=5)
            )
            engine.start()
            engine.set_speed(multiplier)
            engine.tick(2.0)
            return engine.shuttles[0].distance_m

        assert run(2.0) == pytest.approx(run(1.0) * 2, rel=0.01)

    def test_invalid_speed_is_rejected(self, engine: SimulationEngine) -> None:
        with pytest.raises(ValueError, match="speed must be one of"):
            engine.set_speed(3.0)

    def test_engine_requires_routes(self) -> None:
        with pytest.raises(ValueError, match="at least one route"):
            SimulationEngine(())


class TestDeterminism:
    def test_the_same_seed_reproduces_the_same_run(self, repository) -> None:
        """A pitch has to be repeatable, so this is a product requirement."""

        def run(seed: int) -> list[tuple[str, float, float]]:
            engine = SimulationEngine(
                repository.list_routes(), SimulationConfig(shuttles_per_route=2, seed=seed)
            )
            engine.start()
            for _ in range(250):
                engine.tick(1.0)
            return [
                (s.id, round(s.distance_m, 6), round(s.heading, 6))
                for s in sorted(engine.shuttles, key=lambda s: s.id)
            ]

        assert run(42) == run(42)

    def test_different_seeds_diverge(self, repository) -> None:
        def run(seed: int) -> list[float]:
            engine = SimulationEngine(
                repository.list_routes(), SimulationConfig(shuttles_per_route=2, seed=seed)
            )
            engine.start()
            for _ in range(250):
                engine.tick(1.0)
            return [round(s.distance_m, 6) for s in sorted(engine.shuttles, key=lambda s: s.id)]

        assert run(42) != run(99)


def test_shuttles_never_leave_campus(repository) -> None:
    """Whatever the route does, no vehicle may end up off campus."""
    from tests.test_repository import (
        CAMPUS_EAST,
        CAMPUS_NORTH,
        CAMPUS_SOUTH,
        CAMPUS_WEST,
    )

    engine = SimulationEngine(
        repository.list_routes(), SimulationConfig(shuttles_per_route=3, seed=11)
    )
    engine.start()
    engine.set_speed(5.0)

    for _ in range(1200):
        engine.tick(1.0)
        for shuttle in engine.shuttles:
            assert CAMPUS_SOUTH <= shuttle.position.latitude <= CAMPUS_NORTH
            assert CAMPUS_WEST <= shuttle.position.longitude <= CAMPUS_EAST
