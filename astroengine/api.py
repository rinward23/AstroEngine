"""Public API dataclasses for AstroEngine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

__all__ = ["TransitEvent"]


# >>> AUTO-GEN BEGIN: API Domain Fields v1.0
@dataclass
class TransitEvent:
    # NOTE: existing fields remain; these are additive and optional
    severity: Optional[float] = None
    elements: List[str] = field(default_factory=list)        # e.g., ["FIRE"]
    domains: Dict[str, float] = field(default_factory=dict)  # normalized weights
    domain_profile: Optional[str] = None                     # e.g., "vca_neutral"
# >>> AUTO-GEN END: API Domain Fields v1.0
