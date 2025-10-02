"""Utility helpers for Jyotish calculations."""

from __future__ import annotations

import math
from collections.abc import Mapping

from ..ephemeris import BodyPosition, HousePositions
from ..detectors.ingresses import sign_index, sign_name

__all__ = [
    "norm360",
    "circular_separation",
    "degree_in_sign",
    "house_index_for",
    "house_signs",
    "planet_house_map",
]


def norm360(value: float) -> float:
    """Normalise ``value`` to the range [0, 360)."""

    return value % 360.0


def circular_separation(a: float, b: float) -> float:
    """Return the smallest angular separation between ``a`` and ``b`` degrees."""

    diff = abs((a - b + 180.0) % 360.0 - 180.0)
    return diff


def degree_in_sign(longitude: float) -> float:
    """Return the degree within the active sign (0–30)."""

    return norm360(longitude) % 30.0


def house_index_for(longitude: float, houses: HousePositions) -> int:
    """Return the 1-indexed house position for ``longitude`` given ``houses``.

    The logic matches the Swiss Ephemeris definition used in SolarFire.  It is
    essentially a direct copy of the private helper in
    :mod:`astroengine.detectors.ingresses` but exposed here so Jyotish scoring
    can reason about occupants without importing private symbols.
    """

    cusps = list(houses.cusps[:12])
    values = [norm360(value) for value in cusps]
    lon = norm360(longitude)
    for idx in range(12):
        start = values[idx]
        end = values[(idx + 1) % 12]
        if start <= end:
            if start <= lon < end:
                return idx + 1
        else:
            if lon >= start or lon < end:
                return idx + 1
    return 12


def house_signs(houses: HousePositions) -> dict[int, str]:
    """Return the zodiac sign for each house cusp."""

    mapping: dict[int, str] = {}
    for idx, cusp in enumerate(houses.cusps[:12], start=1):
        mapping[idx] = sign_name(sign_index(cusp))
    return mapping


def planet_house_map(
    positions: Mapping[str, BodyPosition], houses: HousePositions
) -> dict[str, int]:
    """Return the house index for each planet in ``positions``."""

    return {
        name: house_index_for(position.longitude, houses)
        for name, position in positions.items()
    }
