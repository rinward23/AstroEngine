"""Profection time-lord periods (annual, monthly, daily)."""

from __future__ import annotations

from datetime import datetime
from typing import List

from ..events import ProfectionEvent
from .context import TimelordContext
from .models import TimelordPeriod
from .utils import clamp_end, isoformat

__all__ = [
    "SIGN_RULERS",
    "generate_profection_periods",
    "annual_profections",
]

SIGN_SEQUENCE = (
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

SIGN_RULERS = {
    "aries": "mars",
    "taurus": "venus",
    "gemini": "mercury",
    "cancer": "moon",
    "leo": "sun",
    "virgo": "mercury",
    "libra": "venus",
    "scorpio": "mars",
    "sagittarius": "jupiter",
    "capricorn": "saturn",
    "aquarius": "saturn",
    "pisces": "jupiter",
}


def _days_in_month(year: int, month: int) -> int:
    if month == 2:
        leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
        return 29 if leap else 28
    if month in {1, 3, 5, 7, 8, 10, 12}:
        return 31
    return 30


def _add_years(moment: datetime, years: int) -> datetime:
    target_year = moment.year + years
    try:
        return moment.replace(year=target_year)
    except ValueError:
        # Handle 29 February → 28 February on non-leap years
        return moment.replace(year=target_year, month=2, day=28)


def _add_months(moment: datetime, months: int) -> datetime:
    total = (moment.month - 1) + months
    year = moment.year + total // 12
    month = (total % 12) + 1
    day = min(moment.day, _days_in_month(year, month))
    return moment.replace(year=year, month=month, day=day)


def _house_index(asc_longitude: float) -> int:
    return int(asc_longitude % 360.0 // 30.0)


def _sign_for_house(asc_index: int, offset: int) -> str:
    return SIGN_SEQUENCE[(asc_index + offset) % len(SIGN_SEQUENCE)]


def _profection_periods(context: TimelordContext, until: datetime) -> list[TimelordPeriod]:
    asc_index = _house_index(context.chart.houses.ascendant)
    periods: list[TimelordPeriod] = []
    year = 0
    start = context.moment
    while start < until:
        next_year = _add_years(context.moment, year + 1)
        end = clamp_end(start, next_year)
        sign = _sign_for_house(asc_index, year)
        ruler = SIGN_RULERS[sign]
        metadata = {"house": (year % 12) + 1, "sign": sign}
        periods.append(
            TimelordPeriod(
                system="profections",
                level="annual",
                ruler=ruler,
                start=start,
                end=end,
                metadata=metadata,
            )
        )
        _monthly_periods(periods, start, end, asc_index, year)
        start = end
        year += 1
        if start >= until:
            break
    return periods


def _monthly_periods(
    periods: list[TimelordPeriod],
    year_start: datetime,
    year_end: datetime,
    asc_index: int,
    year_offset: int,
) -> None:
    for month in range(12):
        start = _add_months(year_start, month)
        end = clamp_end(start, _add_months(year_start, month + 1))
        if end > year_end:
            end = year_end
        if end <= start:
            continue
        house_offset = year_offset + month
        sign = _sign_for_house(asc_index, house_offset)
        ruler = SIGN_RULERS[sign]
        metadata = {
            "house": (house_offset % 12) + 1,
            "sign": sign,
        }
        periods.append(
            TimelordPeriod(
                system="profections",
                level="monthly",
                ruler=ruler,
                start=start,
                end=end,
                metadata=metadata,
            )
        )
        _daily_periods(periods, start, end, asc_index, house_offset)


def _daily_periods(
    periods: list[TimelordPeriod],
    month_start: datetime,
    month_end: datetime,
    asc_index: int,
    offset: int,
) -> None:
    month_span = month_end - month_start
    if month_span.total_seconds() <= 0:
        return
    day_length = month_span / 30
    for day in range(30):
        start = month_start + day_length * day
        end = month_start + day_length * (day + 1)
        end = clamp_end(start, end)
        house_offset = offset + day
        sign = _sign_for_house(asc_index, house_offset)
        ruler = SIGN_RULERS[sign]
        metadata = {
            "house": (house_offset % 12) + 1,
            "sign": sign,
        }
        periods.append(
            TimelordPeriod(
                system="profections",
                level="daily",
                ruler=ruler,
                start=start,
                end=end,
                metadata=metadata,
            )
        )


def generate_profection_periods(
    context: TimelordContext,
    until: datetime,
) -> list[TimelordPeriod]:
    """Return annual/monthly/daily profection periods up to ``until``."""

    return _profection_periods(context, until)


def annual_profections(
    natal_ts: str,
    start_ts: str,
    end_ts: str,
    lat: float,
    lon: float,
) -> List[ProfectionEvent]:
    """Backwards-compatible annual profection API returning events."""

    from .utils import parse_iso
    from .context import build_context

    natal_moment = parse_iso(natal_ts)
    context = build_context(natal_moment, lat, lon)
    start = parse_iso(start_ts)
    end = parse_iso(end_ts)
    periods = _profection_periods(context, end)
    events: List[ProfectionEvent] = []
    for period in periods:
        if period.level != "annual":
            continue
        if period.end <= start or period.start >= end:
            continue
        events.append(
            ProfectionEvent(
                ts=isoformat(period.start),
                jd=context.adapter.julian_day(period.start),
                method="annual",
                house=int(period.metadata["house"]),
                ruler=period.ruler,
                end_ts=isoformat(period.end),
                midpoint_ts=isoformat(period.midpoint()),
            )
        )
    return events
