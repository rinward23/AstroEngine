"""Placeholder eclipse detector returning an empty event list."""

from __future__ import annotations

from typing import List

from ..events import EclipseEvent

__all__ = ["find_eclipses"]


def find_eclipses(start_jd: float, end_jd: float) -> List[EclipseEvent]:
    """Return eclipse events within the requested range (stub implementation)."""

    return []
