
"""Aspect scan dataclasses for search/ranking pipelines."""


from __future__ import annotations

from dataclasses import dataclass

from datetime import datetime
from typing import Any, Mapping, MutableMapping, Optional


@dataclass(slots=True)
class Hit:
    """Raw aspect hit emitted by scanning routines.

    Attributes:
        a: Primary actor identifier (planet/body name).
        b: Secondary actor identifier.
        aspect_angle: Exact aspect angle in degrees.
        exact_time: Timestamp of the aspect hit (timezone-aware preferred).
        orb: Absolute orb distance in degrees.
        orb_limit: Maximum orb allowed for this aspect pairing.
        meta: Optional mutable mapping for downstream annotations.
    """

    a: str
    b: str
    aspect_angle: float
    exact_time: datetime
    orb: float
    orb_limit: float
    meta: Optional[MutableMapping[str, Any]] = None

    def as_mapping(self) -> Mapping[str, Any]:
        """Return a shallow mapping representation of this hit."""

        base = {
            "a": self.a,
            "b": self.b,
            "aspect_angle": self.aspect_angle,
            "exact_time": self.exact_time,
            "orb": self.orb,
            "orb_limit": self.orb_limit,
        }
        if self.meta:
            base.update(self.meta)
        return base

