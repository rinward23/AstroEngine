"""Vimśottarī dasha utilities (legacy period lists and event timelines)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import List, Sequence

from ..detectors.common import UNIX_EPOCH_JD, iso_to_jd, jd_to_iso, moon_lon
from ..events import DashaPeriod, DashaPeriodEvent
from ..utils.angles import norm360

__all__ = ["vimsottari_dashas", "compute_vimshottari_dasha"]

NAKSHATRA_DEGREES = 360.0 / 27.0
SIDEREAL_YEAR_DAYS = 365.25636
TROPICAL_YEAR_DAYS = 365.2425

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

_DASHA_YEARS = {
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

_TOTAL_SEQUENCE_YEARS = sum(_DASHA_YEARS.values())


def _major_index_and_fraction(natal_jd: float) -> tuple[int, float]:
    moon_longitude = moon_lon(natal_jd) % 360.0
    nak_index = int(moon_longitude // NAKSHATRA_DEGREES)
    within = moon_longitude - nak_index * NAKSHATRA_DEGREES
    fraction = within / NAKSHATRA_DEGREES
    major_index = nak_index % len(_DASHA_SEQUENCE)
    return major_index, fraction


def _major_start_jd(natal_jd: float, major_index: int, fraction: float) -> float:
    major_lord = _DASHA_SEQUENCE[major_index]
    major_days = _DASHA_YEARS[major_lord] * SIDEREAL_YEAR_DAYS
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
        length_days = _DASHA_YEARS[lord] * SIDEREAL_YEAR_DAYS
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
        fraction = _DASHA_YEARS[sub_lord] / _TOTAL_SEQUENCE_YEARS
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

        for sub_idx, sub_lord, sub_start, sub_end in _sub_periods(
            idx, seg_start, seg_end, start_frac
        ):
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


def _ensure_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def _to_iso(moment: datetime) -> str:
    moment = _ensure_utc(moment)
    return moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _to_jd(moment: datetime) -> float:
    moment = _ensure_utc(moment)
    return (moment.timestamp() / 86400.0) + UNIX_EPOCH_JD


def _generate_antar_periods(
    ruler_index: int,
    maha_start: datetime,
    maha_end: datetime,
    maha_total_years: float,
    skip_years: float,
    method: str,
) -> list[DashaPeriodEvent]:
    if maha_start >= maha_end:
        return []

    order = _DASHA_SEQUENCE[ruler_index:] + _DASHA_SEQUENCE[:ruler_index]
    parent = _DASHA_SEQUENCE[ruler_index]
    current = maha_start
    remaining_skip = max(skip_years, 0.0)
    produced_years = 0.0
    active_years = max(maha_total_years - skip_years, 0.0)
    events: list[DashaPeriodEvent] = []

    epsilon = timedelta(days=1e-6)

    for sub in order:
        full_years = maha_total_years * (_DASHA_YEARS[sub] / _TOTAL_SEQUENCE_YEARS)
        if remaining_skip >= full_years:
            remaining_skip -= full_years
            continue
        if remaining_skip > 0.0:
            full_years -= remaining_skip
            remaining_skip = 0.0
        if full_years <= 0.0:
            continue
        produced_years += full_years
        if produced_years > active_years:
            full_years -= produced_years - active_years
            produced_years = active_years
        delta = timedelta(days=full_years * TROPICAL_YEAR_DAYS)
        end = current + delta
        if end > maha_end:
            end = maha_end
        if end <= current:
            continue
        events.append(
            DashaPeriodEvent(
                ts=_to_iso(current),
                jd=_to_jd(current),
                method=method,
                level="antar",
                ruler=sub,
                end_ts=_to_iso(end),
                end_jd=_to_jd(end),
                parent=parent,
            )
        )
        current = end
        if current >= maha_end - epsilon:
            break
    if events and current < maha_end:
        last = events[-1]
        events[-1] = DashaPeriodEvent(
            ts=last.ts,
            jd=last.jd,
            method=last.method,
            level=last.level,
            ruler=last.ruler,
            end_ts=_to_iso(maha_end),
            end_jd=_to_jd(maha_end),
            parent=last.parent,
        )
    return events


def compute_vimshottari_dasha(
    moon_longitude_deg: float,
    start: datetime,
    *,
    cycles: int = 1,
    levels: Sequence[str] = ("maha", "antar"),
    method: str = "vimshottari",
) -> list[DashaPeriodEvent]:
    """Return structured Vimsottari periods from a Moon longitude snapshot."""

    if cycles <= 0:
        raise ValueError("cycles must be >= 1")
    levels_normalized = {level.lower() for level in levels}
    if not levels_normalized:
        raise ValueError("at least one level must be requested")
    if not levels_normalized.issubset({"maha", "antar"}):
        raise ValueError("unsupported dasha levels requested")

    start = _ensure_utc(start)
    longitude = norm360(moon_longitude_deg)
    nak_index = int(longitude // NAKSHATRA_DEGREES)
    ruler_index = nak_index % len(_DASHA_SEQUENCE)
    ruler = _DASHA_SEQUENCE[ruler_index]
    total_years = _DASHA_YEARS[ruler]
    offset = longitude % NAKSHATRA_DEGREES
    fraction_elapsed = offset / NAKSHATRA_DEGREES
    elapsed_years = total_years * fraction_elapsed
    current = start
    events: list[DashaPeriodEvent] = []

    for cycle in range(cycles):
        for offset_index in range(len(_DASHA_SEQUENCE)):
            idx = (ruler_index + offset_index) % len(_DASHA_SEQUENCE)
            lord = _DASHA_SEQUENCE[idx]
            full_years = _DASHA_YEARS[lord]
            if cycle == 0 and offset_index == 0:
                skip_years = min(elapsed_years, full_years)
                active_years = max(full_years - skip_years, 0.0)
            else:
                skip_years = 0.0
                active_years = full_years
            if active_years <= 0.0:
                continue
            delta = timedelta(days=active_years * TROPICAL_YEAR_DAYS)
            maha_end = current + delta
            if "maha" in levels_normalized:
                events.append(
                    DashaPeriodEvent(
                        ts=_to_iso(current),
                        jd=_to_jd(current),
                        method=method,
                        level="maha",
                        ruler=lord,
                        end_ts=_to_iso(maha_end),
                        end_jd=_to_jd(maha_end),
                        parent=None,
                    )
                )
            if "antar" in levels_normalized:
                events.extend(
                    _generate_antar_periods(
                        idx,
                        current,
                        maha_end,
                        full_years,
                        skip_years,
                        method,
                    )
                )
            current = maha_end
    return events
