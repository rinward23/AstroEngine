"""AstroEngine package bootstrap and public surface exports."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .catalogs import (
    VCA_CENTAURS,
    VCA_CORE_BODIES,
    VCA_EXT_ASTEROIDS,
    VCA_SENSITIVE_POINTS,
    VCA_TNOS,
)
from .chart import (
    AspectHit,
    ChartLocation,
    NatalChart,
    TransitContact,
    TransitScanner,
    compute_natal_chart,
)
from .core import (
    DOMAINS,
    ELEMENTS,
    ZODIAC_ELEMENT_MAP,
    DomainResolution,
    DomainResolver,
    TransitEvent,
    TransitScanConfig,
    apply_profile_if_any,
    compute_domain_factor,
    get_active_aspect_angles,
    get_feature_flag,
    load_profile_json,
    maybe_attach_domain_fields,
    natal_domain_factor,
    profile_into_ctx,
)
from .ephemeris import SwissEphemerisAdapter
from .infrastructure.environment import collect_environment_report
from .infrastructure.environment import main as environment_report_main
from .modules import (
    DEFAULT_REGISTRY,
    AstroChannel,
    AstroModule,
    AstroRegistry,
    AstroSubchannel,
    AstroSubmodule,
    bootstrap_default_registry,
)
from .modules.vca import serialize_vca_ruleset
from .profiles import (
    VCA_DOMAIN_PROFILES,
    DomainScoringProfile,
    load_base_profile,
    load_vca_outline,
)
from .rulesets import VCA_RULESET, get_vca_aspect, vca_orb_for
from .scoring import (
    DEFAULT_ASPECTS,
    OrbCalculator,
    load_dignities,
    lookup_dignities,
)

__all__ = [
    "__version__",
    "TransitEvent",
    "TransitScanConfig",
    "TransitContact",
    "TransitScanner",
    "AspectHit",
    "ChartLocation",
    "NatalChart",
    "compute_natal_chart",
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
    "serialize_vca_ruleset",
    "bootstrap_default_registry",
    "DEFAULT_REGISTRY",
    "AstroRegistry",
    "AstroModule",
    "AstroSubmodule",
    "AstroChannel",
    "AstroSubchannel",
    "SwissEphemerisAdapter",
    "collect_environment_report",
    "environment_report_main",
    "get_vca_aspect",
    "vca_orb_for",
    "DEFAULT_ASPECTS",
    "OrbCalculator",
    "load_dignities",
    "lookup_dignities",
    "load_base_profile",
    "load_vca_outline",
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
