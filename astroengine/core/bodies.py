"""Body classification helpers for scoring and orb policies."""

from __future__ import annotations

from functools import lru_cache

__all__ = ["body_class"]

_BODY_CLASS_MAP = {
    "sun": "luminary",
    "moon": "luminary",
    "mercury": "personal",
    "venus": "personal",
    "mars": "personal",
    "jupiter": "social",
    "saturn": "social",
    "uranus": "outer",
    "neptune": "outer",
    "pluto": "outer",
    "ceres": "outer",
    "pallas": "outer",
    "juno": "outer",
    "vesta": "outer",
    "chiron": "outer",
    "north_node": "outer",
    "south_node": "outer",
}


@lru_cache(maxsize=None)
def body_class(name: str) -> str:
    """Return the scoring class for the provided body name."""

    if not name:
        return "outer"
    return _BODY_CLASS_MAP.get(name.lower(), "outer")
