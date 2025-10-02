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

from .varga import compute_varga, dasamsa_sign, navamsa_sign
from .shadbala import ShadbalaReport, ShadbalaScore, compute_shadbala


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
    "lord_of_nakshatra",
    "nakshatra_info",
    "nakshatra_of",
    "pada_of",
    "position_for",
    "TITHI_ARC_DEGREES",
    "YOGA_ARC_DEGREES",
    "KARANA_ARC_DEGREES",
    "Tithi",
    "Yoga",
    "Karana",
    "Vaar",
    "Panchang",
    "tithi_from_longitudes",
    "yoga_from_longitudes",
    "karana_from_longitudes",
    "nakshatra_from_longitude",
    "vaar_from_datetime",
    "panchang_from_chart",
    "compute_varga",
    "dasamsa_sign",
    "navamsa_sign",

    "Bhinnashtakavarga",
    "AshtakavargaSet",
    "compute_bhinnashtakavarga",
    "compute_sarvashtakavarga",
    "ShadbalaScore",
    "ShadbalaReport",
    "compute_shadbala",

]
