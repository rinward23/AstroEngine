"""Public scoring dignity helpers backed by repository data."""

from __future__ import annotations

from ..scoring_legacy.dignity import (  # noqa: F401
    DignityRecord,
    load_dignities,
    lookup_dignities,
)

__all__ = ["DignityRecord", "load_dignities", "lookup_dignities"]
