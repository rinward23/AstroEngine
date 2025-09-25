"""Zodiacal releasing calculators for Lots of Spirit and Fortune."""

from __future__ import annotations

import itertools
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from .context import TimelordContext
from .models import TimelordPeriod
from .utils import clamp_end

__all__ = [
    "ZODIAC_SIGNS",
    "SIGN_DURATIONS",
    "generate_zodiacal_releasing",
]

ZODIAC_SIGNS: Sequence[str] = (
    "aries",
    "taurus",
    "gemini",
    "cancer",
    "leo",
    "virgo",
    "libra",
    "scorpio",
    "sagittarius",
    "capricorn",
    "aquarius",
    "pisces",
)

SIGN_DURATIONS: dict[str, float] = {
    "aries": 15.0,
    "taurus": 8.0,
    "gemini": 20.0,
    "cancer": 25.0,
    "leo": 19.0,
    "virgo": 20.0,
    "libra": 8.0,
    "scorpio": 15.0,
    "sagittarius": 12.0,
    "capricorn": 27.0,
    "aquarius": 30.0,
    "pisces": 12.0,
}

TOTAL_UNITS = sum(SIGN_DURATIONS.values())
ZR_YEAR_DAYS = 365.25


@dataclass(frozen=True)
class _ReleaseSeed:
    sign: str
    duration_units: float


def _zodiac_cycle(start_sign: str) -> Iterable[_ReleaseSeed]:
    if start_sign not in SIGN_DURATIONS:
        raise ValueError(f"Unknown sign: {start_sign}")
    index = ZODIAC_SIGNS.index(start_sign)
    while True:
        sign = ZODIAC_SIGNS[index % len(ZODIAC_SIGNS)]
        yield _ReleaseSeed(sign=sign, duration_units=SIGN_DURATIONS[sign])
        index += 1


def _sign_from_longitude(longitude: float) -> str:
    idx = int(longitude % 360.0 // 30.0)
    return ZODIAC_SIGNS[idx]


def _lot_longitudes(context: TimelordContext) -> tuple[float, float]:
    asc = context.chart.houses.ascendant
    sun = context.chart.positions["Sun"].longitude
    moon = context.chart.positions["Moon"].longitude
    day_chart = ((sun - asc) % 360.0) < 180.0
    if day_chart:
        fortune = (asc + moon - sun) % 360.0
        spirit = (asc + sun - moon) % 360.0
    else:
        fortune = (asc + sun - moon) % 360.0
        spirit = (asc + moon - sun) % 360.0
    return spirit, fortune


def _level_label(level: int) -> str:
    return {1: "l1", 2: "l2", 3: "l3", 4: "l4"}.get(level, f"l{level}")


def _subdivide(
    periods: list[TimelordPeriod],
    start: datetime,
    end: datetime,
    sign: str,
    level: int,
    max_level: int,
) -> None:
    if level > max_level:
        return
    total_days = (end - start).total_seconds() / 86400.0
    cursor = start
    accumulator = 0.0
    seeds = list(itertools.islice(_zodiac_cycle(sign), len(ZODIAC_SIGNS)))
    for idx, seed in enumerate(seeds):
        accumulator += seed.duration_units
        if idx == len(seeds) - 1:
            sub_end = end
        else:
            fraction = accumulator / TOTAL_UNITS
            sub_end = start + timedelta(days=total_days * fraction)
        metadata = {"sign": seed.sign}
        if seed.sign in {"cancer", "capricorn"}:
            metadata["loosing"] = True
        periods.append(
            TimelordPeriod(
                system="zodiacal_releasing",
                level=_level_label(level),
                ruler=seed.sign,
                start=cursor,
                end=sub_end,
                metadata=metadata,
            )
        )
        if level < max_level:
            _subdivide(periods, cursor, sub_end, seed.sign, level + 1, max_level)
        cursor = sub_end


def generate_zodiacal_releasing(
    context: TimelordContext,
    until: datetime,
    *,
    lot: str = "spirit",
    levels: int = 4,
) -> list[TimelordPeriod]:
    """Return zodiacal releasing periods for ``lot`` up to ``until``."""

    spirit_lon, fortune_lon = _lot_longitudes(context)
    lot_lon = spirit_lon if lot == "spirit" else fortune_lon
    start_sign = _sign_from_longitude(lot_lon)
    periods: list[TimelordPeriod] = []
    start = context.moment
    cycle = _zodiac_cycle(start_sign)
    while start < until:
        seed = next(cycle)
        length_days = seed.duration_units * ZR_YEAR_DAYS
        end = clamp_end(start, start + timedelta(days=length_days))
        metadata = {"sign": seed.sign}
        if seed.sign in {"cancer", "capricorn"}:
            metadata["loosing"] = True
        periods.append(
            TimelordPeriod(
                system="zodiacal_releasing",
                level="l1",
                ruler=seed.sign,
                start=start,
                end=end,
                metadata=metadata,
            )
        )
        if levels >= 2:
            _subdivide(periods, start, end, seed.sign, 2, levels)
        start = end
        if start >= until:
            break
    return periods
