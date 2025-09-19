"""Public API dataclasses used by AstroEngine helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TransitEvent:
    """Container for a resolved transit event."""

    elements: List[str] = field(default_factory=list)
    domains: Dict[str, float] = field(default_factory=dict)
    domain_profile: Optional[str] = None
    severity: Optional[float] = None


@dataclass
class TransitScanConfig:
    """Configuration options for a transit scan."""

    ruleset_id: str = "vca_core"
    enable_declination: bool = True
    enable_mirrors: bool = True
    enable_harmonics: bool = True


__all__ = ["TransitEvent", "TransitScanConfig"]
