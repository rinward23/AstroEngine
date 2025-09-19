"""Core runtime components for AstroEngine."""

from __future__ import annotations

from .api import TransitEvent, TransitScanConfig
from .config import load_profile_json, profile_into_ctx
from .domains import (
    DEFAULT_HOUSE_DOMAIN_WEIGHTS,
    DEFAULT_PLANET_DOMAIN_WEIGHTS,
    DOMAINS,
    ELEMENTS,
    ZODIAC_ELEMENT_MAP,
    DomainResolution,
    DomainResolver,
    natal_domain_factor,
)
from .engine import (
    apply_profile_if_any,
    get_active_aspect_angles,
    get_feature_flag,
    maybe_attach_domain_fields,
)
from .scoring import compute_domain_factor

__all__ = [
    "TransitEvent",
    "TransitScanConfig",
    "load_profile_json",
    "profile_into_ctx",
    "DEFAULT_PLANET_DOMAIN_WEIGHTS",
    "DEFAULT_HOUSE_DOMAIN_WEIGHTS",
    "DOMAINS",
    "ELEMENTS",
    "ZODIAC_ELEMENT_MAP",
    "DomainResolver",
    "DomainResolution",
    "natal_domain_factor",
    "apply_profile_if_any",
    "get_active_aspect_angles",
    "get_feature_flag",
    "maybe_attach_domain_fields",
    "compute_domain_factor",
]
