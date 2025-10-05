"""Layout helpers for transit ↔ natal heliocentric overlays."""
from __future__ import annotations

from typing import Sequence

__all__ = ["BREAKS", "scale_au"]

# Piecewise linear distance scaling to keep inner planets legible.
BREAKS: Sequence[tuple[float, float, float]] = (
    (0.0, 1.7, 220.0),
    (1.7, 5.5, 60.0),
    (5.5, 40.0, 12.0),
)


def scale_au(distance_au: float) -> float:
    """Return a pixel radius for ``distance_au`` using the piecewise profile."""

    if distance_au <= 0.0:
        return 0.0
    clamped = min(max(distance_au, 0.0), BREAKS[-1][1])
    total = 0.0
    remaining = clamped
    for start, end, factor in BREAKS:
        if remaining <= start:
            continue
        span = min(remaining, end) - start
        if span > 0:
            total += span * factor
        if remaining <= end:
            break
    return total
