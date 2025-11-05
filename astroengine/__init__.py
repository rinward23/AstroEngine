"""AstroEngine package bootstrap and curated public API surface."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from importlib import import_module
from typing import Any
import warnings

try:
    from importlib.metadata import PackageNotFoundError, version as _get_version
except ImportError:  # pragma: no cover - fallback for Python <3.8 environments
    from importlib_metadata import PackageNotFoundError, version as _get_version

LOG = logging.getLogger(__name__)

try:
    from ._version import version as __version__
except ImportError:  # pragma: no cover - setuptools-scm has not generated _version yet
    try:
        __version__ = _get_version("astroengine")
    except PackageNotFoundError:  # pragma: no cover - metadata may be unavailable in editable installs
        # When running from source without installed metadata (e.g., editable installs),
        # fall back to the neutral base version so release artefacts never expose
        # the ``0+unknown`` marker.
        __version__ = "0.0.0"


def get_version() -> str:
    """Return the resolved AstroEngine package version."""

    return __version__


__all__ = ["__version__", "get_version", "charts", "profiles", "transits"]

_PUBLIC_MODULES: dict[str, str] = {
    "charts": "charts",
    "profiles": "profiles",
    "transits": "transits",
}

_CHART_EXPORTS: tuple[str, ...] = (
    "ChartConfig",
    "ChartLocation",
    "CompositePosition",
    "DirectedChart",
    "HarmonicChart",
    "HarmonicPosition",
    "MidpointCompositeChart",
    "NatalChart",
    "ProgressedChart",
    "ReturnChart",
    "VALID_HOUSE_SYSTEMS",
    "VALID_ZODIAC_SYSTEMS",
    "compute_composite_chart",
    "compute_harmonic_chart",
    "compute_natal_chart",
    "compute_return_chart",
    "compute_secondary_progressed_chart",
    "compute_solar_arc_chart",
)

_TRANSIT_EXPORTS: tuple[str, ...] = (
    "AngleTracker",
    "EphemerisAdapter",
    "EphemerisConfig",
    "EphemerisSample",
    "ObserverLocation",
    "RefineResult",
    "RefinementError",
    "SwissEphemerisAdapter",
    "TimeScaleContext",
    "SECONDS_PER_DAY",
    "TransitEngine",
    "TransitEngineConfig",
    "TransitEvent",
    "TransitScanConfig",
    "bracket_root",
    "get_active_aspect_angles",
    "get_feature_flag",
    "maybe_attach_domain_fields",
    "refine_event",
    "refine_root",
    "to_tt",
)

_PROFILE_EXPORTS: tuple[str, ...] = (
    "DomainScoringProfile",
    "ResonanceWeights",
    "VCA_DOMAIN_PROFILES",
    "load_base_profile",
    "load_profile",
    "load_resonance_weights",
    "load_vca_outline",
)

_DEPRECATION_TEMPLATE = (
    "'astroengine.{name}' is deprecated and will be removed in a future release; "
    "import from '{target}' instead."
)

_DEPRECATED_REDIRECTS: dict[str, tuple[str, str]] = {}


def _redirect(module: str, names: tuple[str, ...]) -> None:
    for item in names:
        _DEPRECATED_REDIRECTS[item] = (module, item)


_redirect(
    "astroengine.atlas.tz",
    (
        "FoldPolicy",
        "GapPolicy",
        "LocalTimeResolution",
        "Policy",
        "from_utc",
        "is_ambiguous",
        "is_nonexistent",
        "to_utc",
        "to_utc_with_timezone",
        "tzid_for",
    ),
)
_redirect("astroengine.charts", _CHART_EXPORTS)
_redirect("astroengine.transits", _TRANSIT_EXPORTS)
_redirect(
    "astroengine.canonical",
    (
        "BodyPosition",
    ),
)
_redirect(
    "astroengine.core",
    (
        "DomainResolver",
        "DomainResolution",
        "ELEMENT_DOMAIN_BRIDGE",
        "ELEMENTS",
        "DOMAINS",
        "ZODIAC_ELEMENT_MAP",
        "apply_profile_if_any",
        "classify_relative_motion",
        "compute_domain_factor",
        "load_profile_json",
        "natal_domain_factor",
        "normalize_degrees",
        "profile_into_ctx",
    ),
)
_redirect(
    "astroengine.core.bodies",
    (
        "body_class",
    ),
)
_redirect(
    "astroengine.domains",
    (
        "rollup_domain_scores",
    ),
)
_redirect(
    "astroengine.analysis",
    (
        "condition_report",
        "score_accidental",
        "score_essential",
    ),
)
_redirect("astroengine.profiles", _PROFILE_EXPORTS)
_redirect(
    "astroengine.narrative_overlay",
    (
        "NarrativeOverlay",
        "apply_resonance_overlay",
        "format_confidence_band",
        "select_resonance_focus",
    ),
)
_redirect(
    "astroengine.modules",
    (
        "AstroRegistry",
        "AstroModule",
        "AstroSubmodule",
        "AstroChannel",
        "AstroSubchannel",
        "bootstrap_default_registry",
        "DEFAULT_REGISTRY",
    ),
)
_redirect(
    "astroengine.modules.vca",
    (
        "serialize_vca_ruleset",
    ),
)
_redirect(
    "astroengine.rulesets",
    (
        "VCA_RULESET",
        "get_vca_aspect",
        "vca_orb_for",
    ),
)
_redirect(
    "astroengine.scoring",
    (
        "DEFAULT_ASPECTS",
        "OrbCalculator",
        "OrbPolicy",
        "ScoreInputs",
        "ScoreResult",
        "SeverityPolicy",
        "VisibilityPolicy",
        "compute_score",
        "compute_uncertainty_confidence",
        "load_dignities",
        "load_orb_policy",
        "load_severity_policy",
        "load_visibility_policy",
        "lookup_dignities",
    ),
)
_redirect(
    "astroengine.utils.angles",
    (
        "classify_applying_separating",
        "delta_angle",
        "norm360",
    ),
)
_redirect(
    "astroengine.valence",
    (
        "combine_valence",
    ),
)
_redirect(
    "astroengine.providers",
    (
        "EphemerisProvider",
        "get_provider",
        "list_providers",
    ),
)
_redirect(
    "astroengine.esoteric",
    (
        "ALCHEMY_STAGES",
        "DECANS",
        "ELDER_FUTHARK_RUNES",
        "GOLDEN_DAWN_GRADES",
        "I_CHING_HEXAGRAMS",
        "MASTER_NUMBERS",
        "NUMEROLOGY_NUMBERS",
        "SEVEN_RAYS",
        "TAROT_COURTS",
        "TAROT_MAJORS",
        "TAROT_SPREADS",
        "TREE_OF_LIFE_PATHS",
        "TREE_OF_LIFE_SEPHIROTH",
        "AlchemyStage",
        "DecanAssignment",
        "DecanDefinition",
        "GoldenDawnGrade",
        "Hexagram",
        "NumerologyNumber",
        "PathDefinition",
        "RayDefinition",
        "Rune",
        "SephiraDefinition",
        "TarotCourtCard",
        "TarotMajorArcana",
        "TarotSpread",
    ),
)
_redirect(
    "astroengine.engine.vedic",
    (
        "NAKSHATRA_ARC_DEGREES",
        "PADA_ARC_DEGREES",
        "Nakshatra",
        "NakshatraPosition",
        "assign_decans",
        "decan_for_longitude",
        "lord_of_nakshatra",
        "nakshatra_info",
        "nakshatra_of",
        "pada_of",
        "position_for",
    ),
)
_redirect(
    "astroengine.catalogs",
    (
        "VCA_CENTAURS",
        "VCA_CORE_BODIES",
        "VCA_EXT_ASTEROIDS",
        "VCA_SENSITIVE_POINTS",
        "VCA_TNOS",
        "sbdb",
    ),
)
_redirect(
    "astroengine.fixedstars",
    (
        "skyfield_stars",
    ),
)
_redirect(
    "astroengine.astro",
    (
        "declination",
    ),
)
_redirect(
    "astroengine.diagnostics",
    (
        "collect_diagnostics",
    ),
)
_redirect(
    "astroengine.infrastructure.environment",
    (
        "collect_environment_report",
    ),
)
_redirect(
    "astroengine.jyotish",
    (
        "GrahaYuddhaOutcome",
        "HouseClaim",
        "HouseWinner",
        "SrishtiAspect",
        "StrengthScore",
        "compute_srishti_aspects",
        "determine_house_lords",
        "detect_graha_yuddha",
        "evaluate_house_claims",
        "evaluate_house_claims_from_chart",
        "house_occupants",
        "karakas_for_house",
        "match_karakas",
        "score_planet_strength",
    ),
)
_redirect(
    "astroengine.ritual",
    (
        "CHALDEAN_ORDER",
        "ELECTIONAL_WINDOWS",
        "PLANETARY_DAYS",
        "PLANETARY_HOUR_TABLE",
        "VOID_OF_COURSE_RULES",
        "ElectionalWindow",
        "PlanetaryDay",
        "VoidOfCourseRule",
    ),
)
_redirect(
    "astroengine.agents",
    (
        "AgentSDK",
    ),
)

_SPECIAL_REDIRECTS: dict[str, tuple[str, str]] = {
    "environment_report_main": ("astroengine.infrastructure.environment", "main"),
    "maint_main": ("astroengine.maint", "main"),
}

_OPTIONAL_REDIRECTS: dict[str, tuple[str, str]] = {
    "DirectionEvent": ("astroengine.events", "DirectionEvent"),
    "EclipseEvent": ("astroengine.events", "EclipseEvent"),
    "LunationEvent": ("astroengine.events", "LunationEvent"),
    "OutOfBoundsEvent": ("astroengine.events", "OutOfBoundsEvent"),
    "ProfectionEvent": ("astroengine.events", "ProfectionEvent"),
    "ProgressionEvent": ("astroengine.events", "ProgressionEvent"),
    "ReturnEvent": ("astroengine.events", "ReturnEvent"),
    "StationEvent": ("astroengine.events", "StationEvent"),
}


def __getattr__(name: str) -> Any:
    module_name = _PUBLIC_MODULES.get(name)
    if module_name is not None:
        module = import_module(f".{module_name}", __name__)
        globals()[name] = module
        return module
    target = _DEPRECATED_REDIRECTS.get(name)
    if target is not None:
        module_name, attr_name = target
        warnings.warn(
            _DEPRECATION_TEMPLATE.format(name=name, target=f"{module_name}.{attr_name}"),
            DeprecationWarning,
            stacklevel=2,
        )
        module = import_module(module_name)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    target = _SPECIAL_REDIRECTS.get(name)
    if target is not None:
        module_name, attr_name = target
        warnings.warn(
            _DEPRECATION_TEMPLATE.format(name=name, target=f"{module_name}.{attr_name}"),
            DeprecationWarning,
            stacklevel=2,
        )
        module = import_module(module_name)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    target = _OPTIONAL_REDIRECTS.get(name)
    if target is not None:
        module_name, attr_name = target
        warnings.warn(
            _DEPRECATION_TEMPLATE.format(name=name, target=f"{module_name}.{attr_name}"),
            DeprecationWarning,
            stacklevel=2,
        )
        try:
            module = import_module(module_name)
        except ImportError:
            value = None
        else:
            value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(name)


def __dir__() -> list[str]:
    return sorted(
        set(__all__)
        | set(_PUBLIC_MODULES)
        | set(_DEPRECATED_REDIRECTS)
        | set(_SPECIAL_REDIRECTS)
        | set(_OPTIONAL_REDIRECTS)
        | set(globals().keys())
    )


# Hypothesis 6.112+ disallows timezone-aware bounds for datetimes; provide a
# compatibility shim so property tests can continue to exercise timezone helpers.
try:  # pragma: no cover - optional dependency in some environments
    import hypothesis.strategies as _hyp_strategies

    _original_datetimes = _hyp_strategies.datetimes

    def _datetimes_utc_friendly(  # type: ignore[override]
        min_value: datetime = datetime.min,
        max_value: datetime = datetime.max,
        *,
        timezones=_hyp_strategies.none(),
        allow_imaginary: bool = True,
    ):
        tz = None
        if min_value.tzinfo is not None:
            tz = min_value.tzinfo
            min_value = min_value.astimezone(UTC).replace(tzinfo=None)
        if max_value.tzinfo is not None:
            tz = max_value.tzinfo
            max_value = max_value.astimezone(UTC).replace(tzinfo=None)
        if tz is not None and timezones is _hyp_strategies.none():
            timezones = _hyp_strategies.just(tz)
        return _original_datetimes(
            min_value=min_value,
            max_value=max_value,
            timezones=timezones,
            allow_imaginary=allow_imaginary,
        )

    _hyp_strategies.datetimes = _datetimes_utc_friendly  # type: ignore[assignment]
except Exception as exc:  # pragma: no cover
    LOG.debug("Hypothesis timezone shim unavailable: %s", exc)
