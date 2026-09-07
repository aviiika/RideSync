"""Persisted history.

Two tables, and the relationship between them is the whole point: every ETA the
system commits to is written down, every actual arrival is written down, and
the second resolves the first. That is what turns "the ETA looks about right"
into a number.

It is also the prerequisite for ever training a model. Until real telemetry
replaces the simulation these rows describe the simulation's own behaviour, and
`docs/architecture.md` says so plainly.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Meta(Base):
    """Small key/value facts about the database itself.

    Currently one: a fingerprint of the route network the history was recorded
    against. Predictions made for a different set of stops cannot honestly be
    scored against arrivals at this one.
    """

    __tablename__ = "meta"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(128))


class Arrival(Base):
    """A shuttle actually reached a stop."""

    __tablename__ = "arrivals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shuttle_id: Mapped[str] = mapped_column(String(64), index=True)
    route_id: Mapped[str] = mapped_column(String(64), index=True)
    stop_id: Mapped[str] = mapped_column(String(64), index=True)
    arrived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    #: Whether the shuttle was running late when it arrived.
    delayed: Mapped[bool] = mapped_column(Boolean, default=False)


class Prediction(Base):
    """An ETA the system committed to, and how it turned out.

    Rows start unresolved. When the shuttle reaches the stop, the matching
    prediction is resolved and its error recorded.
    """

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shuttle_id: Mapped[str] = mapped_column(String(64), index=True)
    route_id: Mapped[str] = mapped_column(String(64))
    stop_id: Mapped[str] = mapped_column(String(64), index=True)

    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    #: Seconds until arrival, as estimated at `predicted_at`.
    predicted_seconds: Mapped[float] = mapped_column(Float)

    # Features kept alongside, so these rows are already a training set shape.
    remaining_distance_m: Mapped[float] = mapped_column(Float)
    effective_speed_kmh: Mapped[float] = mapped_column(Float)
    intervening_stops: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(32), default="deterministic")

    resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    actual_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    #: predicted - actual, in seconds. Positive means the ETA was too long.
    error_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)


# Resolving an arrival looks up open predictions for one shuttle at one stop.
Index("ix_predictions_open", Prediction.shuttle_id, Prediction.stop_id, Prediction.resolved)
