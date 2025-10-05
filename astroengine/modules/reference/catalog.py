"""Structured reference catalog for AstroEngine's knowledge base module.

The catalog enumerates the high-level concepts that the runtime exposes
through the registry. Each entry links a human-readable description with
concrete provenance data so knowledge lookups can always be traced back to
verifiable sources.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

__all__ = [
    "ReferenceSource",
    "ReferenceEntry",
    "GLOSSARY",
    "CHART_TYPES",
    "FRAMEWORKS",
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


GLOSSARY: Mapping[str, ReferenceEntry] = {
    "natal_chart": ReferenceEntry(
        term="Natal chart",
        summary=(
            "Radix snapshot produced by ``astroengine.chart.natal.compute_natal_chart`` "
            "using the Swiss Ephemeris adapter, documented orb policy, and house "
            "configuration captured in ``ChartConfig``."
        ),
        sources=(
            ReferenceSource(
                name="AstroEngine natal chart module",
                citation="AstroEngine maintainers. (2025). Natal chart computation pipeline.",
                repository_path="astroengine/chart/natal.py",
            ),
            ReferenceSource(
                name="Swiss Ephemeris for Programmers",
                citation="Astrodienst AG. (2023). Swiss Ephemeris for Programmers: Technical documentation.",
                url="https://www.astro.com/swisseph/swephprg.htm",
            ),
        ),
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
        sources=(
            ReferenceSource(
                name="AstroEngine progression module",
                citation="AstroEngine maintainers. (2025). Secondary progression computation routine.",
                repository_path="astroengine/chart/progressions.py",
            ),
            ReferenceSource(
                name="The Only Way to Learn Astrology, Volume 3",
                citation="March, M. D., & McEvers, J. (1980). The Only Way to Learn Astrology, Vol. 3. ACS Publications. Chapter 1.",
            ),
        ),
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
        sources=(
            ReferenceSource(
                name="AstroEngine return chart module",
                citation="AstroEngine maintainers. (2025). Return chart computation pipeline.",
                repository_path="astroengine/chart/returns.py",
            ),
            ReferenceSource(
                name="Solar Returns",
                citation="Carter, C. E. O. (1971). Solar Returns. Regulus Publishing Company.",
            ),
        ),
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
        sources=(
            ReferenceSource(
                name="AstroEngine natal chart module",
                citation="AstroEngine maintainers. (2025). Natal chart computation pipeline.",
                repository_path="astroengine/chart/natal.py",
            ),
            ReferenceSource(
                name="Swiss Ephemeris for Programmers",
                citation="Astrodienst AG. (2023). Swiss Ephemeris for Programmers: Technical documentation.",
                url="https://www.astro.com/swisseph/swephprg.htm",
            ),
        ),
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
        sources=(
            ReferenceSource(
                name="AstroEngine progression module",
                citation="AstroEngine maintainers. (2025). Secondary progression computation routine.",
                repository_path="astroengine/chart/progressions.py",
            ),
            ReferenceSource(
                name="The Only Way to Learn Astrology, Volume 3",
                citation="March, M. D., & McEvers, J. (1980). The Only Way to Learn Astrology, Vol. 3. ACS Publications. Chapter 1.",
            ),
        ),
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
        sources=(
            ReferenceSource(
                name="AstroEngine return chart module",
                citation="AstroEngine maintainers. (2025). Return chart computation pipeline.",
                repository_path="astroengine/chart/returns.py",
            ),
            ReferenceSource(
                name="Solar Returns",
                citation="Carter, C. E. O. (1971). Solar Returns. Regulus Publishing Company.",
            ),
        ),
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


REFERENCE_SECTIONS: Mapping[str, Mapping[str, ReferenceEntry]] = {
    "glossary": GLOSSARY,
    "chart_types": CHART_TYPES,
    "frameworks": FRAMEWORKS,
}
