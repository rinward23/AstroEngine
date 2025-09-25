"""Refinement helpers for pinpointing transit event timestamps."""

from __future__ import annotations

import datetime as _dt
from collections.abc import Callable
from dataclasses import dataclass

from .adapter import EphemerisAdapter, EphemerisSample, RefinementError

__all__ = ["RefinementBracket", "refine_event"]


@dataclass
class RefinementBracket:
    """Bracketing information for a transit refinement search."""

    body: int
    start: _dt.datetime
    end: _dt.datetime
    start_sample: EphemerisSample
    end_sample: EphemerisSample
    start_offset: float
    end_offset: float


def refine_event(
    adapter: EphemerisAdapter,
    bracket: RefinementBracket,
    offset_fn: Callable[[EphemerisSample], float],
    *,
    max_iterations: int = 12,
    min_step_seconds: float = 30.0,
) -> tuple[_dt.datetime, EphemerisSample]:
    """Return refined timestamp and ephemeris sample inside ``bracket``."""

    start = bracket.start
    end = bracket.end
    start_offset = bracket.start_offset
    end_offset = bracket.end_offset

    if start_offset * end_offset > 0.0:
        raise RefinementError(
            "Bracket does not straddle aspect perfection; re-bracket required"
        )

    start_speed = bracket.start_sample.speed_longitude
    end_speed = bracket.end_sample.speed_longitude
    if start_speed * end_speed < 0.0:
        raise RefinementError("Retrograde loop detected inside refinement bracket")

    for _ in range(max_iterations):
        span_seconds = (end - start).total_seconds()
        if span_seconds <= min_step_seconds:
            break
        midpoint = start + _dt.timedelta(seconds=span_seconds / 2.0)
        sample = adapter.sample(bracket.body, midpoint)
        mid_offset = offset_fn(sample)

        if start_offset * mid_offset <= 0.0:
            end = midpoint
            end_offset = mid_offset
            bracket.end_sample = sample
        else:
            start = midpoint
            start_offset = mid_offset
            bracket.start_sample = sample

    final_sample: EphemerisSample
    final_time: _dt.datetime
    if abs(start_offset) <= abs(end_offset):
        final_sample = bracket.start_sample
        final_time = start
    else:
        final_sample = bracket.end_sample
        final_time = end
    return final_time, final_sample
