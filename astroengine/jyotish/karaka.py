"""Natural significator helpers."""

from __future__ import annotations

from collections.abc import Mapping

from ..ephemeris import BodyPosition
from .lords import karakas_for_house

__all__ = ["match_karakas"]


def match_karakas(
    house: int, positions: Mapping[str, BodyPosition]
) -> tuple[str, ...]:
    """Return karaka planets present in ``positions`` for ``house``."""

    wanted = karakas_for_house(house)
    return tuple(planet for planet in wanted if planet in positions)
