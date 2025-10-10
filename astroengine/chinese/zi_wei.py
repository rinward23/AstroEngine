"""Zi Wei Dou Shu palace and star placement utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, tzinfo
from typing import Mapping, Sequence

from ..chart.natal import ChartLocation
from .constants import EARTHLY_BRANCHES, EarthlyBranch
from .sexagenary import (
    SexagenaryCycleEntry,
    day_cycle_index,
    hour_cycle_index,
    month_cycle_index,
    sexagenary_entry_for_index,
)

PALACE_NAMES: Sequence[str] = (
    "Life",
    "Siblings",
    "Spouse",
    "Children",
    "Wealth",
    "Health",
    "Travel",
    "Friends",
    "Career",
    "Property",
    "Mental",
    "Parents",
)

MAJOR_STARS: Sequence[str] = (
    "Zi Wei",
    "Tian Ji",
    "Tai Yang",
    "Wu Qu",
    "Tian Tong",
    "Lian Zhen",
    "Tian Fu",
    "Tai Yin",
)

SUPPORT_STARS: Sequence[str] = (
    "Tian Xiang",
    "Tian Liang",
    "Qi Sha",
    "Po Jun",
)


@dataclass(frozen=True)
class ZiWeiStar:
    """Representation of a Zi Wei star and its qualitative grouping."""

    name: str
    category: str  # e.g., "major", "support"


@dataclass(frozen=True)
class ZiWeiPalace:
    """One of the twelve palaces (gong) in Zi Wei Dou Shu."""

    name: str
    branch: EarthlyBranch
    stars: Sequence[ZiWeiStar]


@dataclass(frozen=True)
class ZiWeiChart:
    """Computed palace and star distribution for a moment."""

    moment: datetime
    location: ChartLocation | None
    timezone: tzinfo | None
    palaces: Sequence[ZiWeiPalace]
    life_palace_index: int
    body_palace_index: int
    provenance: Mapping[str, object]

    def palace_by_name(self, name: str) -> ZiWeiPalace:
        for palace in self.palaces:
            if palace.name.lower() == name.lower():
                return palace
        raise KeyError(name)


_DEFENSIVE_OFFSET = 4  # Distance from Life to Body palace.


def _life_palace_index(month_entry: SexagenaryCycleEntry, hour_entry: SexagenaryCycleEntry) -> int:
    return (month_entry.branch_index + hour_entry.branch_index) % 12


def _star_offsets(day_entry: SexagenaryCycleEntry) -> Mapping[str, int]:
    base = day_entry.branch_index
    offsets: dict[str, int] = {
        "Zi Wei": 0,
        "Tian Ji": 1,
        "Tai Yang": 2,
        "Wu Qu": 3,
        "Tian Tong": 4,
        "Lian Zhen": 5,
        "Tian Fu": 6,
        "Tai Yin": 7,
        "Tian Xiang": 8,
        "Tian Liang": 9,
        "Qi Sha": 10,
        "Po Jun": 11,
    }
    return {name: (base + offset) % 12 for name, offset in offsets.items()}


def _build_palaces(star_offsets: Mapping[str, int]) -> Sequence[list[ZiWeiStar]]:
    palaces: list[list[ZiWeiStar]] = [[] for _ in range(12)]
    for star in MAJOR_STARS:
        palaces[star_offsets[star]].append(ZiWeiStar(star, "major"))
    for star in SUPPORT_STARS:
        palaces[star_offsets[star]].append(ZiWeiStar(star, "support"))
    return palaces


def compute_zi_wei_chart(
    moment: datetime,
    location: ChartLocation | None = None,
    *,
    timezone: tzinfo | None = None,
) -> ZiWeiChart:
    """Compute a simplified Zi Wei Dou Shu chart for ``moment``."""

    month_entry = sexagenary_entry_for_index(month_cycle_index(moment, tz=timezone))
    hour_entry = sexagenary_entry_for_index(hour_cycle_index(moment, tz=timezone))
    day_entry = sexagenary_entry_for_index(day_cycle_index(moment, tz=timezone))

    life_index = _life_palace_index(month_entry, hour_entry)
    body_index = (life_index + _DEFENSIVE_OFFSET) % 12

    star_offsets = _star_offsets(day_entry)
    palace_star_lists = _build_palaces(star_offsets)

    palaces: list[ZiWeiPalace] = []
    for idx, name in enumerate(PALACE_NAMES):
        palaces.append(
            ZiWeiPalace(
                name=name,
                branch=EARTHLY_BRANCHES[idx],
                stars=tuple(palace_star_lists[idx]),
            )
        )

    provenance = {
        "timezone": str(timezone) if timezone else str(moment.tzinfo or "UTC"),
        "life_palace_branch": EARTHLY_BRANCHES[life_index].name,
        "day_cycle_index": day_entry.index,
    }

    return ZiWeiChart(
        moment=moment,
        location=location,
        timezone=timezone or moment.tzinfo,
        palaces=tuple(palaces),
        life_palace_index=life_index,
        body_palace_index=body_index,
        provenance=provenance,
    )


__all__ = [
    "PALACE_NAMES",
    "MAJOR_STARS",
    "SUPPORT_STARS",
    "ZiWeiStar",
    "ZiWeiPalace",
    "ZiWeiChart",
    "compute_zi_wei_chart",
]
