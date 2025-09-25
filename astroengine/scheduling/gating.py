
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
    """Return bodies ordered by scanning priority (fast movers first).


    The incoming iterable may contain duplicates or aliases. We preserve the first
    occurrence order within each priority tier to keep behavior intuitive for
    callers that expect luminaries to lead the sweep (matching historical
    defaults) while still deduplicating repeated symbols.
    """

    order: dict[str, int] = {}
    canonical_list: list[str] = []
    for idx, body in enumerate(bodies):
        canon = canonical_name(body)
        if not canon or canon in order:
            continue
        order[canon] = idx
        canonical_list.append(canon)

    return sorted(
        canonical_list,
        key=lambda name: (body_priority(name), order[name]),

    )


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

