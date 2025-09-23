
"""Sign ingress detection utilities built on Swiss Ephemeris longitudes."""


from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

try:  # pragma: no cover - exercised indirectly via Swiss-enabled tests
    import swisseph as swe  # type: ignore
except Exception:  # pragma: no cover - optional dependency at runtime
    swe = None  # type: ignore

from ..events import IngressEvent
from .common import body_lon, jd_to_iso, norm360, solve_zero_crossing

__all__ = ["ZODIAC_SIGNS", "sign_index", "sign_name", "find_sign_ingresses"]


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


_DEFAULT_BODIES: Sequence[str] = (
    "sun",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
)


@dataclass(frozen=True)
class _Sample:

    jd: float
    longitude: float


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



def _generate_samples(body: str, start_jd: float, end_jd: float, step_days: float) -> Iterable[_Sample]:
    """Yield unwrapped longitude samples for ``body`` between ``start_jd`` and ``end_jd``."""


    jd = start_jd
    prev_unwrapped: float | None = None
    while jd <= end_jd + step_days:
        lon = body_lon(jd, body)
        lon_norm = norm360(lon)
        if prev_unwrapped is None:
            unwrapped = lon_norm
        else:
            base = prev_unwrapped % 360.0
            delta = lon_norm - base
            while delta > 180.0:
                lon_norm -= 360.0
                delta = lon_norm - base
            while delta < -180.0:
                lon_norm += 360.0
                delta = lon_norm - base
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
        # Fall back to linear interpolation in the unwrapped space.
        span = right.longitude - left.longitude
        if span == 0:
            return left.jd
        fraction = (boundary - left.longitude) / span
        return left.jd + fraction * (right.jd - left.jd)


def find_sign_ingresses(
    start_jd: float,
    end_jd: float,
    *,

    bodies: Sequence[str] | None = None,

    step_hours: float = 6.0,
) -> list[IngressEvent]:
    """Detect sign ingress events between ``start_jd`` and ``end_jd`` inclusive."""

    if end_jd <= start_jd:
        return []


    body_list = tuple(bodies or _DEFAULT_BODIES)
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

    if step_hours <= 0:
        raise ValueError("step_hours must be positive")
    if swe is None:
        raise RuntimeError("Swiss ephemeris not available; install astroengine[ephem]")

    body_list = tuple(bodies or _DEFAULT_BODIES)
    step_days = step_hours / 24.0
    events: list[IngressEvent] = []
    seen: set[tuple[str, int]] = set()

    for body_label in body_list:
        body_key = body_label.lower()
        samples = iter(_generate_samples(body_key, start_jd, end_jd, step_days))
        try:
            prev_sample = next(samples)
        except StopIteration:
            continue
        prev_index = math.floor(prev_sample.longitude / 30.0)

        for sample in samples:
            current_index = math.floor(sample.longitude / 30.0)
            if current_index == prev_index:
                prev_sample = sample
                continue

            direction = 1 if current_index > prev_index else -1
            boundary_index = prev_index + 1 if direction > 0 else prev_index
            while (
                (direction > 0 and boundary_index <= current_index)
                or (direction < 0 and boundary_index > current_index)
            ):
                boundary = boundary_index * 30.0
                jd_root = _refine_ingress(body_key, prev_sample, sample, boundary)
                if not (start_jd <= jd_root <= end_jd):
                    if direction > 0:
                        prev_index = boundary_index
                        prev_sample = _Sample(jd=jd_root, longitude=boundary)
                        boundary_index += direction
                    else:
                        prev_index = boundary_index - 1
                        prev_sample = _Sample(jd=jd_root, longitude=boundary)
                        boundary_index += direction
                    continue

                key = (body_key, int(round(jd_root * 86400)))
                if key in seen:
                    if direction > 0:
                        prev_index = boundary_index
                        prev_sample = _Sample(jd=jd_root, longitude=boundary)
                        boundary_index += direction
                    else:
                        prev_index = boundary_index - 1
                        prev_sample = _Sample(jd=jd_root, longitude=boundary)
                        boundary_index += direction
                    continue

                longitude = norm360(body_lon(jd_root, body_key))
                speed = abs(_estimate_speed(body_key, jd_root)) * (1 if direction > 0 else -1)
                motion = "retrograde" if direction < 0 else "direct"
                if direction > 0:
                    from_index = boundary_index - 1
                    to_index = boundary_index
                else:
                    from_index = boundary_index
                    to_index = boundary_index - 1
                from_sign = sign_name(from_index % 12)
                to_sign = sign_name(to_index % 12)

                events.append(
                    IngressEvent(
                        ts=jd_to_iso(jd_root),
                        jd=jd_root,
                        body=str(body_label),
                        from_sign=from_sign,
                        to_sign=to_sign,
                        longitude=longitude,
                        motion=motion,
                        speed_deg_per_day=float(speed),
                    )
                )
                seen.add(key)

                if direction > 0:
                    prev_index = boundary_index
                    boundary_index += direction

                else:
                    prev_index = boundary_index - 1
                    boundary_index += direction
                prev_sample = _Sample(jd=jd_root, longitude=boundary)


            prev_sample = sample
            prev_index = current_index

    events.sort(key=lambda event: (event.jd, event.body.lower()))
    return events
