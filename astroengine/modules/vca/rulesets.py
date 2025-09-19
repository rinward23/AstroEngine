"""Ruleset metadata for aspect detection."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class AspectDef:
    name: str
    angle: float
    klass: str
    default_orb_deg: float


_VCA_ASPECTS: dict[str, AspectDef] = {
    "conjunction": AspectDef("conjunction", 0.0, "major", 10.0),
    "opposition": AspectDef("opposition", 180.0, "major", 10.0),
    "square": AspectDef("square", 90.0, "major", 8.0),
    "trine": AspectDef("trine", 120.0, "major", 8.0),
    "sextile": AspectDef("sextile", 60.0, "major", 6.0),
    "semisextile": AspectDef("semisextile", 30.0, "minor", 3.0),
    "quincunx": AspectDef("quincunx", 150.0, "minor", 3.0),
    "semisquare": AspectDef("semisquare", 45.0, "minor", 3.0),
    "sesquiquadrate": AspectDef("sesquiquadrate", 135.0, "minor", 3.0),
    "quintile": AspectDef("quintile", 72.0, "minor", 2.0),
    "biquintile": AspectDef("biquintile", 144.0, "minor", 2.0),
    "semiquintile": AspectDef("semiquintile", 36.0, "minor", 2.0),
    "semioctile": AspectDef("semioctile", 22.5, "minor", 1.0),
    "septile": AspectDef("septile", 51.428, "harmonic", 1.0),
    "biseptile": AspectDef("biseptile", 102.857, "harmonic", 1.0),
    "triseptile": AspectDef("triseptile", 154.286, "harmonic", 1.0),
    "novile": AspectDef("novile", 40.0, "harmonic", 1.0),
    "binovile": AspectDef("binovile", 80.0, "harmonic", 1.0),
    "undecile": AspectDef("undecile", 32.717, "harmonic", 1.0),
    "tredecile": AspectDef("tredecile", 108.0, "harmonic", 2.0),
    "quindecile": AspectDef("quindecile", 165.0, "harmonic", 2.0),
    "fifteenth": AspectDef("fifteenth", 24.0, "harmonic", 1.0),
    "quattuordecile": AspectDef("quattuordecile", 25.717, "harmonic", 1.0),
    "vigintile": AspectDef("vigintile", 18.0, "harmonic", 1.0),
    "antiscia": AspectDef("antiscia", 0.0, "mirror", 1.0),
    "contraantiscia": AspectDef("contraantiscia", 180.0, "mirror", 1.0),
    "parallel": AspectDef("parallel", 0.0, "declination", 1.0),
    "contraparallel": AspectDef("contraparallel", 180.0, "declination", 1.0),
}

_VCA_ORB_CLASS_DEFAULTS: Mapping[str, float] = {
    "major": 8.0,
    "minor": 2.0,
    "harmonic": 1.0,
    "declination": 1.0,
    "mirror": 1.0,
}


@dataclass(frozen=True)
class Ruleset:
    id: str
    aspects: Mapping[str, AspectDef]
    orb_class_defaults: Mapping[str, float]
    expand_luminaries: bool = True


VCA_RULESET = Ruleset(
    id="vca_core",
    aspects=_VCA_ASPECTS,
    orb_class_defaults=_VCA_ORB_CLASS_DEFAULTS,
)


def get_vca_aspect(name: str) -> AspectDef | None:
    return _VCA_ASPECTS.get(name.lower())


def vca_orb_for(name: str, *, override: float | None = None) -> float:
    if override is not None:
        return float(override)
    aspect = get_vca_aspect(name)
    if not aspect:
        return 0.0
    return float(_VCA_ORB_CLASS_DEFAULTS.get(aspect.klass, aspect.default_orb_deg))


__all__ = ["AspectDef", "Ruleset", "VCA_RULESET", "get_vca_aspect", "vca_orb_for"]
