"""AstroEngine package bootstrap and public surface exports."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from importlib import import_module
from typing import TYPE_CHECKING, Any

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


__all__ = [
    "__version__",
    "FoldPolicy",
    "GapPolicy",
    "LocalTimeResolution",
    "Policy",
    "tzid_for",
    "to_utc",
    "to_utc_with_timezone",
    "from_utc",
    "is_ambiguous",
    "is_nonexistent",
    "ChartConfig",
    "ChartLocation",
    "NatalChart",
    "ProgressedChart",
    "ReturnChart",
    "HarmonicChart",
    "HarmonicPosition",
    "MidpointCompositeChart",
    "CompositePosition",
    "DirectedChart",
    "TransitEngine",  # ENSURE-LINE
    "TransitEngineConfig",
    "TransitEvent",  # ENSURE-LINE
    "TransitScanConfig",  # ENSURE-LINE
    "BodyPosition",
    "compute_natal_chart",
    "compute_secondary_progressed_chart",
    "compute_return_chart",
    "compute_harmonic_chart",
    "compute_composite_chart",
    "compute_solar_arc_chart",
    "DomainResolver",
    "DomainResolution",
    "ELEMENT_DOMAIN_BRIDGE",
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
    "ResonanceWeights",
    "compute_domain_factor",
    "rollup_domain_scores",
    "load_profile_json",
    "load_base_profile",
    "load_profile",
    "profile_into_ctx",
    "apply_profile_if_any",
    "load_resonance_weights",
    "load_vca_outline",
    "to_tt",
    "NarrativeOverlay",
    "apply_resonance_overlay",
    "format_confidence_band",
    "select_resonance_focus",
    "EphemerisAdapter",
    "EphemerisConfig",
    "EphemerisSample",
    "ObserverLocation",
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
    "AgentSDK",
    "compute_score",
    "ScoreInputs",
    "ScoreResult",
    "OrbCalculator",
    "compute_uncertainty_confidence",
    "condition_report",
    "load_dignities",
    "score_accidental",
    "score_essential",
    "lookup_dignities",
    "OrbPolicy",
    "SeverityPolicy",
    "VisibilityPolicy",
    "load_orb_policy",
    "load_severity_policy",
    "load_visibility_policy",
    "SwissEphemerisAdapter",
    "TimeScaleContext",
    "refine_event",
    "refine_root",
    "bracket_root",
    "RefineResult",
    "SECONDS_PER_DAY",
    "RefinementError",
    "collect_environment_report",
    "environment_report_main",
    "get_vca_aspect",
    "vca_orb_for",
    "DECANS",
    "TREE_OF_LIFE_SEPHIROTH",
    "TREE_OF_LIFE_PATHS",
    "ALCHEMY_STAGES",
    "SEVEN_RAYS",
    "GOLDEN_DAWN_GRADES",
    "TAROT_MAJORS",
    "TAROT_COURTS",
    "TAROT_SPREADS",
    "NUMEROLOGY_NUMBERS",
    "MASTER_NUMBERS",
    "I_CHING_HEXAGRAMS",
    "ELDER_FUTHARK_RUNES",
    "PLANETARY_DAYS",
    "PLANETARY_HOUR_TABLE",
    "VOID_OF_COURSE_RULES",
    "ELECTIONAL_WINDOWS",
    "CHALDEAN_ORDER",
    "DecanAssignment",
    "DecanDefinition",
    "SephiraDefinition",
    "PathDefinition",
    "AlchemyStage",
    "RayDefinition",
    "GoldenDawnGrade",
    "TarotMajorArcana",
    "TarotCourtCard",
    "TarotSpread",
    "NumerologyNumber",
    "Hexagram",
    "Rune",
    "PlanetaryDay",
    "VoidOfCourseRule",
    "ElectionalWindow",
    "NAKSHATRA_ARC_DEGREES",
    "PADA_ARC_DEGREES",
    "Nakshatra",
    "NakshatraPosition",
    "nakshatra_info",
    "nakshatra_of",
    "lord_of_nakshatra",
    "pada_of",
    "position_for",
    "assign_decans",
    "decan_for_longitude",
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
    "OutOfBoundsEvent",
    "determine_house_lords",
    "house_occupants",
    "karakas_for_house",
    "match_karakas",
    "StrengthScore",
    "score_planet_strength",
    "SrishtiAspect",
    "GrahaYuddhaOutcome",
    "compute_srishti_aspects",
    "detect_graha_yuddha",
    "HouseClaim",
    "HouseWinner",
    "evaluate_house_claims",
    "evaluate_house_claims_from_chart",
]


if TYPE_CHECKING:
    from .agents import AgentSDK
    from .analysis import condition_report, score_accidental, score_essential
    from .atlas.tz import (
        FoldPolicy,
        GapPolicy,
        LocalTimeResolution,
        Policy,
        from_utc,
        is_ambiguous,
        is_nonexistent,
        to_utc,
        to_utc_with_timezone,
        tzid_for,
    )
    from .astro import declination
    from .canonical import BodyPosition
    from .catalogs import (
        VCA_CENTAURS,
        VCA_CORE_BODIES,
        VCA_EXT_ASTEROIDS,
        VCA_SENSITIVE_POINTS,
        VCA_TNOS,
        sbdb,
    )
    from .chart import (
        ChartLocation,
        CompositePosition,
        DirectedChart,
        HarmonicChart,
        HarmonicPosition,
        MidpointCompositeChart,
        NatalChart,
        ProgressedChart,
        ReturnChart,
        compute_composite_chart,
        compute_harmonic_chart,
        compute_natal_chart,
        compute_return_chart,
        compute_secondary_progressed_chart,
        compute_solar_arc_chart,
    )
    from .chart.config import ChartConfig, VALID_HOUSE_SYSTEMS, VALID_ZODIAC_SYSTEMS
    from .core import (
        AngleTracker,
        DOMAINS,
        ELEMENT_DOMAIN_BRIDGE,
        ELEMENTS,
        DomainResolution,
        DomainResolver,
        TransitEngine,
        TransitEngineConfig,
        TransitEvent,
        TransitScanConfig,
        ZODIAC_ELEMENT_MAP,
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
    from .core.bodies import body_class
    from .diagnostics import collect_diagnostics
    from .domains import rollup_domain_scores
    from .engine.vedic import (
        CharaKaraka,
        EclipseAlignment,
        IshtaKashtaResult,
        KarakamshaLagna,
        KarmaSegment,
        KarmicProfile,
        Nakshatra,
        NakshatraPosition,
        NAKSHATRA_ARC_DEGREES,
        PADA_ARC_DEGREES,
        assign_decans,
        build_karmic_profile,
        compute_chara_karakas,
        decan_for_longitude,
        eclipse_alignment_roles,
        ishta_kashta_phala,
        karakamsha_lagna,
        karma_attributions,
        lord_of_nakshatra,
        nakshatra_info,
        nakshatra_of,
        pada_of,
        position_for,
    )
    from .ephemeris import (
        EphemerisAdapter,
        EphemerisConfig,
        EphemerisSample,
        ObserverLocation,
        RefineResult,
        RefinementError,
        SwissEphemerisAdapter,
        TimeScaleContext,
        SECONDS_PER_DAY,
        bracket_root,
        refine_event,
        refine_root,
    )
    from .esoteric import (
        ALCHEMY_STAGES,
        DECANS,
        ELDER_FUTHARK_RUNES,
        GOLDEN_DAWN_GRADES,
        I_CHING_HEXAGRAMS,
        MASTER_NUMBERS,
        NUMEROLOGY_NUMBERS,
        SEVEN_RAYS,
        TAROT_COURTS,
        TAROT_MAJORS,
        TAROT_SPREADS,
        TREE_OF_LIFE_PATHS,
        TREE_OF_LIFE_SEPHIROTH,
        AlchemyStage,
        DecanAssignment,
        DecanDefinition,
        GoldenDawnGrade,
        Hexagram,
        NumerologyNumber,
        PathDefinition,
        RayDefinition,
        Rune,
        SephiraDefinition,
        TarotCourtCard,
        TarotMajorArcana,
        TarotSpread,
    )
    from .fixedstars import skyfield_stars
    from .infrastructure.environment import collect_environment_report, main as environment_report_main
    from .jyotish import (
        GrahaYuddhaOutcome,
        HouseClaim,
        HouseWinner,
        SrishtiAspect,
        StrengthScore,
        compute_srishti_aspects,
        determine_house_lords,
        detect_graha_yuddha,
        evaluate_house_claims,
        evaluate_house_claims_from_chart,
        house_occupants,
        karakas_for_house,
        match_karakas,
        score_planet_strength,
    )
    from .maint import main as maint_main
    from .modules import (
        AstroChannel,
        AstroModule,
        AstroRegistry,
        AstroSubchannel,
        AstroSubmodule,
        DEFAULT_REGISTRY,
        bootstrap_default_registry,
    )
    from .modules.vca import serialize_vca_ruleset
    from .narrative_overlay import (
        NarrativeOverlay,
        apply_resonance_overlay,
        format_confidence_band,
        select_resonance_focus,
    )
    from .profiles import (
        DomainScoringProfile,
        ResonanceWeights,
        VCA_DOMAIN_PROFILES,
        load_base_profile,
        load_profile,
        load_resonance_weights,
        load_vca_outline,
    )
    from .providers import EphemerisProvider, get_provider, list_providers
    from .ritual import (
        CHALDEAN_ORDER,
        ELECTIONAL_WINDOWS,
        PLANETARY_DAYS,
        PLANETARY_HOUR_TABLE,
        VOID_OF_COURSE_RULES,
        ElectionalWindow,
        PlanetaryDay,
        VoidOfCourseRule,
    )
    from .rulesets import VCA_RULESET, get_vca_aspect, vca_orb_for
    from .scoring import (
        DEFAULT_ASPECTS,
        OrbCalculator,
        OrbPolicy,
        ScoreInputs,
        ScoreResult,
        SeverityPolicy,
        VisibilityPolicy,
        compute_score,
        compute_uncertainty_confidence,
        load_dignities,
        load_orb_policy,
        load_severity_policy,
        load_visibility_policy,
        lookup_dignities,
    )
    from .utils.angles import classify_applying_separating, delta_angle, norm360
    from .valence import combine_valence

    try:  # pragma: no cover - optional dependency in some environments
        from .events import (
            DirectionEvent,
            EclipseEvent,
            LunationEvent,
            OutOfBoundsEvent,
            ProfectionEvent,
            ProgressionEvent,
            ReturnEvent,
            StationEvent,
        )
    except ImportError:  # pragma: no cover - legacy events surface may be absent
        pass


_LAZY_SUBMODULES: dict[str, tuple[str, ...]] = {
    "agents": ("AgentSDK",),
    "analysis": ("condition_report", "score_accidental", "score_essential"),
    "atlas.tz": (
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
    "astro": ("declination",),
    "canonical": ("BodyPosition",),
    "catalogs": (
        "VCA_CENTAURS",
        "VCA_CORE_BODIES",
        "VCA_EXT_ASTEROIDS",
        "VCA_SENSITIVE_POINTS",
        "VCA_TNOS",
        "sbdb",
    ),
    "chart": (
        "ChartLocation",
        "CompositePosition",
        "DirectedChart",
        "HarmonicChart",
        "HarmonicPosition",
        "MidpointCompositeChart",
        "NatalChart",
        "ProgressedChart",
        "ReturnChart",
        "compute_composite_chart",
        "compute_harmonic_chart",
        "compute_natal_chart",
        "compute_return_chart",
        "compute_secondary_progressed_chart",
        "compute_solar_arc_chart",
    ),
    "chart.config": ("ChartConfig", "VALID_HOUSE_SYSTEMS", "VALID_ZODIAC_SYSTEMS"),
    "core": (
        "AngleTracker",
        "DOMAINS",
        "ELEMENT_DOMAIN_BRIDGE",
        "ELEMENTS",
        "DomainResolution",
        "DomainResolver",
        "TransitEngine",
        "TransitEngineConfig",
        "TransitEvent",
        "TransitScanConfig",
        "ZODIAC_ELEMENT_MAP",
        "apply_profile_if_any",
        "classify_relative_motion",
        "compute_domain_factor",
        "get_active_aspect_angles",
        "get_feature_flag",
        "load_profile_json",
        "maybe_attach_domain_fields",
        "natal_domain_factor",
        "normalize_degrees",
        "profile_into_ctx",
        "to_tt",
    ),
    "core.bodies": ("body_class",),
    "diagnostics": ("collect_diagnostics",),
    "domains": ("rollup_domain_scores",),
    "engine.vedic": (
        "CharaKaraka",
        "EclipseAlignment",
        "IshtaKashtaResult",
        "KarakamshaLagna",
        "KarmaSegment",
        "KarmicProfile",
        "Nakshatra",
        "NakshatraPosition",
        "NAKSHATRA_ARC_DEGREES",
        "PADA_ARC_DEGREES",
        "assign_decans",
        "build_karmic_profile",
        "compute_chara_karakas",
        "decan_for_longitude",
        "eclipse_alignment_roles",
        "ishta_kashta_phala",
        "karakamsha_lagna",
        "karma_attributions",
        "lord_of_nakshatra",
        "nakshatra_info",
        "nakshatra_of",
        "pada_of",
        "position_for",
    ),
    "ephemeris": (
        "EphemerisAdapter",
        "EphemerisConfig",
        "EphemerisSample",
        "ObserverLocation",
        "RefineResult",
        "RefinementError",
        "SwissEphemerisAdapter",
        "TimeScaleContext",
        "SECONDS_PER_DAY",
        "bracket_root",
        "refine_event",
        "refine_root",
    ),
    "esoteric": (
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
    "fixedstars": ("skyfield_stars",),
    "infrastructure.environment": ("collect_environment_report",),
    "jyotish": (
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
    "modules": (
        "AstroChannel",
        "AstroModule",
        "AstroRegistry",
        "AstroSubchannel",
        "AstroSubmodule",
        "DEFAULT_REGISTRY",
        "bootstrap_default_registry",
    ),
    "modules.vca": ("serialize_vca_ruleset",),
    "narrative_overlay": (
        "NarrativeOverlay",
        "apply_resonance_overlay",
        "format_confidence_band",
        "select_resonance_focus",
    ),
    "profiles": (
        "DomainScoringProfile",
        "ResonanceWeights",
        "VCA_DOMAIN_PROFILES",
        "load_base_profile",
        "load_profile",
        "load_resonance_weights",
        "load_vca_outline",
    ),
    "providers": ("EphemerisProvider", "get_provider", "list_providers"),
    "ritual": (
        "CHALDEAN_ORDER",
        "ELECTIONAL_WINDOWS",
        "PLANETARY_DAYS",
        "PLANETARY_HOUR_TABLE",
        "VOID_OF_COURSE_RULES",
        "ElectionalWindow",
        "PlanetaryDay",
        "VoidOfCourseRule",
    ),
    "rulesets": ("VCA_RULESET", "get_vca_aspect", "vca_orb_for"),
    "scoring": (
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
    "utils.angles": ("classify_applying_separating", "delta_angle", "norm360"),
    "valence": ("combine_valence",),
}

_LAZY_ATTRS: dict[str, tuple[str, str]] = {}
for _module, _names in _LAZY_SUBMODULES.items():
    for _name in _names:
        _LAZY_ATTRS[_name] = (_module, _name)

_ALIAS_IMPORTS: dict[str, tuple[str, str]] = {
    "environment_report_main": ("infrastructure.environment", "main"),
    "maint_main": ("maint", "main"),
}

_OPTIONAL_IMPORTS: dict[str, tuple[str, str]] = {
    "DirectionEvent": ("events", "DirectionEvent"),
    "EclipseEvent": ("events", "EclipseEvent"),
    "LunationEvent": ("events", "LunationEvent"),
    "OutOfBoundsEvent": ("events", "OutOfBoundsEvent"),
    "ProfectionEvent": ("events", "ProfectionEvent"),
    "ProgressionEvent": ("events", "ProgressionEvent"),
    "ReturnEvent": ("events", "ReturnEvent"),
    "StationEvent": ("events", "StationEvent"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_ATTRS:
        module_name, attr_name = _LAZY_ATTRS[name]
        module = import_module(f".{module_name}", __name__)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    if name in _ALIAS_IMPORTS:
        module_name, attr_name = _ALIAS_IMPORTS[name]
        module = import_module(f".{module_name}", __name__)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    if name in _OPTIONAL_IMPORTS:
        module_name, attr_name = _OPTIONAL_IMPORTS[name]
        try:
            module = import_module(f".{module_name}", __name__)
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
        | set(_LAZY_ATTRS)
        | set(_ALIAS_IMPORTS)
        | set(_OPTIONAL_IMPORTS)
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
