"""Utilities for computing base aspect and harmonic angles.

The helpers defined here allow other modules to map between canonical aspect
names and their corresponding angles, generate harmonic series angles, and
combine both sources into a single deduplicated list.  The utilities stay
within the 0°–180° range which matches the expectations of the downstream
aspect matching logic.
"""

from __future__ import annotations

from typing import Dict, Iterable, List

# Canonical base aspect angles (degrees)
BASE_ASPECTS: Dict[str, float] = {
    "conjunction": 0.0,
    "opposition": 180.0,
    "square": 90.0,
    "trine": 120.0,
    "sextile": 60.0,
    "quincunx": 150.0,
    "semisquare": 45.0,
    "sesquisquare": 135.0,
    "quintile": 72.0,
    "biquintile": 144.0,
}

EPS = 1e-6


def _dedupe_sorted(values: Iterable[float]) -> List[float]:
    """Return the sorted unique values with tolerance-based deduplication."""

    out: List[float] = []
    for value in sorted(values):
        if not out or abs(value - out[-1]) > EPS:
            out.append(value)
    return out


def base_aspect_angles(names: Iterable[str]) -> List[float]:
    """Map aspect names to exact angles in degrees.

    Unknown aspect names are ignored. The returned list is sorted and contains
    unique angles.
    """

    values: List[float] = []
    for name in names:
        key = str(name).lower()
        if key in BASE_ASPECTS:
            values.append(float(BASE_ASPECTS[key]))
    return _dedupe_sorted(values)


def harmonic_angles(h: int) -> List[float]:
    """Return harmonic angles for step Δ=360/h within (0, 180].

    The generated angles correspond to k * Δ for k=1..⌊h/2⌋. Values are clipped
    to 180 when numerical precision errors make them extremely close to the
    boundary. The resulting list is sorted and deduplicated.
    """

    if h <= 1:
        return []
    step = 360.0 / float(h)
    values = [k * step for k in range(1, (h // 2) + 1)]
    values = [180.0 if abs(value - 180.0) <= 1e-9 else value for value in values]
    return _dedupe_sorted(values)


def combined_angles(aspects: Iterable[str], harmonics: Iterable[int]) -> List[float]:
    """Merge base aspect and harmonic angles into a single sorted list."""

    angles: List[float] = []
    angles.extend(base_aspect_angles(aspects))
    for harmonic in harmonics:
        angles.extend(harmonic_angles(int(harmonic)))
    return _dedupe_sorted(angles)


__all__ = [
    "BASE_ASPECTS",
    "base_aspect_angles",
    "harmonic_angles",
    "combined_angles",
]
