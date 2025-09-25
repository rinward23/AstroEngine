"""Harmonic chart utilities."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .natal import NatalChart

__all__ = ["HarmonicPosition", "HarmonicChart", "compute_harmonic_chart"]


@dataclass(frozen=True)
class HarmonicPosition:
    """Derived harmonic position along with the base longitude."""

    body: str
    base_longitude: float
    harmonic_longitude: float


@dataclass(frozen=True)
class HarmonicChart:
    """Collection of harmonic positions computed from a natal chart."""

    harmonic: int
    positions: Mapping[str, HarmonicPosition]


def _wrap(angle: float) -> float:
    angle %= 360.0
    return angle if angle >= 0 else angle + 360.0


def compute_harmonic_chart(
    natal_chart: NatalChart,
    harmonic: int,
    *,
    bodies: Sequence[str] | None = None,
) -> HarmonicChart:
    """Return harmonic chart positions derived from ``natal_chart``."""

    if harmonic <= 0:
        raise ValueError("harmonic must be positive")

    if bodies is None:
        selected = set(natal_chart.positions.keys())
    else:
        selected = {body for body in bodies if body in natal_chart.positions}
        if not selected:
            raise ValueError("No overlapping bodies for harmonic chart computation")

    positions: dict[str, HarmonicPosition] = {}
    for body in sorted(selected):
        base_long = natal_chart.positions[body].longitude
        harmonic_long = _wrap(base_long * harmonic)
        positions[body] = HarmonicPosition(
            body=body,
            base_longitude=base_long,
            harmonic_longitude=harmonic_long,
        )

    return HarmonicChart(harmonic=harmonic, positions=positions)
