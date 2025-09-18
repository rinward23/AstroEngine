"""AstroEngine package bootstrap.

This lightweight package exposes convenience
helpers for loading schema definitions used by the
validation and doctor tooling.  The actual
rulesets live under :mod:`Version Consolidation` and
are left untouched to preserve the append-only
workflow preferred by operators.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

__all__ = [
    "__version__",
    "TransitEvent",
    "DomainResolver",
    "DomainResolution",
    "ELEMENTS",
    "DOMAINS",
    "ZODIAC_ELEMENT_MAP",
    "natal_domain_factor",
    "DomainScoringProfile",
    "VCA_DOMAIN_PROFILES",
    "compute_domain_factor",
]

try:  # pragma: no cover - package metadata not available during tests
    __version__ = version("astroengine")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

from .api import TransitEvent  # ENSURE-LINE
from .domains import (
    DOMAINS,
    ELEMENTS,
    ZODIAC_ELEMENT_MAP,
    DomainResolution,
    DomainResolver,
    natal_domain_factor,
)
from .profiles import DomainScoringProfile, VCA_DOMAIN_PROFILES  # ENSURE-LINE
from .scoring import compute_domain_factor  # ENSURE-LINE
