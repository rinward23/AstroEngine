"""Body-aware gating helpers for scan cadence selection."""

from __future__ import annotations

from datetime import timedelta
from typing import Iterable, List

from ..core.bodies import body_class, body_priority, canonical_name, step_multiplier

__all__ = [
    "adapt_step_near_bracket",
    "base_step",
    "choose_step",
    "sort_bodies_for_scan",
]


_BASE_STEP = {
    "minute": timedelta(seconds=15),
    "hour": timedelta(minutes=2),
    "day": timedelta(hours=2),
    "month": timedelta(hours=8),
    "year": timedelta(days=2),
    "long": timedelta(days=10),
}

_CLASS_ORDER = {
    "luminary": 0,
    "personal": 1,
    "social": 2,
    "point": 3,
    "asteroid": 4,
    "centaur": 4,
    "outer": 5,
    "tno": 6,
}


def base_step(resolution: str) -> timedelta:
    """Return the baseline timestep for ``resolution``."""

    return _BASE_STEP.get(resolution, timedelta(hours=2))


def choose_step(resolution: str, body: str | None) -> timedelta:
    """Return the gated timestep for ``body`` at ``resolution``."""

    base = base_step(resolution)
    multiplier = step_multiplier(body)
    seconds = max(base.total_seconds() * multiplier, 60.0)
    return timedelta(seconds=seconds)


def sort_bodies_for_scan(bodies: Iterable[str]) -> List[str]:
    """Return ``bodies`` sorted by priority for deterministic scheduling."""

    def _sort_key(name: str) -> tuple[float, int, str]:
        priority = body_priority(name)
        cls = body_class(name)
        return (priority, _CLASS_ORDER.get(cls, 9), canonical_name(name))

    canonical = {canonical_name(name) for name in bodies if canonical_name(name)}
    return sorted(canonical, key=_sort_key)


def adapt_step_near_bracket(step: timedelta) -> timedelta:
    """Tighten the timestep near a detected bracket before refinement."""

    seconds = max(step.total_seconds() / 2.5, 30.0)
    return timedelta(seconds=seconds)
