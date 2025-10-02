"""Jyotish (Vedic) utilities integrated with the core engine."""

from __future__ import annotations

from .ayanamsa import (
    AyanamsaInfo,
    AyanamsaPreset,
    SIDEREAL_PRESETS,
    PRIMARY_AYANAMSAS,
    available_ayanamsas,
    ayanamsa_metadata,
    ayanamsa_value,
    normalize_ayanamsa,
    swe_ayanamsa,
)
from .ashtakavarga import (
    AshtakavargaSet,
    Bhinnashtakavarga,
    compute_bhinnashtakavarga,
    compute_sarvashtakavarga,
)
from .chart import VedicChartContext, compute_sidereal_chart, build_context
from .dasha_vimshottari import (
    DashaPeriod,
    VimshottariOptions,
    build_vimshottari,
    vimshottari_sequence,
)
from .dasha_yogini import build_yogini, yogini_sequence

from .gochar import (
    GocharTransitReport,
    RetrogradeTrigger,
    TransitAlert,
    TransitInteraction,
    TransitSnapshot,
    TransitWeightPolicy,
    analyse_gochar_transits,
)
from .karmic import (
    CharaKaraka,
    EclipseAlignment,
    IshtaKashtaResult,
    KarakamshaLagna,
    KarmaSegment,
    KarmicProfile,
    build_karmic_profile,
    compute_chara_karakas,
    eclipse_alignment_roles,
    ishta_kashta_phala,
    karakamsha_lagna,
    karma_attributions,
)

from .nakshatra import (
    NAKSHATRA_ARC_DEGREES,
    PADA_ARC_DEGREES,
    Nakshatra,
    NakshatraPosition,
    lord_of_nakshatra,
    nakshatra_info,
    nakshatra_of,
    pada_of,
    position_for,
)

from .panchang import NakshatraStatus
from .panchanga import lunar_month
from .shadbala import ShadbalaReport, ShadbalaScore, compute_shadbala
from .yogas import analyze_yogas
from .varga import (
    VARGA_DEFINITIONS,
    compute_varga,
    dasamsa_sign,
    navamsa_sign,
    saptamsa_sign,
)


__all__ = [
    "AyanamsaInfo",
    "AyanamsaPreset",
    "SIDEREAL_PRESETS",
    "PRIMARY_AYANAMSAS",
    "available_ayanamsas",
    "ayanamsa_metadata",
    "ayanamsa_value",
    "normalize_ayanamsa",
    "swe_ayanamsa",
    "VedicChartContext",
    "compute_sidereal_chart",
    "build_context",
    "DashaPeriod",
    "VimshottariOptions",
    "build_vimshottari",
    "vimshottari_sequence",
    "build_yogini",
    "yogini_sequence",

    "TransitSnapshot",
    "TransitInteraction",
    "TransitAlert",
    "RetrogradeTrigger",
    "TransitWeightPolicy",
    "GocharTransitReport",
    "analyse_gochar_transits",

    "NAKSHATRA_ARC_DEGREES",
    "PADA_ARC_DEGREES",
    "Nakshatra",
    "NakshatraPosition",
    "NakshatraStatus",
    "lunar_month",
    "lord_of_nakshatra",
    "nakshatra_info",
    "nakshatra_of",
    "pada_of",
    "position_for",
    "NakshatraStatus",

    "VARGA_DEFINITIONS",

    "compute_varga",
    "dasamsa_sign",
    "navamsa_sign",
    "saptamsa_sign",

    "CharaKaraka",
    "KarakamshaLagna",
    "IshtaKashtaResult",
    "KarmaSegment",
    "KarmicProfile",
    "EclipseAlignment",
    "compute_chara_karakas",
    "karakamsha_lagna",
    "ishta_kashta_phala",
    "karma_attributions",
    "eclipse_alignment_roles",
    "build_karmic_profile",

    "Bhinnashtakavarga",
    "AshtakavargaSet",
    "compute_bhinnashtakavarga",
    "compute_sarvashtakavarga",
    "ShadbalaScore",
    "ShadbalaReport",
    "compute_shadbala",
    "analyze_yogas",

]
