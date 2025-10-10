"""Harmonic aspect angle helpers."""

from __future__ import annotations

from collections.abc import Iterable
from math import gcd

BASE_ASPECTS = {
    "conjunction": 0.0,
    "semisextile": 30.0,
    "undecile": 32.7273,
    "semiquintile": 36.0,
    "novile": 40.0,
    "semisquare": 45.0,
    "septile": 51.4286,
    "sextile": 60.0,
    "quintile": 72.0,
    "binovile": 80.0,
    "square": 90.0,
    "biseptile": 102.8571,
    "tredecile": 108.0,
    "trine": 120.0,
    "sesquisquare": 135.0,
    "biquintile": 144.0,
    "quincunx": 150.0,
    "triseptile": 154.2857,
    "opposition": 180.0,
}


def base_aspect_angles(names: Iterable[str]) -> list[float]:
    """Return sorted unique base aspect angles for the provided names."""

    seen = set()
    angles: list[float] = []
    for name in names:
        key = (name or "").strip().lower()
        if key in BASE_ASPECTS and key not in seen:
            seen.add(key)
            angles.append(BASE_ASPECTS[key])
    angles.sort()
    return angles


def harmonic_angles(order: int) -> list[float]:
    """Return fundamental harmonic angles for ``order``."""

    n = int(order)
    if n <= 1:
        return []
    # Reduce redundant harmonics (e.g., even orders share bases with lower orders).
    # We keep only the angles in (0, 180] unique to this harmonic.
    fundamental: list[float] = []
    for k in range(1, (n // 2) + 1):
        if gcd(k, n) != 1:
            continue
        angle = 360.0 * k / n
        if angle <= 180.0:
            fundamental.append(angle)
    fundamental.sort()
    return fundamental


def combined_angles(aspects: Iterable[str], harmonics: Iterable[int]) -> list[float]:
    """Merge base aspects and harmonic-derived angles, deduplicated and sorted."""

    out = set(base_aspect_angles(aspects))
    for order in harmonics:
        for angle in harmonic_angles(int(order)):
            out.add(round(angle, 6))
    return sorted(out)


__all__ = [
    "BASE_ASPECTS",
    "base_aspect_angles",
    "harmonic_angles",
    "combined_angles",
]
