"""Vimśottarī Daśā calculator supporting maha → praan levels."""

from __future__ import annotations

import itertools
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from .context import TimelordContext
from .models import TimelordPeriod
from .utils import clamp_end

__all__ = [
    "NAKSHATRA_DEGREES",
    "VIMSHOTTARI_SEQUENCE",
    "generate_vimshottari_periods",
]

_LEVEL_BY_DEPTH = {
    1: "maha",
    2: "antar",
    3: "pratyantar",
    4: "sookshma",
    5: "praan",
}

NAKSHATRA_DEGREES = 360.0 / 27.0

VIMSHOTTARI_SEQUENCE: list[tuple[str, float]] = [
    ("ketu", 7.0),
    ("venus", 20.0),
    ("sun", 6.0),
    ("moon", 10.0),
    ("mars", 7.0),
    ("rahu", 18.0),
    ("jupiter", 16.0),
    ("saturn", 19.0),
    ("mercury", 17.0),
]

TOTAL_YEARS = sum(duration for _, duration in VIMSHOTTARI_SEQUENCE)
VIMSHOTTARI_YEAR_DAYS = 365.25

NAKSHATRA_LORDS: list[tuple[str, str]] = [
    ("Ashwini", "ketu"),
    ("Bharani", "venus"),
    ("Krittika", "sun"),
    ("Rohini", "moon"),
    ("Mrigashira", "mars"),
    ("Ardra", "rahu"),
    ("Punarvasu", "jupiter"),
    ("Pushya", "saturn"),
    ("Ashlesha", "mercury"),
    ("Magha", "ketu"),
    ("Purva Phalguni", "venus"),
    ("Uttara Phalguni", "sun"),
    ("Hasta", "moon"),
    ("Chitra", "mars"),
    ("Swati", "rahu"),
    ("Vishakha", "jupiter"),
    ("Anuradha", "saturn"),
    ("Jyeshtha", "mercury"),
    ("Mula", "ketu"),
    ("Purva Ashadha", "venus"),
    ("Uttara Ashadha", "sun"),
    ("Shravana", "moon"),
    ("Dhanishta", "mars"),
    ("Shatabhisha", "rahu"),
    ("Purva Bhadrapada", "jupiter"),
    ("Uttara Bhadrapada", "saturn"),
    ("Revati", "mercury"),
]

_SEQUENCE_INDEX = {name: idx for idx, (name, _) in enumerate(VIMSHOTTARI_SEQUENCE)}


@dataclass(frozen=True)
class _PeriodSeed:
    ruler: str
    duration_years: float


def _cycle(start_ruler: str) -> Iterable[_PeriodSeed]:
    idx = _SEQUENCE_INDEX[start_ruler]
    sequence = VIMSHOTTARI_SEQUENCE
    while True:
        ruler, duration = sequence[idx % len(sequence)]
        yield _PeriodSeed(ruler=ruler, duration_years=duration)
        idx += 1


def _sidereal_moon_longitude(context: TimelordContext) -> float:
    moon = context.chart.positions["Moon"]
    ayanamsa = context.adapter.ayanamsa(context.chart.julian_day)
    return (moon.longitude - ayanamsa) % 360.0


def _nakshatra_index(longitude: float) -> int:
    return int(longitude // NAKSHATRA_DEGREES)


def _nakshatra_fraction(longitude: float) -> float:
    return (longitude % NAKSHATRA_DEGREES) / NAKSHATRA_DEGREES


def _maha_periods(
    context: TimelordContext,
    until: datetime,
    *,
    levels: int,
) -> list[TimelordPeriod]:
    periods: list[TimelordPeriod] = []
    moon_sidereal = _sidereal_moon_longitude(context)
    idx = _nakshatra_index(moon_sidereal)
    nakshatra_name, ruler = NAKSHATRA_LORDS[idx]
    fraction = _nakshatra_fraction(moon_sidereal)
    remaining_fraction = 1.0 - fraction
    start = context.moment
    cycle = _cycle(ruler)

    first = True
    while start < until:
        seed = next(cycle)
        duration_years = seed.duration_years
        if first:
            length_years = duration_years * remaining_fraction
            first = False
        else:
            length_years = duration_years
        length_days = length_years * VIMSHOTTARI_YEAR_DAYS
        end = clamp_end(start, start + timedelta(days=length_days))
        metadata = {"nakshatra": nakshatra_name} if not periods else {}
        periods.append(
            TimelordPeriod(
                system="vimshottari",
                level="maha",
                ruler=seed.ruler,
                start=start,
                end=end,
                metadata=metadata,
            )
        )
        if levels >= 2:
            _subdivide(periods, start, end, seed.ruler, 2, levels)
        start = end
        if start >= until:
            break
    return periods


def _subdivide(
    periods: list[TimelordPeriod],
    start: datetime,
    end: datetime,
    ruler: str,
    level: int,
    max_level: int,
) -> None:
    total_days = (end - start).total_seconds() / 86400.0
    cursor = start
    accumulator = 0.0
    seq = list(itertools.islice(_cycle(ruler), len(VIMSHOTTARI_SEQUENCE)))
    for idx, seed in enumerate(seq):
        accumulator += seed.duration_years
        if idx == len(seq) - 1:
            sub_end = end
        else:
            fraction = accumulator / TOTAL_YEARS
            sub_end = start + timedelta(days=total_days * fraction)
        level_name = _LEVEL_BY_DEPTH.get(level, f"level{level}")
        metadata = {"parent": ruler}
        periods.append(
            TimelordPeriod(
                system="vimshottari",
                level=level_name,
                ruler=seed.ruler,
                start=cursor,
                end=sub_end,
                metadata=metadata,
            )
        )
        if level < max_level:
            _subdivide(periods, cursor, sub_end, seed.ruler, level + 1, max_level)
        cursor = sub_end


def generate_vimshottari_periods(
    context: TimelordContext,
    until: datetime,
    *,
    levels: int = 5,
) -> list[TimelordPeriod]:
    """Return Vimśottarī periods covering ``context.moment`` → ``until``."""

    if levels < 1:
        raise ValueError("levels must be >= 1")
    if levels > len(_LEVEL_BY_DEPTH):
        raise ValueError(
            f"levels must be <= {len(_LEVEL_BY_DEPTH)} for Vimśottarī calculations"
        )
    return _maha_periods(context, until, levels=levels)
