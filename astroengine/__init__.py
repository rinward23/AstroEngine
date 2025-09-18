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

try:  # pragma: no cover - package metadata not available during tests
    __version__ = version("astroengine")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

from .api import TransitEvent  # ENSURE-LINE
from .domains import (  # ENSURE-LINE
    DOMAINS,
    ELEMENTS,
    ZODIAC_ELEMENT_MAP,
    DomainResolution,
    DomainResolver,
)
from .engine import attach_domain_fields, build_transit_event
from .exporters import event_to_row
from .profiles import DomainScoringProfile, VCA_DOMAIN_PROFILES  # ENSURE-LINE

__all__ = [
    "__version__",
    "TransitEvent",
    "DomainResolver",
    "DomainResolution",
    "ELEMENTS",
    "DOMAINS",
    "ZODIAC_ELEMENT_MAP",
    "DomainScoringProfile",
    "VCA_DOMAIN_PROFILES",
    "build_transit_event",
    "attach_domain_fields",
    "event_to_row",
]
