"""Lunisolar calendar helpers for Jyotish calculations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from ...detectors.lunations import find_lunations
from ...events import LunationEvent
from ...ephemeris.swisseph_adapter import SwissEphemerisAdapter, get_swisseph
from .chart import VedicChartContext

__all__ = ["LunarMonth", "lunar_month"]


_AMANTA_MONTHS: Final[tuple[str, ...]] = (
    "Chaitra",
    "Vaishakha",
    "Jyeshtha",
    "Ashadha",
    "Shravana",
    "Bhadrapada",
    "Ashwin",
    "Kartika",
    "Margashirsha",
    "Pausha",
    "Magha",
    "Phalguna",
)

_SIDEREAL_SIGNS: Final[tuple[str, ...]] = (
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

_SUN_SIGN_TO_MONTH_INDEX: Final[dict[int, int]] = {
    11: 0,  # Pisces → Chaitra
    0: 1,  # Aries → Vaishakha
    1: 2,  # Taurus → Jyeshtha
    2: 3,  # Gemini → Ashadha
    3: 4,  # Cancer → Shravana
    4: 5,  # Leo → Bhadrapada
    5: 6,  # Virgo → Ashwin
    6: 7,  # Libra → Kartika
    7: 8,  # Scorpio → Margashirsha
    8: 9,  # Sagittarius → Pausha
    9: 10,  # Capricorn → Magha
    10: 11,  # Aquarius → Phalguna
}

_LUNATION_WINDOW_DAYS: Final[float] = 35.0


@dataclass(frozen=True)
class LunarMonth:
    """Resolved lunar month metadata for a given moment."""

    name: str
    index: int
    adhika: bool
    start: datetime
    end: datetime
    start_julian_day: float
    end_julian_day: float
    sun_sign: str
    sun_sign_index: int

    def contains(self, moment: datetime) -> bool:
        """Return ``True`` when ``moment`` falls inside the month interval."""

        if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
            moment = moment.replace(tzinfo=UTC)
        moment_utc = moment.astimezone(UTC)
        return self.start <= moment_utc < self.end


def _sign_index(longitude: float) -> int:
    normalized = float(longitude) % 360.0
    return int(normalized // 30.0)


def _month_index_for_sign(sign_index: int) -> int:
    try:
        return _SUN_SIGN_TO_MONTH_INDEX[sign_index]
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"Unsupported sign index {sign_index}") from exc


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(UTC)


def _surrounding_new_moons(jd_ut: float) -> tuple[LunationEvent, LunationEvent]:
    events = find_lunations(jd_ut - _LUNATION_WINDOW_DAYS, jd_ut + _LUNATION_WINDOW_DAYS)
    new_moons: list[LunationEvent] = [event for event in events if event.phase == "new_moon"]
    if not new_moons:
        raise ValueError("Unable to locate lunations within the search window")

    prev_candidates = [event for event in new_moons if event.jd <= jd_ut]
    next_candidates = [event for event in new_moons if event.jd > jd_ut]

    if not prev_candidates or not next_candidates:
        raise ValueError("Insufficient lunations to bracket the requested moment")

    prev_event = max(prev_candidates, key=lambda event: event.jd)
    next_event = min(next_candidates, key=lambda event: event.jd)
    return prev_event, next_event


def _sun_sign(adapter: SwissEphemerisAdapter, jd_ut: float) -> tuple[int, str]:
    try:
        swe = get_swisseph()
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency guard
        raise RuntimeError(
            "Swiss Ephemeris is required for panchanga calculations. Install astroengine[ephem]."
        ) from exc
    position = adapter.body_position(jd_ut, swe.SUN, body_name="Sun")
    idx = _sign_index(position.longitude)
    return idx, _SIDEREAL_SIGNS[idx]


def lunar_month(context: VedicChartContext) -> LunarMonth:
    """Return the amanta month and Adhika status for ``context``."""

    jd = context.chart.julian_day
    prev_new_moon, next_new_moon = _surrounding_new_moons(jd)

    sun_sign_index, sun_sign = _sun_sign(context.adapter, prev_new_moon.jd)
    next_sign_index, _ = _sun_sign(context.adapter, next_new_moon.jd)

    month_index = _month_index_for_sign(sun_sign_index)
    name = _AMANTA_MONTHS[month_index]

    return LunarMonth(
        name=name,
        index=month_index,
        adhika=sun_sign_index == next_sign_index,
        start=_parse_ts(prev_new_moon.ts),
        end=_parse_ts(next_new_moon.ts),
        start_julian_day=prev_new_moon.jd,
        end_julian_day=next_new_moon.jd,
        sun_sign=sun_sign,
        sun_sign_index=sun_sign_index,
    )
