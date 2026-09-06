"""How much to trust an estimate.

This is a **heuristic band, not a statistical interval**. There is no model
behind it and no historical error distribution to draw one from, so it is
named and worded to say exactly that: it reports the conditions that make an
estimate shakier, not a probability.

The three conditions that actually degrade a deterministic ETA are: distance
(more route left, more time for reality to diverge), intervening stops (each
one adds a dwell that is only ever an average), and a shuttle already known to
be running late.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.eta.engine import EtaEstimate
from app.models import Shuttle, ShuttleStatus

#: Beyond this much remaining route, treat the estimate as weak.
LOW_CONFIDENCE_DISTANCE_M = 2000.0
#: Within this much remaining route, and with few stops, treat it as strong.
HIGH_CONFIDENCE_DISTANCE_M = 800.0
#: Calling at this many stops or more makes dwell dominate the estimate.
LOW_CONFIDENCE_STOPS = 3


class ConfidenceLevel(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True, slots=True)
class Confidence:
    """A confidence band, with the reason it was assigned."""

    level: ConfidenceLevel
    label: str
    #: Plain-language reason, shown to the user rather than hidden in a log.
    reason: str


def assess(estimate: EtaEstimate, shuttle: Shuttle) -> Confidence:
    """Grade an estimate by the conditions that make it less reliable."""
    features = estimate.features

    if shuttle.status is ShuttleStatus.DELAYED:
        return Confidence(
            level=ConfidenceLevel.LOW,
            label="Low confidence",
            reason="This shuttle is running late, so its arrival is unpredictable.",
        )

    if (
        features.remaining_distance_m > LOW_CONFIDENCE_DISTANCE_M
        or features.intervening_stops >= LOW_CONFIDENCE_STOPS
    ):
        return Confidence(
            level=ConfidenceLevel.LOW,
            label="Low confidence",
            reason="It is still far away and calls at several stops on the way.",
        )

    if (
        features.remaining_distance_m <= HIGH_CONFIDENCE_DISTANCE_M
        and features.intervening_stops == 0
    ):
        return Confidence(
            level=ConfidenceLevel.HIGH,
            label="High confidence",
            reason="It is close and comes straight here.",
        )

    return Confidence(
        level=ConfidenceLevel.MEDIUM,
        label="Medium confidence",
        reason="A stop or two on the way could shift this by a minute.",
    )
