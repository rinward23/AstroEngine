"""Sign ingress detection utilities built on Swiss Ephemeris longitudes."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

try:  # pragma: no cover - exercised through Swiss-dependent tests
    import swisseph as swe  # type: ignore
except Exception:  # pragma: no cover
    swe = None  # type: ignore

from ..events import IngressEvent
from .common import body_lon, jd_to_iso, norm360, solve_zero_crossing

__all__ = [
    "ZODIAC_SIGNS",
    "sign_index",
    "sign_name",
    "find_sign_ingresses",
]

ZODIAC_SIGNS: Sequence[str] = (
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

_BODY_CODES = {
    "sun": lambda: swe.SUN,
    "moon": lambda: swe.MOON,
    "mercury": lambda: swe.MERCURY,
    "venus": lambda: swe.VENUS,
    "mars": lambda: swe.MARS,
    "jupiter": lambda: swe.JUPITER,
    "saturn": lambda: swe.SATURN,
    "uranus": lambda: swe.URANUS,
    "neptune": lambda: swe.NEPTUNE,
    "pluto": lambda: swe.PLUTO,
    "ceres": lambda: swe.CERES,
    "pallas": lambda: swe.PALLAS,
    "juno": lambda: swe.JUNO,
    "vesta": lambda: swe.VESTA,
    "chiron": lambda: swe.CHIRON,
}


def _body_code(name: str) -> int | None:
    resolver = _BODY_CODES.get(name.lower())
    if resolver is None or swe is None:
        return None
    return int(resolver())


def _longitude_and_speed(jd_ut: float, code: int) -> tuple[float, float]:
    assert swe is not None
    values, _ = swe.calc_ut(jd_ut, code, swe.FLG_SWIEPH | swe.FLG_SPEED)
    longitude = float(values[0]) % 360.0
    speed = float(values[3])
    return longitude, speed


def sign_index(longitude: float) -> int:
    """Return the zero-based zodiac sign index for ``longitude`` in degrees."""

    return int(math.floor(norm360(longitude) / 30.0)) % 12


def sign_name(index: int) -> str:
    """Return the canonical sign name for ``index`` (0 = Aries)."""

    return ZODIAC_SIGNS[index % len(ZODIAC_SIGNS)]


def _wrap_to_target(value: float, target: float) -> float:
    """Adjust ``value`` so it lies within ±180° of ``target``."""

    while value - target > 180.0:
        value -= 360.0
    while value - target < -180.0:
        value += 360.0
    return value


def _estimate_speed(body: str, jd_ut: float, *, hours: float = 6.0) -> float:
    """Estimate longitudinal speed in degrees per day at ``jd_ut``."""

    delta_days = max(hours, 1.0) / 24.0
    lon_center = body_lon(jd_ut, body)
    lon_before = _wrap_to_target(body_lon(jd_ut - delta_days, body), lon_center)
    lon_after = _wrap_to_target(body_lon(jd_ut + delta_days, body), lon_center)
    span = lon_after - lon_before
    return span / (2.0 * delta_days)


@dataclass(frozen=True)
class _Sample:
    jd: float
    longitude: float


def _generate_samples(body: str, start_jd: float, end_jd: float, step_days: float) -> Iterable[_Sample]:
    jd = start_jd
    prev_unwrapped: float | None = None
    while jd <= end_jd + step_days:
        lon = body_lon(jd, body)
        if prev_unwrapped is None:
            unwrapped = norm360(lon)
        else:
            base = prev_unwrapped % 360.0
            delta = lon - base
            while delta > 180.0:
                lon -= 360.0
                delta = lon - base
            while delta < -180.0:
                lon += 360.0
                delta = lon - base
            unwrapped = prev_unwrapped + delta
        prev_unwrapped = unwrapped
        yield _Sample(jd=jd, longitude=unwrapped)
        jd += step_days


def _refine_ingress(body: str, left: _Sample, right: _Sample, boundary: float) -> float:
    """Return the Julian day where ``body`` crosses ``boundary`` longitude."""

    def fn(jd: float) -> float:
        lon = _wrap_to_target(body_lon(jd, body), boundary)
        return lon - boundary

    try:
        return solve_zero_crossing(fn, left.jd, right.jd, tol=1e-6, tol_deg=1e-5)
    except ValueError:
        span = right.longitude - left.longitude
        if span == 0:
            return left.jd
        fraction = (boundary - left.longitude) / span
        return left.jd + fraction * (right.jd - left.jd)


def find_sign_ingresses(
    start_jd: float,
    end_jd: float,
    bodies: Iterable[str] | None = None,
    *,
    step_hours: float = 6.0,
) -> list[IngressEvent]:
    """Detect sign ingress events between ``start_jd`` and ``end_jd`` inclusive."""

    if end_jd <= start_jd:
        return []
    if swe is None:
        raise RuntimeError("Swiss ephemeris not available; install astroengine[ephem]")

    body_list = tuple(bodies or ("sun", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"))
    step_days = max(step_hours, 1.0) / 24.0
    events: list[IngressEvent] = []

    for body in body_list:
        samples = list(_generate_samples(body, start_jd, end_jd, step_days))
        for idx in range(1, len(samples)):
            prev = samples[idx - 1]
            curr = samples[idx]
            if prev.longitude == curr.longitude:
                continue
            lower = min(prev.longitude, curr.longitude)
            upper = max(prev.longitude, curr.longitude)
            if math.isclose(lower, upper):
                continue
            start_index = math.floor(lower / 30.0)
            end_index = math.floor(upper / 30.0)
            if start_index == end_index:
                continue

            direction = 1 if curr.longitude > prev.longitude else -1
            boundary_indices = range(start_index + 1, end_index + 1)
            if direction < 0:
                boundary_indices = reversed(list(boundary_indices))

            left_sample = prev
            for boundary_index in boundary_indices:
                boundary = boundary_index * 30.0
                if not (lower - 1e-6 <= boundary <= upper + 1e-6):
                    continue
                jd_root = _refine_ingress(body, left_sample, curr, boundary)
                if not (start_jd <= jd_root <= end_jd):
                    left_sample = _Sample(jd=jd_root, longitude=boundary)
                    continue

                lon_exact = norm360(body_lon(jd_root, body))
                speed = _estimate_speed(body, jd_root)
                retrograde = speed < 0

                if direction >= 0:
                    from_idx = sign_index(boundary - 1e-6)
                    to_idx = sign_index(boundary + 1e-6)
                else:
                    from_idx = sign_index(boundary + 1e-6)
                    to_idx = sign_index(boundary - 1e-6)

                event = IngressEvent(
                    ts=jd_to_iso(jd_root),
                    jd=jd_root,
                    body=body,
                    sign_from=sign_name(from_idx),
                    sign_to=sign_name(to_idx),
                    longitude=lon_exact,
                    speed_longitude=float(speed),
                    retrograde=retrograde,
                )
                events.append(event)
                left_sample = _Sample(jd=jd_root, longitude=boundary)

    events.sort(key=lambda item: item.jd)
    return events
