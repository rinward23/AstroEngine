"""Zodiacal releasing period tables for the Lot of Fortune."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from ..detectors.common import UNIX_EPOCH_JD
from ..events import ZodiacalReleasingPeriod
from ..utils.angles import norm360

YEAR_IN_DAYS = 365.2425

_SIGNS = [
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
]

_PERIOD_YEARS = {
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

_TOTAL_YEARS = sum(_PERIOD_YEARS.values())

__all__ = ["compute_zodiacal_releasing"]


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


def _generate_level_two(
    parent_index: int,
    parent_start: datetime,
    parent_end: datetime,
    lot: str,
    method: str,
) -> list[ZodiacalReleasingPeriod]:
    epsilon = timedelta(days=1e-6)
    parent_sign = _SIGNS[parent_index]
    parent_years = _PERIOD_YEARS[parent_sign]
    scale = parent_years / _TOTAL_YEARS
    current = parent_start
    events: list[ZodiacalReleasingPeriod] = []

    for offset in range(len(_SIGNS)):
        idx = (parent_index + offset) % len(_SIGNS)
        sign = _SIGNS[idx]
        span_years = _PERIOD_YEARS[sign] * scale
        delta = timedelta(days=span_years * YEAR_IN_DAYS)
        end = current + delta
        if end > parent_end:
            end = parent_end
        if end <= current:
            continue
        events.append(
            ZodiacalReleasingPeriod(
                ts=_to_iso(current),
                jd=_to_jd(current),
                method=method,
                level="l2",
                ruler=sign,
                end_ts=_to_iso(end),
                end_jd=_to_jd(end),
                lot=lot,
                sign=sign,
            )
        )
        current = end
        if current >= parent_end - epsilon:
            break

    if events and current < parent_end:
        last = events[-1]
        events[-1] = ZodiacalReleasingPeriod(
            ts=last.ts,
            jd=last.jd,
            method=last.method,
            level=last.level,
            ruler=last.ruler,
            end_ts=_to_iso(parent_end),
            end_jd=_to_jd(parent_end),
            lot=last.lot,
            sign=last.sign,
        )
    return events


def compute_zodiacal_releasing(
    fortune_longitude_deg: float,
    start: datetime,
    *,
    lot: str = "fortune",
    periods: int = 12,
    levels: Sequence[str] = ("l1", "l2"),
    method: str | None = None,
) -> list[ZodiacalReleasingPeriod]:
    if periods <= 0:
        raise ValueError("periods must be >= 1")
    levels_normalized = {level.lower() for level in levels}
    if not levels_normalized:
        raise ValueError("at least one releasing level must be requested")
    if not levels_normalized.issubset({"l1", "l2"}):
        raise ValueError("unsupported releasing levels requested")

    start = _ensure_utc(start)
    lot_lower = lot.lower()
    method_name = method or f"zr_{lot_lower}"
    longitude = norm360(fortune_longitude_deg)
    sign_index = int(longitude // 30.0) % len(_SIGNS)
    current = start
    events: list[ZodiacalReleasingPeriod] = []

    for count in range(periods):
        idx = (sign_index + count) % len(_SIGNS)
        sign = _SIGNS[idx]
        span_years = _PERIOD_YEARS[sign]
        end = current + timedelta(days=span_years * YEAR_IN_DAYS)
        if "l1" in levels_normalized:
            events.append(
                ZodiacalReleasingPeriod(
                    ts=_to_iso(current),
                    jd=_to_jd(current),
                    method=method_name,
                    level="l1",
                    ruler=sign,
                    end_ts=_to_iso(end),
                    end_jd=_to_jd(end),
                    lot=lot_lower,
                    sign=sign,
                )
            )
        if "l2" in levels_normalized:
            events.extend(
                _generate_level_two(
                    idx,
                    current,
                    end,
                    lot_lower,
                    method_name,
                )
            )
        current = end
    return events
