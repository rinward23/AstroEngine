"""Public API dataclasses used by the AstroEngine runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# >>> AUTO-GEN BEGIN: API Domain Fields v1.0


@dataclass
class TransitEvent:
    """Lightweight event structure enriched with optional domain metadata."""

    severity: Optional[float] = None
    elements: List[str] = field(default_factory=list)
    domains: Dict[str, float] = field(default_factory=dict)
    domain_profile: Optional[str] = None


# >>> AUTO-GEN END: API Domain Fields v1.0


__all__ = ["TransitEvent"]

