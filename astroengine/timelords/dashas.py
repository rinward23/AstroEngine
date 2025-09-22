"""Vimsottari dasha timelines derived from the natal Moon nakshatra."""

from __future__ import annotations

from typing import List

from ..detectors.common import iso_to_jd, jd_to_iso, moon_lon
from ..events import DashaPeriod

__all__ = ["vimsottari_dashas"]


_DASHA_SEQUENCE: tuple[str, ...] = (
    "Ketu",
    "Venus",
    "Sun",
    "Moon",
    "Mars",
    "Rahu",
    "Jupiter",
    "Saturn",
    "Mercury",
)

_DASHA_LENGTH_YEARS = {
    "Ketu": 7.0,
    "Venus": 20.0,
    "Sun": 6.0,
    "Moon": 10.0,
    "Mars": 7.0,
    "Rahu": 18.0,
    "Jupiter": 16.0,
    "Saturn": 19.0,
    "Mercury": 17.0,
}

_TOTAL_SEQUENCE_YEARS = sum(_DASHA_LENGTH_YEARS.values())
_NAKSHATRA_DEG = 360.0 / 27.0
_SIDEREAL_YEAR_DAYS = 365.25636


def _major_index_and_fraction(natal_jd: float) -> tuple[int, float]:
    moon_longitude = moon_lon(natal_jd) % 360.0
    nak_index = int(moon_longitude // _NAKSHATRA_DEG)
    within = moon_longitude - nak_index * _NAKSHATRA_DEG
    fraction = within / _NAKSHATRA_DEG
    major_index = nak_index % len(_DASHA_SEQUENCE)
    return major_index, fraction


def _major_start_jd(natal_jd: float, major_index: int, fraction: float) -> float:
    major_lord = _DASHA_SEQUENCE[major_index]
    major_days = _DASHA_LENGTH_YEARS[major_lord] * _SIDEREAL_YEAR_DAYS
    elapsed_days = major_days * fraction
    return natal_jd - elapsed_days


def _iterate_major_periods(
    start_jd: float,
    major_index: int,
    start_fraction: float,
    end_jd: float,
):
    current_start = start_jd
    index = major_index
    fraction = start_fraction
    first = True
    while current_start <= end_jd:
        lord = _DASHA_SEQUENCE[index]
        length_days = _DASHA_LENGTH_YEARS[lord] * _SIDEREAL_YEAR_DAYS
        current_end = current_start + length_days
        yield index, lord, current_start, current_end, (fraction if first else 0.0)
        current_start = current_end
        index = (index + 1) % len(_DASHA_SEQUENCE)
        fraction = 0.0
        first = False


def _sub_periods(
    major_index: int,
    major_start: float,
    major_end: float,
    start_fraction: float,
):
    major_length = major_end - major_start
    cumulative = 0.0
    for offset in range(len(_DASHA_SEQUENCE)):
        sub_index = (major_index + offset) % len(_DASHA_SEQUENCE)
        sub_lord = _DASHA_SEQUENCE[sub_index]
        fraction = _DASHA_LENGTH_YEARS[sub_lord] / _TOTAL_SEQUENCE_YEARS
        sub_start_fraction = cumulative
        sub_end_fraction = cumulative + fraction
        cumulative = sub_end_fraction

        if sub_end_fraction <= start_fraction:
            continue

        start = major_start + max(sub_start_fraction, start_fraction) * major_length
        end = major_start + min(sub_end_fraction, 1.0) * major_length
        yield sub_index, sub_lord, start, end

        if sub_end_fraction >= 1.0:
            break


def vimsottari_dashas(
    natal_ts: str,
    start_ts: str,
    end_ts: str,
    *,
    include_partial: bool = True,
) -> List[DashaPeriod]:
    """Return Vimsottari dasha sub-periods intersecting ``start_ts`` → ``end_ts``."""

    start_jd = iso_to_jd(start_ts)
    end_jd = iso_to_jd(end_ts)
    natal_jd = iso_to_jd(natal_ts)

    if end_jd <= start_jd:
        return []

    major_index, major_fraction = _major_index_and_fraction(natal_jd)
    major_start = _major_start_jd(natal_jd, major_index, major_fraction)

    periods: list[DashaPeriod] = []

    for idx, lord, seg_start, seg_end, start_frac in _iterate_major_periods(
        major_start, major_index, major_fraction, end_jd
    ):
        if seg_end < start_jd and not include_partial:
            continue

        for sub_idx, sub_lord, sub_start, sub_end in _sub_periods(idx, seg_start, seg_end, start_frac):
            if sub_end < start_jd and not include_partial:
                continue
            if sub_end < start_jd:
                continue
            if sub_start > end_jd:
                break

            periods.append(
                DashaPeriod(
                    ts=jd_to_iso(sub_start),
                    jd=sub_start,
                    method="vimsottari",
                    major_lord=lord,
                    sub_lord=sub_lord,
                    end_jd=sub_end,
                    end_ts=jd_to_iso(sub_end),
                )
            )

        if seg_start > end_jd:
            break

    periods.sort(key=lambda period: period.jd)
    return periods
