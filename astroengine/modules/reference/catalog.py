"""Structured reference catalog for AstroEngine's knowledge base module.

The catalog enumerates the high-level concepts that the runtime exposes
through the registry. Each entry links a human-readable description with
concrete provenance data so knowledge lookups can always be traced back to
verifiable sources.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Mapping

__all__ = [
    "ReferenceSource",
    "ReferenceEntry",
    "GLOSSARY",
    "CHART_TYPES",
    "FRAMEWORKS",
    "INDICATORS",
    "REFERENCE_SECTIONS",
]


@dataclass(frozen=True)
class ReferenceSource:
    """Documentation or dataset that substantiates a knowledge-base entry."""

    name: str
    citation: str
    url: str | None = None
    repository_path: str | None = None

    def as_payload(self) -> dict[str, str]:
        data: dict[str, str] = {
            "name": self.name,
            "citation": self.citation,
        }
        if self.url:
            data["url"] = self.url
        if self.repository_path:
            data["repository_path"] = self.repository_path
        return data


@dataclass(frozen=True)
class ReferenceEntry:
    """A single knowledge base entry."""

    term: str
    summary: str
    sources: tuple[ReferenceSource, ...]
    related: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


# Consolidated ``ReferenceSource`` definitions reused across multiple catalog
# sections.  The constants keep citations in sync whenever a module appears in
# several reference groups.

_NATAL_MODULE_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="AstroEngine natal chart module",
    citation="AstroEngine maintainers. (2025). Natal chart computation pipeline.",
    repository_path="astroengine/chart/natal.py",
)
_SWISS_EPHEMERIS_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="Swiss Ephemeris for Programmers",
    citation="Astrodienst AG. (2023). Swiss Ephemeris for Programmers: Technical documentation.",
    url="https://www.astro.com/swisseph/swephprg.htm",
)
_NATAL_CHART_SOURCES: Final[tuple[ReferenceSource, ReferenceSource]] = (
    _NATAL_MODULE_SOURCE,
    _SWISS_EPHEMERIS_SOURCE,
)

_PROGRESSION_MODULE_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="AstroEngine progression module",
    citation="AstroEngine maintainers. (2025). Secondary progression computation routine.",
    repository_path="astroengine/chart/progressions.py",
)
_PROGRESSION_TEXT_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="The Only Way to Learn Astrology, Volume 3",
    citation="March, M. D., & McEvers, J. (1980). The Only Way to Learn Astrology, Vol. 3. ACS Publications. Chapter 1.",
)
_PROGRESSION_SOURCES: Final[tuple[ReferenceSource, ReferenceSource]] = (
    _PROGRESSION_MODULE_SOURCE,
    _PROGRESSION_TEXT_SOURCE,
)

_RETURN_MODULE_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="AstroEngine return chart module",
    citation="AstroEngine maintainers. (2025). Return chart computation pipeline.",
    repository_path="astroengine/chart/returns.py",
)
_RETURN_TEXT_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="Solar Returns",
    citation="Carter, C. E. O. (1971). Solar Returns. Regulus Publishing Company.",
)
_RETURN_CHART_SOURCES: Final[tuple[ReferenceSource, ReferenceSource]] = (
    _RETURN_MODULE_SOURCE,
    _RETURN_TEXT_SOURCE,
)

_INDICATORS_OUTLINE_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="Astrological indicators outline",
    citation="AstroEngine maintainers. (2025). Astrological indicators outline.",
    repository_path="docs/reference/astrological_indicators.md",
)

_HOUSE_SYSTEMS_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="House systems engine",
    citation="AstroEngine maintainers. (2025). House system enumeration and validation routines.",
    repository_path="core/houses_plus/engine.py",
)

_HOUSE_CONFIG_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="Chart configuration normaliser",
    citation="AstroEngine maintainers. (2025). Chart configuration validation for house systems.",
    repository_path="astroengine/chart/config.py",
)

_HARMONICS_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="Aspect harmonics registry",
    citation="AstroEngine maintainers. (2025). Harmonic aspect families and canonical angles.",
    repository_path="astroengine/core/aspects_plus/harmonics.py",
)

_ASPECT_POLICY_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="Aspect policy dataset",
    citation="AstroEngine maintainers. (2025). Aspect families, harmonics, and orb allowances.",
    repository_path="profiles/aspects_policy.json",
)

_DIGNITIES_DATA_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="Traditional dignity dataset",
    citation="AstroEngine maintainers. (2025). Bounds, decans, and dignity scoring coefficients.",
    repository_path="profiles/dignities.csv",
)

_DECANS_MODULE_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="Decan correspondence module",
    citation="AstroEngine maintainers. (2025). Decan-to-tarot mappings and runtime helpers.",
    repository_path="astroengine/esoteric/decans.py",
)

_TRANSITS_MODULE_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="Transit detection module",
    citation="AstroEngine maintainers. (2025). Transit scanning and aspect matching pipeline.",
    repository_path="astroengine/chart/transits.py",
)

_PROFECTIONS_MODULE_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="Annual profections engine",
    citation="AstroEngine maintainers. (2025). Traditional profection and time-lord scheduler.",
    repository_path="astroengine/engine/traditional/profections.py",
)

_ESOTERIC_MODULE_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="Esoteric overlays registry",
    citation="AstroEngine maintainers. (2025). Registry wiring for decans, tarot, and Seven Rays datasets.",
    repository_path="astroengine/modules/esoteric/__init__.py",
)

_SEVEN_RAYS_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="Seven Rays correspondences",
    citation="AstroEngine maintainers. (2025). Seven Rays planetary and ray attributions.",
    repository_path="astroengine/esoteric/seven_rays.py",
)

_JYOTISH_MODULE_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="Jyotiṣa toolkit",
    citation="AstroEngine maintainers. (2025). Jyotiṣa graha dignities, yogas, and dasa calculations.",
    repository_path="astroengine/jyotish/__init__.py",
)

_TRADITIONAL_MODELS_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="Traditional model definitions",
    citation="AstroEngine maintainers. (2025). Sect, triplicity, and time-lord configuration models.",
    repository_path="astroengine/engine/traditional/models.py",
)

_MUNDANE_DOC_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="Outer cycle analytics documentation",
    citation="AstroEngine maintainers. (2025). Outer planet cycles, harmonics, and ingress scoring outline.",
    repository_path="docs/module/mundane/submodules/outer_cycle_analytics.md",
)

_INGRESS_MODULE_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="Mundane ingress module",
    citation="AstroEngine maintainers. (2025). Cardinal ingress chart computation and cycle baselines.",
    repository_path="astroengine/mundane/ingress.py",
)

_ARABIC_PARTS_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="Arabic parts analysis module",
    citation="AstroEngine maintainers. (2025). Arabic parts calculations and scoring helpers.",
    repository_path="astroengine/analysis/arabic_parts.py",
)

_LOTS_EVENTS_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="Lots event engine",
    citation="AstroEngine maintainers. (2025). Event-driven part calculations and metadata payloads.",
    repository_path="astroengine/engine/lots/events.py",
)

_FIXED_STARS_DATA_SOURCE: Final[ReferenceSource] = ReferenceSource(
    name="Fixed star catalog dataset",
    citation="AstroEngine maintainers. (2025). Fixed star positions and metadata for symbolic overlays.",
    repository_path="profiles/fixed_stars.csv",
)


GLOSSARY: Mapping[str, ReferenceEntry] = {
    "natal_chart": ReferenceEntry(
        term="Natal chart",
        summary=(
            "Radix snapshot produced by ``astroengine.chart.natal.compute_natal_chart`` "
            "using the Swiss Ephemeris adapter, documented orb policy, and house "
            "configuration captured in ``ChartConfig``."
        ),
        sources=_NATAL_CHART_SOURCES,
        related=(
            "profiles/base_profile.yaml",
            "schemas/orbs_policy.json",
        ),
        tags=("astrology", "foundational"),
    ),
    "transit_contact": ReferenceEntry(
        term="Transit contact",
        summary=(
            "Aspect event detected by ``astroengine.chart.transits.TransitScanner`` "
            "when a moving body forms an enabled aspect to a natal position with an "
            "orb permitted by the shared orb calculator."
        ),
        sources=(
            ReferenceSource(
                name="AstroEngine transit detection module",
                citation="AstroEngine maintainers. (2025). Transit scanning implementation details.",
                repository_path="astroengine/chart/transits.py",
            ),
            ReferenceSource(
                name="Predictive Astrology: The Eagle and the Lark",
                citation="Brady, B. (2008). Predictive Astrology: The Eagle and the Lark. Weiser Books. Chapters 2–4.",
            ),
        ),
        related=(
            "qa/artifacts/solarfire/2025-10-02/cross_engine.json",
            "profiles/aspects_policy.json",
        ),
        tags=("astrology", "timing"),
    ),
    "progressed_positions": ReferenceEntry(
        term="Progressed positions",
        summary=(
            "Secondary progression longitudes generated in "
            "``astroengine.chart.progressions.compute_secondary_progression`` "
            "using the day-for-a-year method mirrored from Solar Fire outputs."
        ),
        sources=_PROGRESSION_SOURCES,
        related=(
            "qa/artifacts/solarfire/2025-10-02/cross_engine.json",
            "profiles/base_profile.yaml",
        ),
        tags=("astrology", "forecasting"),
    ),
    "solar_return": ReferenceEntry(
        term="Solar return",
        summary=(
            "Annual chart cast in ``astroengine.chart.returns.compute_return_chart`` "
            "when the transiting Sun revisits its natal longitude; used for Solar Fire "
            "parity checks in the maintainer QA artifacts."
        ),
        sources=_RETURN_CHART_SOURCES,
        related=(
            "qa/artifacts/solarfire/2025-10-02/cross_engine.json",
        ),
        tags=("astrology", "forecasting"),
    ),
    "composite_chart": ReferenceEntry(
        term="Composite chart",
        summary=(
            "Relationship midpoint chart composed by ``astroengine.chart.composite`` "
            "routines that average natal positions and provenance metadata for two "
            "participants."
        ),
        sources=(
            ReferenceSource(
                name="AstroEngine composite chart module",
                citation="AstroEngine maintainers. (2025). Composite chart computation workflow.",
                repository_path="astroengine/chart/composite.py",
            ),
            ReferenceSource(
                name="Planets in Composite",
                citation="Hand, R. (1975). Planets in Composite. Whitford Press.",
            ),
        ),
        related=(
            "astroengine/synastry",
            "profiles/base_profile.yaml",
        ),
        tags=("astrology", "relationship"),
    ),
    "aspect_orb_policy": ReferenceEntry(
        term="Aspect orb policy",
        summary=(
            "Repository-wide orb allowances resolved through "
            "``astroengine.scoring.orb.OrbCalculator`` and the versioned "
            "``profiles/aspects_policy.json`` dataset."
        ),
        sources=(
            ReferenceSource(
                name="AstroEngine orb calculator",
                citation="AstroEngine maintainers. (2025). Orb calculation rules.",
                repository_path="astroengine/scoring/orb.py",
            ),
            ReferenceSource(
                name="The Astrologer's Handbook",
                citation="Sakoian, F., & Acker, L. (1973). The Astrologer's Handbook. HarperCollins. Appendix on aspect orbs.",
            ),
        ),
        related=(
            "schemas/orbs_policy.json",
            "docs/module/core-transit-math.md",
        ),
        tags=("astrology", "scoring"),
    ),
    "ayanamsa_profile": ReferenceEntry(
        term="Ayanāṁśa profile",
        summary=(
            "Sidereal offsets controlled by ``ChartConfig`` and evaluated through the "
            "Swiss Ephemeris adapter whenever a chart is computed in sidereal mode."
        ),
        sources=(
            ReferenceSource(
                name="AstroEngine chart configuration",
                citation="AstroEngine maintainers. (2025). Chart configuration and ayanāṁśa support.",
                repository_path="astroengine/chart/config.py",
            ),
            ReferenceSource(
                name="Sidereal Astrology",
                citation="Fagan, C., & Bradley, D. (1950). Sidereal Astrology. Llewellyn Publications.",
            ),
        ),
        related=(
            "astroengine/ephemeris/sidereal.py",
        ),
        tags=("astrology", "sidereal"),
    ),
}


CHART_TYPES: Mapping[str, ReferenceEntry] = {
    "natal": ReferenceEntry(
        term="Natal chart",
        summary=(
            "Base event chart produced for births or project inceptions. Natal charts "
            "anchor every downstream timing technique and feed the transit, "
            "progression, and synastry modules."
        ),
        sources=_NATAL_CHART_SOURCES,
        related=(
            "astroengine/modules/data_packs/__init__.py",
        ),
        tags=("astrology", "chart"),
    ),
    "progressed": ReferenceEntry(
        term="Secondary progression",
        summary=(
            "Chart advanced using the Solar Fire style day-for-a-year key via "
            "``astroengine.chart.progressions.compute_secondary_progression``."
        ),
        sources=_PROGRESSION_SOURCES,
        related=(
            "astroengine/modules/predictive/__init__.py",
        ),
        tags=("astrology", "chart"),
    ),
    "return": ReferenceEntry(
        term="Planetary return",
        summary=(
            "Return chart utilities from ``astroengine.chart.returns`` that locate the "
            "exact moment a selected body revisits its natal longitude (solar, lunar, "
            "or custom returns)."
        ),
        sources=_RETURN_CHART_SOURCES,
        related=(
            "astroengine/modules/event_detectors/__init__.py",
        ),
        tags=("astrology", "chart"),
    ),
    "synastry": ReferenceEntry(
        term="Synastry overlays",
        summary=(
            "Cross-chart contacts and scoring routines in ``astroengine.synastry`` that "
            "feed the relationship timeline and VCA resonance pipelines."
        ),
        sources=(
            ReferenceSource(
                name="AstroEngine synastry module",
                citation="AstroEngine maintainers. (2025). Synastry overlay implementation.",
                repository_path="astroengine/synastry/__init__.py",
            ),
            ReferenceSource(
                name="Relating: An Astrological Guide to Living with Others",
                citation="Greene, L. (1977). Relating: An Astrological Guide to Living with Others on a Small Planet. Weiser Books.",
            ),
        ),
        related=(
            "astroengine/modules/relation_timeline",
            "astroengine/modules/vca",
        ),
        tags=("astrology", "relationship"),
    ),
}


FRAMEWORKS: Mapping[str, ReferenceEntry] = {
    "vca": ReferenceEntry(
        term="Venus Cycle Analytics",
        summary=(
            "Psychological resonance model encoded in ``astroengine.modules.vca`` and "
            "its CSV outline. The module blends house domains, dignity weights, and "
            "timing overlays derived from Solar Fire research exports."
        ),
        sources=(
            ReferenceSource(
                name="AstroEngine VCA module",
                citation="AstroEngine maintainers. (2025). Venus Cycle Analytics implementation overview.",
                repository_path="astroengine/modules/vca/__init__.py",
            ),
            ReferenceSource(
                name="profiles/vca_outline.json dataset",
                citation="AstroEngine maintainers. (2025). Venus Cycle Analytics outline dataset.",
                repository_path="profiles/vca_outline.json",
            ),
            ReferenceSource(
                name="The Lunation Cycle",
                citation="Rudhyar, D. (1986). The Lunation Cycle. Aurora Press. Chapters on Venus phases.",
            ),
        ),
        related=(
            "docs/vca_profile_mapping.md",
            "tests/test_vca_profile.py",
        ),
        tags=("psychology", "scoring"),
    ),
    "seven_rays": ReferenceEntry(
        term="Seven Rays",
        summary=(
            "Esoteric psychology correspondences distributed through "
            "``astroengine.esoteric.seven_rays.SEVEN_RAYS`` with ray virtues, vices, "
            "and planetary rulers."
        ),
        sources=(
            ReferenceSource(
                name="AstroEngine Seven Rays dataset",
                citation="AstroEngine maintainers. (2025). Seven Rays correspondences.",
                repository_path="astroengine/esoteric/seven_rays.py",
            ),
            ReferenceSource(
                name="Esoteric Psychology Volume I",
                citation="Bailey, A. A. (1936). Esoteric Psychology, Volume I. Lucis Publishing Company.",
            ),
        ),
        related=(
            "astroengine/modules/esoteric/__init__.py",
        ),
        tags=("psychology", "esoteric"),
    ),
    "tarot_correspondences": ReferenceEntry(
        term="Golden Dawn tarot correspondences",
        summary=(
            "Major, court, and pip card mappings in ``astroengine.esoteric.tarot`` that "
            "back the tarot overlays and documented spreads."
        ),
        sources=(
            ReferenceSource(
                name="AstroEngine tarot correspondences",
                citation="AstroEngine maintainers. (2025). Golden Dawn tarot correspondences dataset.",
                repository_path="astroengine/esoteric/tarot.py",
            ),
            ReferenceSource(
                name="The Golden Dawn",
                citation="Regardie, I. (1989). The Golden Dawn. Llewellyn Publications. Book T correspondences.",
            ),
        ),
        related=(
            "tests/esoteric/test_symbolic_overlays.py",
            "astroengine/modules/esoteric/__init__.py",
        ),
        tags=("tarot", "esoteric"),
    ),
    "tree_of_life": ReferenceEntry(
        term="Tree of Life paths",
        summary=(
            "Path attributions in ``astroengine.esoteric.tree_of_life`` joining Hebrew "
            "letters, planetary rulerships, and tarot keys for the Golden Dawn system."
        ),
        sources=(
            ReferenceSource(
                name="AstroEngine Tree of Life dataset",
                citation="AstroEngine maintainers. (2025). Tree of Life path correspondences.",
                repository_path="astroengine/esoteric/tree_of_life.py",
            ),
            ReferenceSource(
                name="The Qabalistic Tarot",
                citation="Wang, R. (2004). The Qabalistic Tarot. Samuel Weiser. Path correspondences appendix.",
            ),
        ),
        related=(
            "astroengine/modules/esoteric/__init__.py",
        ),
        tags=("tarot", "kabbalah"),
    ),
}


INDICATORS: Mapping[str, ReferenceEntry] = {
    "celestial_bodies": ReferenceEntry(
        term="Celestial bodies",
        summary=(
            "Luminaries, classical planets, modern discoveries, and calculated points "
            "enumerated in the indicators outline and implemented through the "
            "``DEFAULT_BODIES`` map shared by chart factories."
        ),
        sources=(
            _INDICATORS_OUTLINE_SOURCE,
            _NATAL_MODULE_SOURCE,
        ),
        related=("profiles/base_profile.yaml",),
        tags=("astrology", "bodies"),
    ),
    "house_systems": ReferenceEntry(
        term="House systems",
        summary=(
            "Quadrant, whole-sign, equal, and topocentric house options with provenance "
            "logging that records requested versus computed systems."
        ),
        sources=(
            _INDICATORS_OUTLINE_SOURCE,
            _HOUSE_SYSTEMS_SOURCE,
            _HOUSE_CONFIG_SOURCE,
        ),
        related=("core/houses_plus/engine.py", "astroengine/chart/config.py"),
        tags=("astrology", "houses"),
    ),
    "aspect_families": ReferenceEntry(
        term="Aspect families and harmonics",
        summary=(
            "Ptolemaic, minor, and harmonic aspect groups with shared orb governance "
            "mirrored in the aspect policy dataset."
        ),
        sources=(
            _INDICATORS_OUTLINE_SOURCE,
            _HARMONICS_SOURCE,
            _ASPECT_POLICY_SOURCE,
        ),
        related=("profiles/aspects_policy.json", "docs/module/core-transit-math.md"),
        tags=("astrology", "aspects"),
    ),
    "zodiac_subdivisions": ReferenceEntry(
        term="Zodiac subdivisions",
        summary=(
            "Bounds, decans, dwads, and nakṣatra overlays that expand sign-based "
            "interpretation frameworks."
        ),
        sources=(
            _INDICATORS_OUTLINE_SOURCE,
            _DIGNITIES_DATA_SOURCE,
            _DECANS_MODULE_SOURCE,
        ),
        related=("profiles/dignities.csv", "astroengine/esoteric/decans.py"),
        tags=("astrology", "dignities"),
    ),
    "timing_techniques": ReferenceEntry(
        term="Timing techniques",
        summary=(
            "Transit, progression, direction, and profection engines that drive "
            "forecasting workflows and parity checks."
        ),
        sources=(
            _INDICATORS_OUTLINE_SOURCE,
            _TRANSITS_MODULE_SOURCE,
            _PROFECTIONS_MODULE_SOURCE,
        ),
        related=(
            "astroengine/chart/transits.py",
            "astroengine/chart/progressions.py",
            "astroengine/chart/directions.py",
        ),
        tags=("astrology", "timing"),
    ),
    "esoteric_systems": ReferenceEntry(
        term="Esoteric systems",
        summary=(
            "Seven Rays psychology, Tree of Life paths, tarot correspondences, and "
            "chakra mappings that enrich interpretive overlays."
        ),
        sources=(
            _INDICATORS_OUTLINE_SOURCE,
            _ESOTERIC_MODULE_SOURCE,
            _SEVEN_RAYS_SOURCE,
        ),
        related=("astroengine/esoteric/seven_rays.py", "astroengine/esoteric/tarot.py"),
        tags=("esoteric", "symbolism"),
    ),
    "cultural_systems": ReferenceEntry(
        term="Cultural systems",
        summary=(
            "Jyotiṣa, Hellenistic, Mesoamerican, and humanistic frameworks that align "
            "with AstroEngine's multicultural tooling."
        ),
        sources=(
            _INDICATORS_OUTLINE_SOURCE,
            _JYOTISH_MODULE_SOURCE,
            _TRADITIONAL_MODELS_SOURCE,
        ),
        related=("astroengine/jyotish", "astroengine/engine/traditional"),
        tags=("astrology", "cultural"),
    ),
    "collective_cycles": ReferenceEntry(
        term="Collective cycles",
        summary=(
            "Outer-planet synodic pairs, ingress analytics, eclipse seasons, and "
            "planetary phase indexes for socio-economic modelling."
        ),
        sources=(
            _INDICATORS_OUTLINE_SOURCE,
            _MUNDANE_DOC_SOURCE,
            _INGRESS_MODULE_SOURCE,
        ),
        related=("astroengine/mundane/ingress.py", "profiles/vca_outline.json"),
        tags=("astrology", "mundane"),
    ),
    "symbolic_overlays": ReferenceEntry(
        term="Symbolic overlays",
        summary=(
            "Arabic parts, fixed stars, asteroid selections, and mythopoetic "
            "narratives layered onto core chart data."
        ),
        sources=(
            _INDICATORS_OUTLINE_SOURCE,
            _ARABIC_PARTS_SOURCE,
            _LOTS_EVENTS_SOURCE,
            _FIXED_STARS_DATA_SOURCE,
        ),
        related=(
            "astroengine/analysis/arabic_parts.py",
            "astroengine/engine/lots",
            "profiles/fixed_stars.csv",
        ),
        tags=("astrology", "symbolism"),
    ),
}


REFERENCE_SECTIONS: Mapping[str, Mapping[str, ReferenceEntry]] = {
    "glossary": GLOSSARY,
    "chart_types": CHART_TYPES,
    "frameworks": FRAMEWORKS,
    "indicators": INDICATORS,
}
