"""Measured performance of the ETA engine."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.services.history_service import EtaAccuracy


class EtaAccuracyResponse(BaseModel):
    """How far the ETA engine has been off, measured against real arrivals.

    "Real" means real within the simulation. This is a measurement of the
    estimator against the world it estimates, not a claim about buses.
    """

    resolved_predictions: int
    pending_predictions: int
    recorded_arrivals: int
    mean_absolute_error_seconds: float | None
    mean_absolute_error_minutes: float | None
    median_absolute_error_seconds: float | None
    bias_seconds: float | None = Field(
        default=None, description="Signed mean error. Positive means the ETA ran long."
    )
    measured_against: str = Field(
        default="simulated arrivals",
        description="What the error was measured against. Never real-world GPS.",
    )

    @classmethod
    def from_domain(cls, accuracy: EtaAccuracy) -> EtaAccuracyResponse:
        return cls(
            resolved_predictions=accuracy.resolved,
            pending_predictions=accuracy.pending,
            recorded_arrivals=accuracy.arrivals,
            mean_absolute_error_seconds=accuracy.mean_absolute_error_seconds,
            mean_absolute_error_minutes=accuracy.mean_absolute_error_minutes,
            median_absolute_error_seconds=accuracy.median_absolute_error_seconds,
            bias_seconds=accuracy.bias_seconds,
        )
