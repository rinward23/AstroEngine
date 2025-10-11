"""Mundane cycle search helpers backed by the dynamic aspect engine."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from typing import Any

from astroengine.core.aspects_plus.provider_wrappers import PositionProvider
from astroengine.core.aspects_plus.scan import Hit
from astroengine.core.aspects_plus.search import AspectSearch, TimeRange, search_time_range

DEFAULT_OUTER_BODIES: tuple[str, ...] = (
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
)

DEFAULT_OUTER_ASPECTS: tuple[str, ...] = (
    "conjunction",
    "opposition",
    "square",
    "trine",
    "sextile",
    "semisquare",
    "sesquisquare",
)


def search(
    *,
    start: datetime,
    end: datetime,
    position_provider: PositionProvider,
    bodies: Sequence[str] | None = None,
    aspects: Sequence[str] | None = None,
    harmonics: Sequence[int] | None = None,
    orb_policy: Mapping[str, Any] | None = None,
    pairs: Iterable[tuple[str, str]] | None = None,
    step_minutes: int = 720,
    include_antiscia: bool = False,
    antiscia_orb: float | None = None,
) -> list[Hit]:
    """Run an outer-planet cycle search over ``start``/``end``."""

    timerange = TimeRange(start=start, end=end, step_minutes=step_minutes)
    config = AspectSearch(
        objects=tuple(bodies) if bodies is not None else DEFAULT_OUTER_BODIES,
        aspects=tuple(aspects) if aspects is not None else DEFAULT_OUTER_ASPECTS,
        harmonics=tuple(harmonics or ()),
        orb_policy=orb_policy,
        pairs=pairs,
        include_antiscia=include_antiscia,
        antiscia_orb=antiscia_orb,
    )
    return search_time_range(position_provider=position_provider, timerange=timerange, config=config)


__all__ = ["search", "DEFAULT_OUTER_BODIES", "DEFAULT_OUTER_ASPECTS"]

