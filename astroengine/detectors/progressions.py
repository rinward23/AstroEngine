"""Placeholder progressions detector returning an empty event list."""

from __future__ import annotations

from typing import List

from ..events import ProgressionEvent

__all__ = ["secondary_progressions"]


def secondary_progressions(natal_iso: str, start_iso: str, end_iso: str) -> List[ProgressionEvent]:
    """Return secondary progression hits (stub implementation)."""

    return []
