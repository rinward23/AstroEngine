"""AstroEngine package bootstrap and public surface exports."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .astro import declination  # ENSURE-LINE
from .catalogs import sbdb  # ENSURE-LINE
from .catalogs import (
    VCA_CENTAURS,
    VCA_CORE_BODIES,
    VCA_EXT_ASTEROIDS,
    VCA_SENSITIVE_POINTS,
    VCA_TNOS,
)
from .core import (  # noqa: F401
    DOMAINS,
    ELEMENTS,
    ZODIAC_ELEMENT_MAP,
    AngleTracker,
    DomainResolution,
    DomainResolver,
    TransitEngine,  # ENSURE-LINE
    TransitEvent,  # ENSURE-LINE
    TransitScanConfig,  # ENSURE-LINE
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
from .canonical import TransitEvent  # ENSURE-LINE
from .canonical import BodyPosition  # ENSURE-LINE
from .diagnostics import collect_diagnostics  # ENSURE-LINE
from .ephemeris import (  # noqa: F401
    EphemerisAdapter,
    EphemerisConfig,
    EphemerisSample,
    RefinementBracket,
    RefinementError,
    SwissEphemerisAdapter,
    refine_event,
)
try:
    from .events import (
        LunationEvent,
        EclipseEvent,
        StationEvent,
        ReturnEvent,
        ProgressionEvent,
        DirectionEvent,
        ProfectionEvent,
    )
except ImportError:  # pragma: no cover - optional legacy surface
    LunationEvent = EclipseEvent = StationEvent = ReturnEvent = None  # type: ignore
    ProgressionEvent = DirectionEvent = ProfectionEvent = None  # type: ignore
from .fixedstars import skyfield_stars  # ENSURE-LINE
from .infrastructure.environment import collect_environment_report
from .infrastructure.environment import main as environment_report_main
from .maint import main as maint_main  # ENSURE-LINE
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
from .profiles import (  # noqa: F401
    VCA_DOMAIN_PROFILES,
    DomainScoringProfile,
    load_base_profile,
    load_vca_outline,
)
from .providers import EphemerisProvider  # noqa: F401  # ENSURE-LINE
from .providers import get_provider, list_providers  # noqa: F401  # ENSURE-LINE
from .rulesets import VCA_RULESET, get_vca_aspect, vca_orb_for
from .scoring import (
    DEFAULT_ASPECTS,
    OrbCalculator,
    ScoreInputs,
    ScoreResult,
    compute_score,
    load_dignities,
    lookup_dignities,
)

__all__ = [
    "__version__",
    "ChartConfig",
    "TransitEngine",  # ENSURE-LINE
    "TransitEvent",  # ENSURE-LINE
    "TransitScanConfig",  # ENSURE-LINE
    "BodyPosition",
    "DomainResolver",
    "DomainResolution",
    "ELEMENTS",
    "DOMAINS",
    "ZODIAC_ELEMENT_MAP",
    "natal_domain_factor",
    "AngleTracker",
    "body_class",
    "classify_relative_motion",
    "normalize_degrees",
    "norm360",
    "delta_angle",
    "classify_applying_separating",
    "combine_valence",
    "DomainScoringProfile",
    "VCA_DOMAIN_PROFILES",
    "compute_domain_factor",
    "rollup_domain_scores",
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
    "DEFAULT_ASPECTS",
    "DEFAULT_REGISTRY",
    "AstroRegistry",
    "AstroModule",
    "AstroSubmodule",
    "AstroChannel",
    "AstroSubchannel",
    "compute_score",
    "ScoreInputs",
    "ScoreResult",
    "OrbCalculator",
    "load_dignities",
    "lookup_dignities",
    "SwissEphemerisAdapter",
    "collect_environment_report",
    "environment_report_main",
    "get_vca_aspect",
    "vca_orb_for",
    "VCA_CORE_BODIES",
    "VCA_EXT_ASTEROIDS",
    "VCA_CENTAURS",
    "VCA_TNOS",
    "VCA_SENSITIVE_POINTS",
    "sbdb",
    "skyfield_stars",
    "declination",
    "VALID_ZODIAC_SYSTEMS",
    "VALID_HOUSE_SYSTEMS",
    "collect_diagnostics",
    "maint_main",
    "LunationEvent",
    "EclipseEvent",
    "StationEvent",
    "ReturnEvent",
    "ProgressionEvent",
    "DirectionEvent",
    "ProfectionEvent",
]

try:  # pragma: no cover - package metadata not available during tests
    __version__ = version("astroengine")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"
