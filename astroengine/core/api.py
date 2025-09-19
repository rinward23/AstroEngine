"""Public API dataclasses used by AstroEngine helpers."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field


@dataclass
class TransitEvent:
    """Container for a resolved transit event."""

    timestamp: _dt.datetime | None = None
    body: str | None = None
    target: str | None = None
    aspect: str | None = None
    orb: float | None = None
    motion: str | None = None
    elements: list[str] = field(default_factory=list)
    domains: dict[str, float] = field(default_factory=dict)
    domain_profile: str | None = None
    severity: float | None = None


@dataclass
class TransitScanConfig:
    """Configuration options for a transit scan."""

    ruleset_id: str = "vca_core"
    enable_declination: bool = True
    enable_mirrors: bool = True
    enable_harmonics: bool = True


__all__ = ["TransitEvent", "TransitScanConfig"]
