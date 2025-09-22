"""Planetary station detector backed by Swiss ephemeris speeds."""

from __future__ import annotations

        "mercury": swe.MERCURY,
        "venus": swe.VENUS,
        "mars": swe.MARS,
        "jupiter": swe.JUPITER,
        "saturn": swe.SATURN,
        "uranus": swe.URANUS,
        "neptune": swe.NEPTUNE,
        "pluto": swe.PLUTO,



def find_stations(
    start_jd: float,
    end_jd: float,
    bodies: Optional[Sequence[str]] = None,

