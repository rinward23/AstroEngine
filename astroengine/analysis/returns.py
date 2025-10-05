"""Numerical solvers for locating return charts and ingress events."""

from __future__ import annotations

from datetime import UTC, datetime, tzinfo

try:  # pragma: no cover - import guard for optional zoneinfo module on <3.9
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - fallback when zoneinfo unavailable
    ZoneInfo = None  # type: ignore[misc,assignment]

from ..core.time import ensure_utc, to_tt
from ..engine.returns import find_return_instant, guess_window
from ..engine.returns._codes import resolve_body_code
from ..ephemeris import EphemerisAdapter

__all__ = [
    "ReturnComputationError",
    "aries_ingress_year",
    "lunar_return_datetimes",
    "solar_return_datetime",
]


class ReturnComputationError(RuntimeError):
    """Raised when a return or ingress cannot be resolved."""


def _safe_year(moment: datetime, year: int) -> datetime:
    """Return ``moment`` with the year substituted, adjusting leap days."""

    try:
        return moment.replace(year=year)
    except ValueError:
        if moment.month == 2 and moment.day == 29:
            return moment.replace(year=year, day=28)
        raise


def _resolve_zoneinfo(tz: str | tzinfo | None) -> tzinfo | None:
    if isinstance(tz, tzinfo):
        return tz
    if isinstance(tz, str) and tz.strip():
        if ZoneInfo is None:  # pragma: no cover - python <3.9 fallback
            raise ReturnComputationError(
                "zoneinfo module not available on this interpreter"
            )
        try:
            return ZoneInfo(tz.strip())
        except Exception as exc:  # pragma: no cover - defensive guard
            raise ReturnComputationError(f"invalid timezone '{tz}'") from exc
    return None


def _apply_timezone(moment: datetime, tz: tzinfo | None) -> datetime:
    if tz is None:
        return moment
    return moment.astimezone(tz)


def _adapter(instance: EphemerisAdapter | None = None) -> EphemerisAdapter:
    if instance is not None:
        return instance
    try:
        return EphemerisAdapter()
    except Exception as exc:  # pragma: no cover - adapter availability guard
        raise ReturnComputationError(str(exc)) from exc


def _natal_longitude(
    adapter: EphemerisAdapter, moment: datetime, body: str
) -> float:
    code = resolve_body_code(body).code
    sample = adapter.sample(code, to_tt(moment))
    return sample.longitude % 360.0


def solar_return_datetime(
    natal_dt: datetime,
    tz: str | tzinfo | None,
    approx_year: int,
    *,
    adapter: EphemerisAdapter | None = None,
) -> datetime:
    """Return the datetime of the solar return nearest ``approx_year``."""

    if approx_year < 0:
        raise ValueError("approx_year must be positive")

    adapter = _adapter(adapter)
    natal_utc = ensure_utc(natal_dt)
    target_lon = _natal_longitude(adapter, natal_utc, "Sun")

    around = _safe_year(natal_utc, approx_year)
    window = guess_window("Sun", None, around)

    try:
        instant = find_return_instant(
            adapter,
            "Sun",
            target_lon,
            window,
            tz_hint=tz if isinstance(tz, str) else None,
        )
    except Exception as exc:  # pragma: no cover - propagate as computation error
        raise ReturnComputationError(str(exc)) from exc

    tzinfo = _resolve_zoneinfo(tz) if not isinstance(tz, tzinfo) else tz
    if tzinfo is None and natal_dt.tzinfo is not None:
        tzinfo = natal_dt.tzinfo
    return _apply_timezone(instant.exact_time, tzinfo)


def lunar_return_datetimes(
    natal_dt: datetime,
    *,
    n: int = 12,
    tz: str | tzinfo | None = None,
    adapter: EphemerisAdapter | None = None,
) -> list[datetime]:
    """Return the next ``n`` lunar returns following ``natal_dt``."""

    if n <= 0:
        return []

    adapter = _adapter(adapter)
    natal_utc = ensure_utc(natal_dt)
    target_lon = _natal_longitude(adapter, natal_utc, "Moon")

    results: list[datetime] = []
    last_return = natal_utc
    tzinfo = _resolve_zoneinfo(tz) if not isinstance(tz, tzinfo) else tz
    if tzinfo is None and natal_dt.tzinfo is not None:
        tzinfo = natal_dt.tzinfo

    for _ in range(n):
        window = guess_window("Moon", last_return, last_return)
        try:
            instant = find_return_instant(
                adapter,
                "Moon",
                target_lon,
                window,
                tz_hint=tz if isinstance(tz, str) else None,
            )
        except Exception as exc:  # pragma: no cover - propagate as computation error
            raise ReturnComputationError(str(exc)) from exc
        last_return = instant.exact_time
        results.append(_apply_timezone(last_return, tzinfo))

    return results


def aries_ingress_year(
    year: int,
    *,
    tz: str | tzinfo | None = None,
    adapter: EphemerisAdapter | None = None,
) -> datetime:
    """Return the datetime when the Sun reaches 0° Aries for ``year``."""

    if year < 0:
        raise ValueError("year must be positive")

    adapter = _adapter(adapter)
    start = datetime(year, 3, 1, tzinfo=UTC)
    end = datetime(year, 4, 1, tzinfo=UTC)

    try:
        instant = find_return_instant(
            adapter,
            "Sun",
            0.0,
            (start, end),
            tz_hint=tz if isinstance(tz, str) else None,
        )
    except Exception as exc:  # pragma: no cover - propagate as computation error
        raise ReturnComputationError(str(exc)) from exc

    tzinfo = _resolve_zoneinfo(tz) if not isinstance(tz, tzinfo) else tz
    return _apply_timezone(instant.exact_time, tzinfo)
