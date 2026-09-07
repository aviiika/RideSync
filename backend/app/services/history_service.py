"""Recording what was predicted and what actually happened.

Every failure here is swallowed and logged rather than propagated. History is
observability, not the product: a locked database file must never take down the
simulation or blank the map.
"""

from __future__ import annotations

import hashlib
import logging
import statistics
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select

from app.db.models import Arrival, Meta, Prediction
from app.db.session import Database
from app.eta import EtaEstimate
from app.models import Route

logger = logging.getLogger("shuttle.history")

#: Predictions older than this are abandoned rather than matched to an arrival.
#: A shuttle that never turned up would otherwise resolve against the next lap
#: and record an enormous, meaningless error.
STALE_PREDICTION_SECONDS = 1800.0


@dataclass(frozen=True, slots=True)
class EtaAccuracy:
    """Measured error of the ETA engine, over resolved predictions."""

    resolved: int
    pending: int
    arrivals: int
    mean_absolute_error_seconds: float | None
    median_absolute_error_seconds: float | None
    #: Signed mean. Positive means the ETA ran long on average.
    bias_seconds: float | None

    @property
    def mean_absolute_error_minutes(self) -> float | None:
        if self.mean_absolute_error_seconds is None:
            return None
        return round(self.mean_absolute_error_seconds / 60.0, 2)


class HistoryService:
    """Writes predictions and arrivals, and measures one against the other."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def record_prediction(
        self,
        *,
        shuttle_id: str,
        route_id: str,
        stop_id: str,
        estimate: EtaEstimate,
    ) -> None:
        try:
            with self._database.session() as session:
                session.add(
                    Prediction(
                        shuttle_id=shuttle_id,
                        route_id=route_id,
                        stop_id=stop_id,
                        predicted_seconds=estimate.seconds,
                        remaining_distance_m=estimate.features.remaining_distance_m,
                        effective_speed_kmh=estimate.features.effective_speed_kmh,
                        intervening_stops=estimate.features.intervening_stops,
                        source=estimate.source,
                    )
                )
        except Exception:
            logger.exception("could not record prediction for %s", shuttle_id)

    def record_arrival(
        self,
        *,
        shuttle_id: str,
        route_id: str,
        stop_id: str,
        arrived_at: datetime,
        delayed: bool = False,
    ) -> int:
        """Record an arrival and resolve the predictions it settles.

        Returns how many predictions were resolved.
        """
        try:
            with self._database.session() as session:
                session.add(
                    Arrival(
                        shuttle_id=shuttle_id,
                        route_id=route_id,
                        stop_id=stop_id,
                        arrived_at=arrived_at,
                        delayed=delayed,
                    )
                )

                open_predictions = session.scalars(
                    select(Prediction).where(
                        Prediction.shuttle_id == shuttle_id,
                        Prediction.stop_id == stop_id,
                        Prediction.resolved.is_(False),
                    )
                ).all()

                resolved = 0
                for prediction in open_predictions:
                    predicted_at = _as_utc(prediction.predicted_at)
                    actual_seconds = (arrived_at - predicted_at).total_seconds()

                    if actual_seconds < 0 or actual_seconds > STALE_PREDICTION_SECONDS:
                        # Abandon rather than record a meaningless error.
                        prediction.resolved = True
                        continue

                    prediction.resolved = True
                    prediction.actual_seconds = actual_seconds
                    prediction.error_seconds = prediction.predicted_seconds - actual_seconds
                    resolved += 1

                return resolved
        except Exception:
            logger.exception("could not record arrival for %s", shuttle_id)
            return 0

    def adopt_network(self, fingerprint: str) -> bool:
        """Discard history recorded against a different route network.

        Predictions made for stops that have since moved cannot honestly be
        scored against arrivals at the new ones - the measured error would
        describe two campuses at once. Returns whether anything was cleared.
        """
        try:
            with self._database.session() as session:
                stored = session.get(Meta, NETWORK_FINGERPRINT_KEY)

                if stored is not None and stored.value == fingerprint:
                    return False

                # History with no fingerprint predates this check, so the
                # network it describes is unknown - which is not the same as
                # matching, and must not be treated as such.
                has_history = session.query(Arrival.id).first() is not None
                cleared = stored is not None or has_history

                if cleared:
                    session.query(Prediction).delete()
                    session.query(Arrival).delete()
                    logger.warning(
                        "route network changed or is unknown - cleared trip history "
                        "recorded against the previous one"
                    )

                if stored is None:
                    session.add(Meta(key=NETWORK_FINGERPRINT_KEY, value=fingerprint))
                else:
                    stored.value = fingerprint

                return cleared
        except Exception:
            logger.exception("could not check the recorded network")
            return False

    def accuracy(self) -> EtaAccuracy:
        """Measure the ETA engine against what actually happened."""
        try:
            with self._database.session() as session:
                errors = list(
                    session.scalars(
                        select(Prediction.error_seconds).where(
                            Prediction.error_seconds.is_not(None)
                        )
                    ).all()
                )
                pending = session.scalar(
                    select(Prediction.id).where(Prediction.resolved.is_(False)).limit(1)
                )
                pending_count = (
                    len(
                        session.scalars(
                            select(Prediction.id).where(Prediction.resolved.is_(False))
                        ).all()
                    )
                    if pending is not None
                    else 0
                )
                arrivals = len(session.scalars(select(Arrival.id)).all())
        except Exception:
            logger.exception("could not read accuracy")
            return EtaAccuracy(0, 0, 0, None, None, None)

        if not errors:
            return EtaAccuracy(0, pending_count, arrivals, None, None, None)

        absolute = [abs(error) for error in errors]
        return EtaAccuracy(
            resolved=len(errors),
            pending=pending_count,
            arrivals=arrivals,
            mean_absolute_error_seconds=round(statistics.fmean(absolute), 1),
            median_absolute_error_seconds=round(statistics.median(absolute), 1),
            bias_seconds=round(statistics.fmean(errors), 1),
        )


def _as_utc(value: datetime) -> datetime:
    """SQLite hands back naive datetimes; treat them as the UTC they were."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


NETWORK_FINGERPRINT_KEY = "network_fingerprint"


def network_fingerprint(routes: Iterable[Route]) -> str:
    """A stable digest of the route network's shape.

    Changing a stop's position changes this, which is the point: it is how the
    application notices that recorded history describes a different campus.
    """
    parts: list[str] = []
    for route in sorted(routes, key=lambda route: route.id):
        parts.append(route.id)
        for stop in route.stops:
            # Five decimal places is about a metre - finer than any correction
            # anyone will make by hand.
            parts.append(f"{stop.id}:{stop.position.latitude:.5f},{stop.position.longitude:.5f}")

    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:32]
