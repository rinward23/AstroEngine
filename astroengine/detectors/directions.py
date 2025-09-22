"""Placeholder solar arc directions detector returning an empty event list."""

from __future__ import annotations

from typing import List

from ..events import DirectionEvent

__all__ = ["solar_arc_directions"]


def solar_arc_directions(natal_iso: str, start_iso: str, end_iso: str) -> List[DirectionEvent]:
    """Return solar arc direction hits (stub implementation)."""

    return []
