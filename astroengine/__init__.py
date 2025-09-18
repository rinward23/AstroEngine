"""AstroEngine package bootstrap and public surface exports."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .api import TransitEvent, TransitScanConfig
from .catalogs import (
    VCA_CENTAURS,
    VCA_CORE_BODIES,
    VCA_EXT_ASTEROIDS,
    VCA_SENSITIVE_POINTS,
    VCA_TNOS,
)
from .config import load_profile_json, profile_into_ctx
from .domains import (
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
from .profiles import DomainScoringProfile, VCA_DOMAIN_PROFILES
from .rulesets import VCA_RULESET, get_vca_aspect, vca_orb_for
from .scoring import compute_domain_factor

__all__ = [
    "__version__",
    "TransitEvent",
    "TransitScanConfig",
    "DomainResolver",
    "DomainResolution",
    "ELEMENTS",
    "DOMAINS",
    "ZODIAC_ELEMENT_MAP",
    "natal_domain_factor",
    "DomainScoringProfile",
    "VCA_DOMAIN_PROFILES",
    "compute_domain_factor",
    "load_profile_json",
    "profile_into_ctx",
    "apply_profile_if_any",
    "get_active_aspect_angles",
    "get_feature_flag",
    "maybe_attach_domain_fields",
    "VCA_RULESET",
    "get_vca_aspect",
    "vca_orb_for",
    "VCA_CORE_BODIES",
    "VCA_EXT_ASTEROIDS",
    "VCA_CENTAURS",
    "VCA_TNOS",
    "VCA_SENSITIVE_POINTS",
]

try:  # pragma: no cover - package metadata not available during tests
    __version__ = version("astroengine")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"
