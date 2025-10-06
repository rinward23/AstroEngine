"""High precision return finder built on top of :class:`EphemerisAdapter`."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import sin
from typing import Any

from ...core.time import TimeConversion, ensure_utc, to_tt
from ...ephemeris import EphemerisAdapter, RefineResult, refine_root
from ._codes import resolve_body_code

__all__ = [
    "ReturnInstant",
    "ReturnNotFoundError",
    "find_return_instant",
    "guess_window",
]

# Julian day helper constants shared with detectors
_UNIX_EPOCH_JD = 2440587.5
_SECONDS_PER_DAY = 86400.0


@dataclass(frozen=True)
class ReturnInstant:
    """Precise return solution describing the perfected longitude."""

    body: str
    target_longitude_deg: float
    exact_time: datetime
    longitude_deg: float
    delta_arcsec: float
    bracket_start: datetime
    bracket_end: datetime
    iterations: int
    evaluations: int
    tolerance_seconds: float
    achieved_tolerance_seconds: float
    status: str
    delta_t_seconds: float
    diagnostics: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "body": self.body,
            "target_longitude_deg": self.target_longitude_deg,
            "exact_time": self.exact_time.isoformat().replace("+00:00", "Z"),
            "longitude_deg": self.longitude_deg,
            "delta_arcsec": self.delta_arcsec,
            "iterations": self.iterations,
            "evaluations": self.evaluations,
            "tolerance_seconds": self.tolerance_seconds,
            "achieved_tolerance_seconds": self.achieved_tolerance_seconds,
            "status": self.status,
            "delta_t_seconds": self.delta_t_seconds,
        }
        payload["diagnostics"] = dict(self.diagnostics)
        payload["bracket"] = {
            "start": self.bracket_start.isoformat().replace("+00:00", "Z"),
            "end": self.bracket_end.isoformat().replace("+00:00", "Z"),
        }
        return payload


class ReturnNotFoundError(RuntimeError):
    """Raised when a return cannot be bracketed inside the supplied window."""


# Mean synodic periods expressed in days. Values loosely follow NASA/JPL data.
_MEAN_PERIODS_DAYS: dict[str, float] = {
    "sun": 365.2422,
    "moon": 27.321661,
    "mercury": 87.9691,
    "venus": 224.7008,
    "mars": 686.980,
    "jupiter": 4332.589,
    "saturn": 10759.22,
    "uranus": 30688.5,
    "neptune": 60182.0,
    "pluto": 90560.0,
}

_STEP_MINUTES: dict[str, float] = {
    "moon": 60.0,  # fast body → 1-hour sampling when bracketing
    "mercury": 360.0,
    "venus": 480.0,
    "sun": 720.0,
}


def _norm360(angle: float) -> float:
    wrapped = angle % 360.0
    return wrapped + 360.0 if wrapped < 0 else wrapped


def _signed_delta(a: float, b: float) -> float:
    delta = (_norm360(a) - _norm360(b) + 180.0) % 360.0 - 180.0
    return delta


def _half_angle_metric(delta_deg: float) -> float:
    # Use the half-angle sine method to avoid false roots at 180°.
    from math import radians

    return sin(radians(delta_deg / 2.0))


def _jd_to_datetime(jd_ut: float) -> datetime:
    seconds = (jd_ut - _UNIX_EPOCH_JD) * _SECONDS_PER_DAY
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    return epoch + timedelta(seconds=seconds)


def _datetime_series(start: datetime, end: datetime, step: timedelta) -> Iterable[datetime]:
    current = start
    while current <= end:
        yield current
        current = current + step


def guess_window(
    body: str,
    last_return: datetime | None,
    around: datetime,
) -> tuple[datetime, datetime]:
    """Return a coarse search window centred around the expected return."""

    key = body.lower()
    period = _MEAN_PERIODS_DAYS.get(key, 365.2422)
    scale = 0.55 if last_return else 0.45
    half_span = max(period * scale, 5.0)
    center = last_return + timedelta(days=period) if last_return else around
    center = ensure_utc(center)
    return (center - timedelta(days=half_span), center + timedelta(days=half_span))


def _step_for(body: str) -> timedelta:
    minutes = _STEP_MINUTES.get(body.lower(), 24 * 60.0)
    return timedelta(minutes=minutes)


def _prepare_conversion(moment: datetime) -> TimeConversion:
    return to_tt(ensure_utc(moment))


def _refine_root(
    adapter: EphemerisAdapter,
    body: str,
    target_lon: float,
    *,
    bracket: tuple[datetime, datetime],
    tol_seconds: float,
    evaluations: int,
) -> tuple[ReturnInstant, int]:
    code = resolve_body_code(body).code
    start_dt, end_dt = bracket
    start_conv = _prepare_conversion(start_dt)
    end_conv = _prepare_conversion(end_dt)
    start_jd = start_conv.jd_utc
    end_jd = end_conv.jd_utc

    conversion_cache: dict[float, TimeConversion] = {
        start_jd: start_conv,
        end_jd: end_conv,
    }

    def _conversion_for(jd_ut: float) -> TimeConversion:
        try:
            return conversion_cache[jd_ut]
        except KeyError:
            conv = to_tt(_jd_to_datetime(jd_ut))
            conversion_cache[jd_ut] = conv
            return conv

    def _delta_at(jd_ut: float) -> float:
        nonlocal evaluations
        conv = _conversion_for(jd_ut)
        sample = adapter.sample(code, conv)
        evaluations += 1
        return _half_angle_metric(_signed_delta(sample.longitude, target_lon))

    refine: RefineResult = refine_root(
        _delta_at,
        start_jd,
        end_jd,
        tol_seconds=max(tol_seconds, 0.05),
        max_iter=64,
    )

    exact_conv = _conversion_for(refine.t_exact_jd)
    exact_sample = adapter.sample(code, exact_conv)
    evaluations += 1
    exact_time = ensure_utc(exact_conv.utc_datetime)
    delta_deg = abs(_signed_delta(exact_sample.longitude, target_lon))
    delta_arcsec = delta_deg * 3600.0

    diagnostics: dict[str, Any] = {
        "method": refine.method,
        "status": refine.status,
        "bracket_jd": (start_jd, end_jd),
        "used_code": code,
    }

    config = getattr(adapter, "_config", None)
    zodiac = "sidereal" if getattr(config, "sidereal", False) else "tropical"
    ayanamsha = getattr(config, "sidereal_mode", None)
    provenance = {
        "zodiac": zodiac,
        "ayanamsha": ayanamsha,
    }

    instant = ReturnInstant(
        body=body,
        target_longitude_deg=target_lon % 360.0,
        exact_time=exact_time,
        longitude_deg=exact_sample.longitude % 360.0,
        delta_arcsec=delta_arcsec,
        bracket_start=start_dt,
        bracket_end=end_dt,
        iterations=refine.iterations,
        evaluations=evaluations,
        tolerance_seconds=tol_seconds,
        achieved_tolerance_seconds=refine.achieved_tol_sec,
        status=refine.status,
        delta_t_seconds=exact_conv.delta_t_seconds,
        diagnostics={**diagnostics, "provenance": provenance},
    )
    return instant, evaluations


def find_return_instant(
    ephem: EphemerisAdapter,
    body: str,
    lambda_natal_deg: float,
    t_window: tuple[datetime, datetime],
    *,
    tz_hint: str | None = None,
    tol_seconds: float = 0.25,
) -> ReturnInstant:
    """Locate the exact instant the transiting ``body`` returns to ``lambda_natal_deg``."""

    start_raw, end_raw = t_window
    start = ensure_utc(start_raw)
    end = ensure_utc(end_raw)
    if end <= start:
        raise ValueError("t_window end must be after start")

    target = lambda_natal_deg % 360.0
    step = _step_for(body)

    samples: list[tuple[datetime, float]] = []
    evaluations = 0
    prev_time: datetime | None = None
    prev_metric: float | None = None
    bracket: tuple[datetime, datetime] | None = None

    code = resolve_body_code(body).code

    for moment in _datetime_series(start, end, step):
        conv = _prepare_conversion(moment)
        sample = ephem.sample(code, conv)
        evaluations += 1
        delta = _signed_delta(sample.longitude, target)
        metric = _half_angle_metric(delta)
        samples.append((moment, delta))
        if abs(metric) <= 1e-8:
            bracket = (moment - timedelta(seconds=step.total_seconds()), moment)
            break
        if prev_time is not None and prev_metric is not None:
            if prev_metric == 0.0 or metric == 0.0 or prev_metric * metric <= 0.0:
                bracket = (prev_time, moment)
                break
        prev_time, prev_metric = moment, metric

    if bracket is None:
        raise ReturnNotFoundError(
            f"Could not bracket {body} return between {start.isoformat()} and {end.isoformat()}"
        )

    instant, evaluations = _refine_root(
        ephem,
        body,
        target,
        bracket=bracket,
        tol_seconds=tol_seconds,
        evaluations=evaluations,
    )

    if tz_hint:
        try:
            from zoneinfo import ZoneInfo  # Python 3.9+

            local_dt = instant.exact_time.astimezone(ZoneInfo(tz_hint))
            instant.diagnostics["local_time"] = local_dt.isoformat()
        except Exception:  # pragma: no cover - invalid tz identifiers
            instant.diagnostics["local_time_error"] = tz_hint

    instant.diagnostics["bracket_samples"] = [
        (moment.isoformat().replace("+00:00", "Z"), value) for moment, value in samples
    ]
    instant.diagnostics["step_minutes"] = step.total_seconds() / 60.0

    return instant
