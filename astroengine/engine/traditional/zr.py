"""Zodiacal releasing timelines with loosing of the bond support."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from .models import ZRPeriod, ZRTimeline
from .profections import SIGN_RULERS

__all__ = [
    "PERIOD_YEARS",
    "apply_loosing_of_bond",
    "flag_peaks_fortune",
    "zr_periods",
]

SIGN_ORDER = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)

PERIOD_YEARS = {
    "Aries": 15.0,
    "Taurus": 8.0,
    "Gemini": 20.0,
    "Cancer": 25.0,
    "Leo": 19.0,
    "Virgo": 20.0,
    "Libra": 8.0,
    "Scorpio": 15.0,
    "Sagittarius": 12.0,
    "Capricorn": 27.0,
    "Aquarius": 30.0,
    "Pisces": 12.0,
}

TOTAL_UNITS = sum(PERIOD_YEARS.values())
YEAR_DAYS = 365.2425

MODALITY = {
    "Aries": "cardinal",
    "Cancer": "cardinal",
    "Libra": "cardinal",
    "Capricorn": "cardinal",
    "Taurus": "fixed",
    "Leo": "fixed",
    "Scorpio": "fixed",
    "Aquarius": "fixed",
    "Gemini": "mutable",
    "Virgo": "mutable",
    "Sagittarius": "mutable",
    "Pisces": "mutable",
}


def _normalize_sign(sign: str) -> str:
    key = sign.strip().lower()
    for candidate in SIGN_ORDER:
        if candidate.lower() == key:
            return candidate
    raise ValueError(f"Unknown zodiac sign: {sign}")


def _next_sign(current: str, previous: str | None) -> tuple[str, tuple[str, str] | None]:
    idx = SIGN_ORDER.index(current)
    default_next = SIGN_ORDER[(idx + 1) % len(SIGN_ORDER)]
    if current == "Cancer" and previous != "Capricorn":
        return "Capricorn", ("Cancer", "Capricorn")
    if current == "Capricorn" and previous != "Cancer":
        return "Cancer", ("Capricorn", "Cancer")
    return default_next, None


def _build_level(
    level: int,
    start: datetime,
    end: datetime,
    start_sign: str,
    max_level: int,
) -> list[ZRPeriod]:
    periods: list[ZRPeriod] = []
    current_sign = start_sign
    previous_sign: str | None = None
    pending_lb: tuple[str, str] | None = None
    cursor = start
    epsilon = timedelta(seconds=1)
    while cursor < end - epsilon:
        if level == 1:
            span_days = PERIOD_YEARS[current_sign] * YEAR_DAYS
        else:
            parent_days = (end - start).total_seconds() / 86400.0
            span_days = parent_days * (PERIOD_YEARS[current_sign] / TOTAL_UNITS)
        next_end = cursor + timedelta(days=span_days)
        if next_end > end:
            next_end = end
        lb_flag = False
        lb_from: str | None = None
        lb_to: str | None = None
        if pending_lb and pending_lb[1] == current_sign:
            lb_flag = True
            lb_from, lb_to = pending_lb
            pending_lb = None
        period = ZRPeriod(
            level=level,
            start=cursor,
            end=next_end,
            sign=current_sign,
            ruler=SIGN_RULERS[current_sign.lower()],
            lb=lb_flag,
            lb_from=lb_from,
            lb_to=lb_to,
            metadata={},
        )
        periods.append(period)
        if level < max_level:
            sub_periods = _build_level(level + 1, cursor, next_end, current_sign, max_level)
            periods.extend(sub_periods)
        next_sign, lob = _next_sign(current_sign, previous_sign)
        if lob:
            pending_lb = lob
        previous_sign = current_sign
        current_sign = next_sign
        cursor = next_end
        if cursor >= end:
            break
    return periods


def zr_periods(
    lot_sign: str,
    start: datetime,
    end: datetime,
    *,
    levels: int = 2,
    source: Literal["Spirit", "Fortune"] = "Spirit",
) -> ZRTimeline:
    """Compute zodiacal releasing periods for ``lot_sign`` between ``start`` and ``end``."""

    if levels < 1 or levels > 4:
        raise ValueError("levels must be between 1 and 4")
    if start.tzinfo is None or start.tzinfo.utcoffset(start) is None:
        raise ValueError("start must be timezone-aware")
    if end.tzinfo is None or end.tzinfo.utcoffset(end) is None:
        raise ValueError("end must be timezone-aware")
    if end <= start:
        raise ValueError("end must be after start")
    lot = _normalize_sign(lot_sign)
    start_utc = start.astimezone(UTC)
    end_utc = end.astimezone(UTC)
    levels_map: dict[int, list[ZRPeriod]] = {level: [] for level in range(1, levels + 1)}
    level_periods = _build_level(1, start_utc, end_utc, lot, levels)
    for period in level_periods:
        if period.level <= levels:
            levels_map[period.level].append(period)
    packed = {key: tuple(value) for key, value in levels_map.items()}
    return ZRTimeline(levels=packed, lot=lot, source=source)


def apply_loosing_of_bond(timeline: ZRTimeline) -> ZRTimeline:
    """Return a timeline with Loosing of the Bond metadata normalised."""

    updated: dict[int, list[ZRPeriod]] = {}
    for level, periods in timeline.levels.items():
        updated[level] = []
        for period in periods:
            updated[level].append(period)
    timeline.levels = {key: tuple(value) for key, value in updated.items()}
    return timeline


def flag_peaks_fortune(timeline: ZRTimeline, fortune_sign: str) -> None:
    """Annotate level-1 periods that coincide with Lot of Fortune peaks."""

    fortune = _normalize_sign(fortune_sign)
    fortune_modality = MODALITY[fortune]
    updated: list[ZRPeriod] = []
    for period in timeline.levels.get(1, ()):  # type: ignore[arg-type]
        metadata = dict(period.metadata)
        peak: str | None = None
        if period.sign == fortune:
            peak = "major"
        elif MODALITY.get(period.sign) == fortune_modality:
            peak = "moderate"
        if peak:
            metadata["peak"] = peak
        updated.append(
            ZRPeriod(
                level=period.level,
                start=period.start,
                end=period.end,
                sign=period.sign,
                ruler=period.ruler,
                lb=period.lb,
                lb_from=period.lb_from,
                lb_to=period.lb_to,
                metadata=metadata,
            )
        )
    if updated:
        timeline.levels = dict(timeline.levels)
        timeline.levels[1] = tuple(updated)
