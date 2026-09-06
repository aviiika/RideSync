"""Should I wait?

A deterministic demo policy, not a model. It lives in its own service so the
UI consumes a recommendation object rather than re-deriving thresholds in JSX,
and so the policy can be tuned in one place.

The policy accounts for **how long it takes to reach the stop**. A shuttle
arriving in two minutes is no use if the stop is a five-minute walk away, and
telling someone to hurry for a bus they cannot catch is worse than telling them
nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

#: Slack allowed when deciding whether a stop is reachable in time, in minutes.
#: Nobody times a walk to the second, and being marginally late to a stop the
#: shuttle also has to dwell at is usually fine.
REACHABLE_SLACK_MINUTES = 1.0


class RecommendationLevel(StrEnum):
    ARRIVING_SOON = "ARRIVING_SOON"
    WORTH_WAITING = "WORTH_WAITING"
    CONSIDER_WAITING = "CONSIDER_WAITING"
    LONG_WAIT = "LONG_WAIT"
    TOO_TIGHT = "TOO_TIGHT"
    """It arrives before the rider can plausibly get to the stop."""
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


def recommend(eta_minutes: float | None, walk_minutes: float | None = None) -> Recommendation:
    """Turn an ETA, and the walk to the stop, into advice.

    ``None`` for the ETA yields an honest "unavailable". ``None`` for the walk
    simply skips the reachability check.
    """
    if eta_minutes is None:
        return _UNAVAILABLE

    if walk_minutes is not None and walk_minutes > eta_minutes + REACHABLE_SLACK_MINUTES:
        return Recommendation(
            level=RecommendationLevel.TOO_TIGHT,
            label="You won't make it",
            detail=(
                f"The stop is about {round(walk_minutes)} min away on foot "
                "and this one arrives before that. Wait for the next."
            ),
        )

    for upper, level, label, detail in _THRESHOLDS:
        if eta_minutes <= upper:
            return Recommendation(level=level, label=label, detail=detail)

    return _LONG_WAIT
