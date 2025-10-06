"""Solar rise and set convenience helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Iterable, Sequence

from ...ephemeris.adapter import EphemerisAdapter, ObserverLocation
from .events import EventOptions, rise_set_times
from astroengine.ephemeris.swe import has_swe, swe


_HAS_SWE = has_swe()
_SUN_ID = int(getattr(swe(), "SUN", 0)) if _HAS_SWE else 0
_DEFAULT_DEPRESSION_DEG = -0.8333
_DAY_OFFSETS: Sequence[int] = tuple(range(-3, 4))
_DEFAULT_ADAPTER: EphemerisAdapter | None = None


def _default_adapter() -> EphemerisAdapter:
    global _DEFAULT_ADAPTER
    if _DEFAULT_ADAPTER is None:
        _DEFAULT_ADAPTER = EphemerisAdapter()
    return _DEFAULT_ADAPTER


def _normalize_moment(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def _collect_solar_events(
    adapter: EphemerisAdapter,
    observer: ObserverLocation,
    base_day: datetime,
    *,
    depression_deg: float,
    options: EventOptions,
) -> list[tuple[datetime, str]]:
    events: list[tuple[datetime, str]] = []
    for offset in _DAY_OFFSETS:
        sample_day = base_day + timedelta(days=offset)
        sunrise, sunset = rise_set_times(
            adapter,
            _SUN_ID,
            sample_day,
            observer,
            h0_deg=depression_deg,
            options=options,
        )
        if sunrise is not None:
            events.append((sunrise, "rise"))
        if sunset is not None:
            events.append((sunset, "set"))
    events.sort(key=lambda item: item[0])
    return events


def _nearest_sunset(
    events: Iterable[tuple[datetime, str]],
    *,
    after: datetime,
    before: datetime,
    reference: datetime,
) -> datetime:
    candidates = [
        moment
        for moment, kind in events
        if kind == "set" and after <= moment <= before
    ]
    if not candidates:
        raise RuntimeError("Sunset could not be determined for supplied location")
    return min(candidates, key=lambda dt: abs((dt - reference).total_seconds()))


def solar_cycle(
    moment: datetime,
    observer: ObserverLocation,
    *,
    adapter: EphemerisAdapter | None = None,
    depression_deg: float = _DEFAULT_DEPRESSION_DEG,
    options: EventOptions | None = None,
) -> tuple[datetime, datetime, datetime]:
    """Return sunrise, sunset, and next sunrise surrounding ``moment``.

    The calculation honours the supplied ``observer`` coordinates and will
    raise :class:`RuntimeError` if the solar cycle cannot be determined
    (for example at extreme latitudes during polar day or night).
    """

    adapter = adapter or _default_adapter()
    normalized = _normalize_moment(moment)
    base_day = normalized.replace(hour=0, minute=0, second=0, microsecond=0)
    opts = options or EventOptions()

    events = _collect_solar_events(
        adapter,
        observer,
        base_day,
        depression_deg=depression_deg,
        options=opts,
    )
    rises = [time for time, kind in events if kind == "rise"]

    try:
        sunrise = max(time for time in rises if time <= normalized)
    except ValueError as exc:
        raise RuntimeError(
            "Sunrise could not be determined for supplied location"
        ) from exc

    future_rises = [time for time in rises if time > normalized]
    if not future_rises:
        raise RuntimeError(
            "Next sunrise could not be determined for supplied location"
        )
    next_sunrise = future_rises[0]

    if next_sunrise <= sunrise:
        raise RuntimeError("Solar cycle could not be resolved around moment")

    sunset = _nearest_sunset(
        events,
        after=sunrise,
        before=next_sunrise,
        reference=normalized,
    )

    return sunrise, sunset, next_sunrise


def solar_cycle_for_location(
    moment: datetime,
    *,
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float = 0.0,
    adapter: EphemerisAdapter | None = None,
    depression_deg: float = _DEFAULT_DEPRESSION_DEG,
    options: EventOptions | None = None,
) -> tuple[datetime, datetime, datetime]:
    """Convenience wrapper accepting geodetic coordinates directly."""

    observer = ObserverLocation(
        latitude_deg=float(latitude_deg),
        longitude_deg=float(longitude_deg),
        elevation_m=float(elevation_m),
    )
    return solar_cycle(
        moment,
        observer,
        adapter=adapter,
        depression_deg=depression_deg,
        options=options,
    )


__all__ = ["solar_cycle", "solar_cycle_for_location"]
