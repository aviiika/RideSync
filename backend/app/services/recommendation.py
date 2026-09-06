"""Should I wait?

A deterministic demo policy, not a model. It lives in its own service so the UI
consumes a recommendation object rather than re-deriving thresholds in JSX -
and so the policy can be tuned in one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RecommendationLevel(StrEnum):
    ARRIVING_SOON = "ARRIVING_SOON"
    WORTH_WAITING = "WORTH_WAITING"
    CONSIDER_WAITING = "CONSIDER_WAITING"
    LONG_WAIT = "LONG_WAIT"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class Recommendation:
    """The answer to "should I wait for this one?", with a reason."""

    level: RecommendationLevel
    label: str
    detail: str


# Upper bound in minutes for each level, most urgent first.
_THRESHOLDS: tuple[tuple[float, RecommendationLevel, str, str], ...] = (
    (3, RecommendationLevel.ARRIVING_SOON, "Arriving soon", "Head to the stop now."),
    (7, RecommendationLevel.WORTH_WAITING, "Worth waiting", "A short wait at the stop."),
    (
        12,
        RecommendationLevel.CONSIDER_WAITING,
        "Consider waiting",
        "Walking may be quicker over short distances.",
    ),
)

_LONG_WAIT = Recommendation(
    level=RecommendationLevel.LONG_WAIT,
    label="Long wait",
    detail="Consider another route or walking.",
)

_UNAVAILABLE = Recommendation(
    level=RecommendationLevel.UNAVAILABLE,
    label="ETA unavailable",
    detail="No reliable estimate for this shuttle right now.",
)


def recommend(eta_minutes: float | None) -> Recommendation:
    """Turn an ETA into advice. ``None`` yields an honest "unavailable"."""
    if eta_minutes is None:
        return _UNAVAILABLE

    for upper, level, label, detail in _THRESHOLDS:
        if eta_minutes <= upper:
            return Recommendation(level=level, label=label, detail=detail)

    return _LONG_WAIT
