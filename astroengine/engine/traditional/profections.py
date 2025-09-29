"""Annual and monthly profection helpers."""

from __future__ import annotations

import math
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from ..traditional.dignities import sign_dignities
from ..traditional.models import ChartCtx, Interval, ProfectionSegment, ProfectionState

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

__all__ = [
    "current_profection",
    "profection_year_segments",
]


def _sign_index(longitude: float) -> int:
    return int(math.floor(longitude % 360.0 / 30.0)) % 12


def _sign_from_index(idx: int) -> str:
    return SIGN_SEQUENCE[idx % 12]


def _co_rulers(sign: str) -> dict[str, Any]:
    bundle = sign_dignities(sign)
    data: dict[str, Any] = {
        "exaltation": bundle.exaltation,
        "triplicity": {
            "day": bundle.triplicity_day,
            "night": bundle.triplicity_night,
            "participating": bundle.triplicity_participating,
        },
        "terms": tuple(
            {
                "ruler": span.ruler,
                "start_deg": span.start_deg,
                "end_deg": span.end_deg,
            }
            for span in bundle.bounds
        ),
        "faces": tuple(
            {
                "ruler": span.ruler,
                "start_deg": span.start_deg,
                "end_deg": span.end_deg,
            }
            for span in bundle.decans
        ),
    }
    return data


def _anniversary(moment: datetime, years: int) -> datetime:
    base = moment
    target_year = base.year + years
    try:
        return base.replace(year=target_year)
    except ValueError:
        if base.month == 2 and base.day == 29:
            return base.replace(year=target_year, month=2, day=28)
        return base.replace(year=target_year, day=min(base.day, 28))


def _years_elapsed(base: datetime, moment: datetime) -> int:
    years = max(0, moment.year - base.year)
    anniversary = _anniversary(base, years)
    if anniversary > moment:
        years -= 1
    return max(years, 0)


def _profection_house(asc_index: int, offset: int) -> tuple[int, str]:
    house = (offset % 12) + 1
    sign = _sign_from_index(asc_index + offset)
    return house, sign


def _house_of_body(chart: ChartCtx, body: str, asc_index: int) -> int | None:
    positions = chart.natal.positions
    key = body.capitalize()
    if key not in positions:
        return None
    sign_index = _sign_index(positions[key].longitude)
    house = ((sign_index - asc_index) % 12) + 1
    return house


def _year_lord(sign: str) -> str:
    return SIGN_RULERS.get(sign, "")


def _monthly_base_house(
    chart: ChartCtx,
    asc_index: int,
    year_house_offset: int,
    year_lord: str,
    mode: Literal["hellenistic", "medieval"],
) -> int:
    if mode == "hellenistic":
        return year_house_offset
    lord_house = _house_of_body(chart, year_lord, asc_index)
    if lord_house is None:
        return year_house_offset
    return lord_house - 1


def _monthly_segments(
    chart: ChartCtx,
    start: datetime,
    end: datetime,
    base_offset: int,
    asc_index: int,
    year_lord: str,
    mode: Literal["hellenistic", "medieval"],
    co_rulers: dict[str, Any],
) -> Iterable[ProfectionSegment]:
    span_seconds = (end - start).total_seconds()
    month_seconds = span_seconds / 12.0
    base_house_offset = _monthly_base_house(
        chart, asc_index, base_offset, year_lord, mode
    )
    for month in range(12):
        m_start = start + timedelta(seconds=month_seconds * month)
        if month == 11:
            m_end = end
        else:
            m_end = start + timedelta(seconds=month_seconds * (month + 1))
        house_offset = base_house_offset + month
        house, sign = _profection_house(asc_index, house_offset)
        yield ProfectionSegment(
            start=m_start,
            end=m_end,
            house=house,
            sign=sign,
            year_lord=_year_lord(sign),
            co_rulers=_co_rulers(sign),
            notes=(f"month={month+1}", f"mode={mode}"),
        )


def profection_year_segments(
    natal: ChartCtx,
    for_range: Interval,
    mode: Literal["hellenistic", "medieval"] = "hellenistic",
) -> list[ProfectionSegment]:
    """Return profection year and month segments intersecting ``for_range``."""

    chart = natal.natal
    base = chart.moment.astimezone(UTC)
    start = for_range.start.astimezone(UTC)
    end = for_range.end.astimezone(UTC)
    asc_index = _sign_index(chart.houses.ascendant)
    segments: list[ProfectionSegment] = []

    if end <= base:
        return []

    years_since_birth = _years_elapsed(base, start)
    year_start = _anniversary(base, years_since_birth)
    age = years_since_birth
    while year_start < end:
        next_anniversary = _anniversary(base, age + 1)
        year_end = min(next_anniversary, end)
        house_offset = age
        house, sign = _profection_house(asc_index, house_offset)
        year_lord = _year_lord(sign)
        co_rulers = _co_rulers(sign)
        segments.append(
            ProfectionSegment(
                start=year_start,
                end=year_end,
                house=house,
                sign=sign,
                year_lord=year_lord,
                co_rulers=co_rulers,
                notes=(f"age={age}",),
            )
        )
        segments.extend(
            _monthly_segments(
                natal,
                year_start,
                year_end,
                house_offset,
                asc_index,
                year_lord,
                mode,
                co_rulers,
            )
        )
        age += 1
        year_start = next_anniversary
        if year_start >= end:
            break
    return [seg for seg in segments if seg.end > start and seg.start < end]


def _active_month_segment(
    segments: Iterable[ProfectionSegment], moment: datetime
) -> ProfectionSegment | None:
    for segment in segments:
        if not segment.notes or not segment.notes[0].startswith("month="):
            continue
        if segment.start <= moment < segment.end:
            return segment
    return None


def current_profection(moment: datetime, natal: ChartCtx) -> ProfectionState:
    """Return the profected year/month state at ``moment``."""

    base = natal.natal.moment.astimezone(UTC)
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        raise ValueError("Moment must be timezone-aware")
    moment_utc = moment.astimezone(UTC)
    if moment_utc < base:
        raise ValueError("Moment precedes natal chart")
    years_since = _years_elapsed(base, moment_utc)
    year_start = _anniversary(base, years_since)
    year_end = _anniversary(base, years_since + 1)
    full_segments = profection_year_segments(
        natal, Interval(start=year_start, end=year_end)
    )
    year_segment = next((seg for seg in full_segments if seg.notes and seg.notes[0].startswith("age=")), None)
    if year_segment is None:
        raise ValueError("Unable to resolve profection year")
    month_segment = _active_month_segment(full_segments, moment_utc)
    if month_segment is None:
        raise ValueError("Unable to resolve profection month")
    return ProfectionState(
        moment=moment_utc,
        year_house=year_segment.house,
        year_sign=year_segment.sign,
        year_lord=year_segment.year_lord,
        month_house=month_segment.house,
        month_sign=month_segment.sign,
        month_lord=month_segment.year_lord,
        co_rulers=year_segment.co_rulers,
    )
