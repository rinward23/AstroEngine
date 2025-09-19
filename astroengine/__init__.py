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
from .chart import ChartConfig, VALID_HOUSE_SYSTEMS, VALID_ZODIAC_SYSTEMS
from .core import (
    DOMAINS,
    ELEMENTS,
    ZODIAC_ELEMENT_MAP,
    AngleTracker,
    DomainResolution,
    DomainResolver,
    TransitEngine,
    TransitEvent,
    TransitScanConfig,
    apply_profile_if_any,
    classify_relative_motion,
    compute_domain_factor,
    get_active_aspect_angles,
    get_feature_flag,
    load_profile_json,
    maybe_attach_domain_fields,
    natal_domain_factor,
    normalize_degrees,
    profile_into_ctx,
    to_tt,
)
from .ephemeris import (
    EphemerisAdapter,
    EphemerisConfig,
    EphemerisSample,
    RefinementBracket,
    RefinementError,
    refine_event,
)
from .infrastructure.environment import (
    collect_environment_report,
)
from .infrastructure.environment import (
    main as environment_report_main,
)
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
from .profiles import VCA_DOMAIN_PROFILES, DomainScoringProfile
from .rulesets import VCA_RULESET, get_vca_aspect, vca_orb_for

__all__ = [
    "__version__",
    "ChartConfig",
    "TransitEvent",
    "TransitScanConfig",
    "TransitEngine",
    "to_tt",
    "DomainResolver",
    "DomainResolution",
    "ELEMENTS",
    "DOMAINS",
    "ZODIAC_ELEMENT_MAP",
    "natal_domain_factor",
    "AngleTracker",
    "classify_relative_motion",
    "normalize_degrees",
    "DomainScoringProfile",
    "VCA_DOMAIN_PROFILES",
    "compute_domain_factor",
    "load_profile_json",
    "profile_into_ctx",
    "apply_profile_if_any",
    "EphemerisAdapter",
    "EphemerisConfig",
    "EphemerisSample",
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
    "collect_environment_report",
    "environment_report_main",
    "get_vca_aspect",
    "vca_orb_for",
    "RefinementBracket",
    "RefinementError",
    "refine_event",
    "VCA_CORE_BODIES",
    "VCA_EXT_ASTEROIDS",
    "VCA_CENTAURS",
    "VCA_TNOS",
    "VCA_SENSITIVE_POINTS",
    "VALID_ZODIAC_SYSTEMS",
    "VALID_HOUSE_SYSTEMS",
]

try:  # pragma: no cover - package metadata not available during tests
    __version__ = version("astroengine")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"
