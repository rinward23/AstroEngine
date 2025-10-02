"""Helpers for mapping house lords, occupants, and karakas."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping

from ..ephemeris import BodyPosition, HousePositions
from .data import HOUSE_KARAKAS, SIGN_CO_LORDS, SIGN_LORDS
from .utils import house_signs, planet_house_map

__all__ = [
    "determine_house_lords",
    "house_occupants",
    "karakas_for_house",
]


def determine_house_lords(
    houses: HousePositions, *, include_co_lords: bool = True
) -> dict[int, tuple[str, ...]]:
    """Return the ruling planet sequence for each house."""

    mapping: dict[int, tuple[str, ...]] = {}
    for house, sign in house_signs(houses).items():
        lords = list(SIGN_LORDS.get(sign, ()))
        if include_co_lords and sign in SIGN_CO_LORDS:
            lords.extend(SIGN_CO_LORDS[sign])
        if lords:
            mapping[house] = tuple(dict.fromkeys(lords))
        else:
            mapping[house] = ()
    return mapping


def house_occupants(
    positions: Mapping[str, BodyPosition], houses: HousePositions
) -> dict[int, tuple[str, ...]]:
    """Return the occupants of each house sorted by zodiacal order."""

    house_map = planet_house_map(positions, houses)
    occupants: dict[int, list[tuple[float, str]]] = defaultdict(list)
    for name, position in positions.items():
        house_idx = house_map[name]
        occupants[house_idx].append((position.longitude % 360.0, name))
    sorted_map: dict[int, tuple[str, ...]] = {}
    for house_idx, values in occupants.items():
        values.sort(key=lambda item: item[0])
        sorted_map[house_idx] = tuple(name for _, name in values)
    return sorted_map


def karakas_for_house(house: int) -> tuple[str, ...]:
    """Return natural significators (karakas) for ``house``."""

    return HOUSE_KARAKAS.get(house, ())
