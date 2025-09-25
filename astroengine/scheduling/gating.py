
"""Resolution-aware body gating utilities used by the scan orchestrator."""


from __future__ import annotations

from datetime import timedelta
from typing import Iterable, List


from ..core.bodies import body_priority, canonical_name, step_multiplier

# Base cadence per resolution before body-specific multipliers are applied.

_BASE_STEP = {
    "minute": timedelta(seconds=15),
    "hour": timedelta(minutes=2),
    "day": timedelta(hours=2),
    "month": timedelta(hours=8),
    "year": timedelta(days=2),
    "long": timedelta(days=10),
}



def base_step(resolution: str) -> timedelta:
    """Return the base cadence for ``resolution`` (defaults to daily sweep)."""


    return _BASE_STEP.get(resolution, timedelta(hours=2))


def choose_step(resolution: str, body: str) -> timedelta:
    """Return the gated timestep for ``body`` at the given ``resolution``."""

    step = base_step(resolution)
    multiplier = step_multiplier(body)
    return timedelta(seconds=step.total_seconds() * multiplier)


def sort_bodies_for_scan(bodies: Iterable[str]) -> List[str]:
    """Return bodies ordered by scanning priority (fast movers first)."""

    canonical = {canonical_name(body) for body in bodies}
    return sorted((b for b in canonical if b), key=body_priority)


def adapt_step_near_bracket(step: timedelta) -> timedelta:
    """Tighten the step locally once a bracket has been detected."""

    if step.total_seconds() <= 0:
        return step
    return timedelta(seconds=step.total_seconds() / 2.5)


__all__ = [
    "adapt_step_near_bracket",
    "base_step",
    "body_priority",
    "choose_step",
    "sort_bodies_for_scan",
]

