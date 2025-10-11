"""High-level aspect search helpers built on :mod:`astroengine.core.aspects_plus.scan`."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .provider_wrappers import PositionProvider
from .scan import Hit, TimeWindow, scan_time_range as _scan_time_range


@dataclass(frozen=True)
class TimeRange:
    """Parameters describing an inclusive time span for aspect searches."""

    start: datetime
    end: datetime
    step_minutes: int = 60

    def as_window(self) -> TimeWindow:
        """Return a :class:`~astroengine.core.aspects_plus.scan.TimeWindow` instance."""

        return TimeWindow(start=self.start, end=self.end)


@dataclass(frozen=True)
class AspectSearch:
    """Configuration block describing which combinations to scan."""

    objects: Sequence[str]
    aspects: Sequence[str] = field(default_factory=tuple)
    harmonics: Sequence[int] = field(default_factory=tuple)
    orb_policy: Mapping[str, Any] | None = None
    pairs: Iterable[tuple[str, str]] | None = None
    include_antiscia: bool = False
    antiscia_orb: float | None = None

    def normalized_pairs(self) -> Iterable[tuple[str, str]] | None:
        """Return a reusable iterable for pair restrictions if provided."""

        if self.pairs is None:
            return None
        return tuple(tuple(pair[:2]) for pair in self.pairs if pair and len(pair) >= 2)


def search_time_range(
    *,
    position_provider: PositionProvider,
    timerange: TimeRange,
    config: AspectSearch,
) -> list[Hit]:
    """Execute a time-ranged aspect search using ``scan_time_range`` primitives."""

    if not config.objects:
        raise ValueError("config.objects must contain at least one body")

    window = timerange.as_window()
    hits = _scan_time_range(
        objects=tuple(config.objects),
        window=window,
        position_provider=position_provider,
        aspects=tuple(config.aspects),
        harmonics=tuple(config.harmonics),
        orb_policy=config.orb_policy,
        pairs=config.normalized_pairs(),
        step_minutes=timerange.step_minutes,
        include_antiscia=config.include_antiscia,
        antiscia_orb=config.antiscia_orb,
    )
    return hits


def search_pair(
    *,
    position_provider: PositionProvider,
    body_a: str,
    body_b: str,
    timerange: TimeRange,
    aspects: Sequence[str],
    harmonics: Sequence[int] | None = None,
    orb_policy: Mapping[str, Any] | None = None,
    include_antiscia: bool = False,
    antiscia_orb: float | None = None,
) -> list[Hit]:
    """Convenience wrapper for scanning a single pair of bodies."""

    pair_config = AspectSearch(
        objects=(body_a, body_b),
        aspects=tuple(aspects),
        harmonics=tuple(harmonics or ()),
        orb_policy=orb_policy,
        pairs=((body_a, body_b),),
        include_antiscia=include_antiscia,
        antiscia_orb=antiscia_orb,
    )
    return search_time_range(
        position_provider=position_provider,
        timerange=timerange,
        config=pair_config,
    )


__all__ = ["TimeRange", "AspectSearch", "search_time_range", "search_pair"]

