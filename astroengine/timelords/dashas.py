"""Vimshottari dasha timelines derived from the Moon's nakshatra."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Sequence

from ..detectors.common import UNIX_EPOCH_JD
from ..events import DashaPeriodEvent
from ..utils.angles import norm360

YEAR_IN_DAYS = 365.2425
NAKSHATRA_SIZE = 360.0 / 27.0

_DASHA_ORDER = [
    "Ketu",
    "Venus",
    "Sun",
    "Moon",
    "Mars",
    "Rahu",
    "Jupiter",
    "Saturn",
    "Mercury",
]

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

_TOTAL_CYCLE_YEARS = sum(_DASHA_YEARS.values())

__all__ = ["compute_vimshottari_dasha"]


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

    order = _DASHA_ORDER[ruler_index:] + _DASHA_ORDER[:ruler_index]
    parent = _DASHA_ORDER[ruler_index]
    current = maha_start
    remaining_skip = max(skip_years, 0.0)
    produced_years = 0.0
    active_years = max(maha_total_years - skip_years, 0.0)
    events: list[DashaPeriodEvent] = []

    epsilon = timedelta(days=1e-6)

    for sub in order:
        full_years = maha_total_years * (_DASHA_YEARS[sub] / _TOTAL_CYCLE_YEARS)
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
        delta = timedelta(days=full_years * YEAR_IN_DAYS)
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
    if cycles <= 0:
        raise ValueError("cycles must be >= 1")
    levels_normalized = {level.lower() for level in levels}
    if not levels_normalized:
        raise ValueError("at least one level must be requested")
    if not levels_normalized.issubset({"maha", "antar"}):
        raise ValueError("unsupported dasha levels requested")

    start = _ensure_utc(start)
    longitude = norm360(moon_longitude_deg)
    nak_index = int(longitude // NAKSHATRA_SIZE)
    ruler_index = nak_index % len(_DASHA_ORDER)
    ruler = _DASHA_ORDER[ruler_index]
    total_years = _DASHA_YEARS[ruler]
    offset = longitude % NAKSHATRA_SIZE
    fraction_elapsed = offset / NAKSHATRA_SIZE
    elapsed_years = total_years * fraction_elapsed
    current = start
    events: list[DashaPeriodEvent] = []

    for cycle in range(cycles):
        for offset_index in range(len(_DASHA_ORDER)):
            idx = (ruler_index + offset_index) % len(_DASHA_ORDER)
            lord = _DASHA_ORDER[idx]
            full_years = _DASHA_YEARS[lord]
            if cycle == 0 and offset_index == 0:
                skip_years = min(elapsed_years, full_years)
                active_years = max(full_years - skip_years, 0.0)
            else:
                skip_years = 0.0
                active_years = full_years
            if active_years <= 0.0:
                continue
            delta = timedelta(days=active_years * YEAR_IN_DAYS)
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
