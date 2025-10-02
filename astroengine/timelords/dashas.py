"""Vimśottarī daśā timelines derived from the natal Moon nakṣatra."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime, timedelta

from ..detectors.common import UNIX_EPOCH_JD, iso_to_jd, jd_to_iso, moon_lon
from ..events import DashaPeriod, DashaPeriodEvent
from ..utils.angles import norm360

YEAR_IN_DAYS = 365.2425
SIDEREAL_YEAR_DAYS = 365.25636
NAKSHATRA_SIZE = 360.0 / 27.0

NAKSHATRA_DEGREES = NAKSHATRA_SIZE
TROPICAL_YEAR_DAYS = YEAR_IN_DAYS


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


_LEVEL_NAMES: tuple[str, ...] = (
    "maha",
    "antar",
    "pratyantar",
    "sookshma",
    "praan",
)

_LEVEL_TO_DEPTH = {name: depth for depth, name in enumerate(_LEVEL_NAMES, start=1)}


__all__ = ["vimsottari_dashas", "compute_vimshottari_dasha"]


def _major_index_and_fraction(natal_jd: float) -> tuple[int, float]:
    longitude = norm360(moon_lon(natal_jd))
    nak_index = int(longitude // NAKSHATRA_SIZE)
    within = longitude - nak_index * NAKSHATRA_SIZE
    fraction = within / NAKSHATRA_SIZE

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
) -> Iterable[tuple[int, str, float, float, float]]:
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
) -> Iterable[tuple[int, str, float, float]]:
    major_length = max(major_end - major_start, 0.0)
    if major_length <= 0.0:
        return []
    cumulative = 0.0
    results: list[tuple[int, str, float, float]] = []
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
        results.append((sub_index, sub_lord, start, end))

        if sub_end_fraction >= 1.0:
            break
    return results


def vimsottari_dashas(
    natal_ts: str,
    start_ts: str,
    end_ts: str,
    *,
    include_partial: bool = True,
) -> list[DashaPeriod]:
    """Return Vimśottarī daśā sub-periods intersecting ``start_ts`` → ``end_ts``."""

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

        for _sub_idx, sub_lord, sub_start, sub_end in _sub_periods(
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
    return _ensure_utc(moment).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _to_jd(moment: datetime) -> float:
    moment_utc = _ensure_utc(moment)
    return (moment_utc.timestamp() / 86400.0) + UNIX_EPOCH_JD


def _generate_nested_periods(
    ruler_index: int,
    parent_start: datetime,
    parent_end: datetime,
    parent_total_years: float,
    skip_years: float,
    *,
    method: str,
    requested_levels: set[str],
    max_depth: int,
    depth: int,
    parent_chain: tuple[str, ...],
) -> list[DashaPeriodEvent]:
    if depth > max_depth:
        return []

    parent_start = _ensure_utc(parent_start)
    parent_end = _ensure_utc(parent_end)
    if parent_end <= parent_start or parent_total_years <= 0.0:
        return []

    parent_total_days = parent_total_years * TROPICAL_YEAR_DAYS
    active_days = (parent_end - parent_start).total_seconds() / 86400.0
    if active_days <= 0.0:
        return []

    start_fraction = 0.0
    if parent_total_years > 0.0:
        start_fraction = max(0.0, min(skip_years / parent_total_years, 1.0))

    active_fraction = min(max(active_days / parent_total_days, 0.0), 1.0 - start_fraction)
    end_fraction = min(1.0, start_fraction + active_fraction)
    coverage = max(end_fraction - start_fraction, 0.0)
    if coverage <= 0.0:
        return []

    level_name = _LEVEL_NAMES[depth - 1]
    order = _DASHA_SEQUENCE[ruler_index:] + _DASHA_SEQUENCE[:ruler_index]
    parent_length = timedelta(days=active_days)
    events: list[DashaPeriodEvent] = []

    cumulative = 0.0
    epsilon = 1e-9
    for offset, sub in enumerate(order):
        fraction = _DASHA_YEARS[sub] / _TOTAL_SEQUENCE_YEARS
        sub_start_fraction = cumulative
        sub_end_fraction = cumulative + fraction
        cumulative = sub_end_fraction

        if sub_end_fraction <= start_fraction + epsilon:
            continue
        if sub_start_fraction >= end_fraction - epsilon:
            break

        actual_start_fraction = max(sub_start_fraction, start_fraction)
        actual_end_fraction = min(sub_end_fraction, end_fraction)
        if actual_start_fraction >= actual_end_fraction:
            continue

        if coverage <= 0.0:
            continue
        normalized_start = (actual_start_fraction - start_fraction) / coverage
        normalized_end = (actual_end_fraction - start_fraction) / coverage
        child_start = parent_start + parent_length * normalized_start
        child_end = parent_start + parent_length * normalized_end
        if (
            offset == len(order) - 1
            or actual_end_fraction >= end_fraction - epsilon
            or child_end > parent_end
        ):
            child_end = parent_end

        child_total_years = parent_total_years * fraction
        skipped_fraction = max(0.0, start_fraction - sub_start_fraction)
        child_skip_years = (
            child_total_years * (skipped_fraction / fraction)
            if fraction > 0.0
            else 0.0
        )

        if level_name in requested_levels:
            events.append(
                DashaPeriodEvent(
                    ts=_to_iso(child_start),
                    jd=_to_jd(child_start),
                    method=method,
                    level=level_name,
                    ruler=sub,
                    end_ts=_to_iso(child_end),
                    end_jd=_to_jd(child_end),
                    parent=parent_chain[-1] if parent_chain else None,
                )
            )

        next_index = (ruler_index + offset) % len(_DASHA_SEQUENCE)
        if depth < max_depth:
            events.extend(
                _generate_nested_periods(
                    next_index,
                    child_start,
                    child_end,
                    child_total_years,
                    child_skip_years,
                    method=method,
                    requested_levels=requested_levels,
                    max_depth=max_depth,
                    depth=depth + 1,
                    parent_chain=(*parent_chain, sub),
                )
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
    """Return ordered daśā periods beginning from ``start``."""

    if cycles <= 0:
        raise ValueError("cycles must be >= 1")
    normalized_levels = {level.lower() for level in levels}
    if not normalized_levels:
        raise ValueError("at least one dasha level must be requested")
    unknown = normalized_levels.difference(_LEVEL_TO_DEPTH)
    if unknown:
        raise ValueError(f"unsupported dasha levels requested: {sorted(unknown)!r}")

    start = _ensure_utc(start)
    longitude = norm360(moon_longitude_deg)

    nak_index = int(longitude // NAKSHATRA_SIZE)
    ruler_index = nak_index % len(_DASHA_SEQUENCE)
    ruler = _DASHA_SEQUENCE[ruler_index]
    total_years = _DASHA_YEARS[ruler]
    offset = longitude % NAKSHATRA_DEGREES
    fraction_elapsed = offset / NAKSHATRA_DEGREES
    elapsed_years = total_years * fraction_elapsed
    current = start
    events: list[DashaPeriodEvent] = []
    max_depth = max(_LEVEL_TO_DEPTH[level] for level in normalized_levels)

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
            if "maha" in normalized_levels:
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
            if max_depth > 1:
                events.extend(
                    _generate_nested_periods(
                        idx,
                        current,
                        maha_end,
                        full_years,
                        skip_years,
                        method=method,
                        requested_levels=normalized_levels,
                        max_depth=max_depth,
                        depth=2,
                        parent_chain=(lord,),
                    )
                )
            current = maha_end
    return events
