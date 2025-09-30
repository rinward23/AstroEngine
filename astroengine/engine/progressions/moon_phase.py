"""Progressed Moon phase helpers."""

from __future__ import annotations

from dataclasses import dataclass

from ...core.angles import normalize_degrees
from ...ephemeris.adapter import EphemerisAdapter
from ...providers.swisseph_adapter import SE_MOON, SE_SUN

__all__ = ["PhaseInfo", "progressed_phase"]


@dataclass(frozen=True)
class PhaseInfo:
    """Describe the progressed lunar phase."""

    angle_deg: float
    phase_name: str
    octile_index: int


_PHASE_NAMES = (
    "New Moon",
    "Waxing Crescent",
    "First Quarter",
    "Waxing Gibbous",
    "Full Moon",
    "Waning Gibbous",
    "Last Quarter",
    "Waning Crescent",
)


def _phase_name(angle: float) -> tuple[str, int]:
    normalized = normalize_degrees(angle)
    index = int((normalized + 22.5) // 45.0) % 8
    return _PHASE_NAMES[index], index


def progressed_phase(ephem: EphemerisAdapter, tP: object) -> PhaseInfo:
    """Return the lunar phase at the progressed instant ``tP``."""

    sun = ephem.sample(SE_SUN, tP)
    moon = ephem.sample(SE_MOON, tP)
    angle = normalize_degrees(moon.longitude - sun.longitude)
    name, index = _phase_name(angle)
    return PhaseInfo(angle_deg=angle, phase_name=name, octile_index=index)
