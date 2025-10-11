"""Ingress detection utilities built on Swiss Ephemeris longitudes."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from astroengine.ephemeris.swe import has_swe

from ..events import IngressEvent
from ..profiles.profiles import load_base_profile
from .common import body_lon, delta_deg, jd_to_iso, norm360, solve_zero_crossing

_HAS_SWE = has_swe()

__all__ = [
    "ZODIAC_SIGNS",
    "sign_index",
    "sign_name",
    "find_sign_ingresses",
    "find_house_ingresses",
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


_BASE_CORE_BODIES: tuple[str, ...] = (
    "sun",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
)


@dataclass(frozen=True)
class _IngressPolicy:
    """Lightweight container for ingress feature toggles."""

    enabled: bool = True
    include_moon: bool = False
    inner_mode: str = "angles_only"


@dataclass(frozen=True)
class _Sample:

    jd: float
    longitude: float


def _policy_from_mapping(payload: Mapping[str, Any] | None) -> _IngressPolicy:
    if not isinstance(payload, Mapping):
        return _IngressPolicy()

    include_moon = bool(payload.get("include_moon", False))
    inner_mode_raw = str(payload.get("inner_mode", "angles_only") or "angles_only")
    inner_mode = inner_mode_raw.strip().lower()
    if inner_mode not in {"always", "angles_only"}:
        inner_mode = "angles_only"
    enabled = bool(payload.get("enabled", True))
    return _IngressPolicy(enabled=enabled, include_moon=include_moon, inner_mode=inner_mode)


def _ingress_policy(profile: Mapping[str, Any] | None = None) -> _IngressPolicy:
    if profile is None:
        try:
            profile = load_base_profile()
        except Exception:
            profile = None

    feature_flags = (
        profile.get("feature_flags")
        if isinstance(profile, Mapping)
        else None
    )
    ingresses = (
        feature_flags.get("ingresses")
        if isinstance(feature_flags, Mapping)
        else None
    )
    return _policy_from_mapping(ingresses)


def _resolve_policy(
    *,
    include_moon: bool | None,
    inner_mode: str | None,
    profile: Mapping[str, Any] | None,
) -> _IngressPolicy:
    policy = _ingress_policy(profile)
    if include_moon is not None:
        policy = _IngressPolicy(
            enabled=policy.enabled,
            include_moon=bool(include_moon),
            inner_mode=policy.inner_mode,
        )
    if inner_mode is not None:
        mode = str(inner_mode or "").strip().lower()
        if mode not in {"always", "angles_only"}:
            raise ValueError(
                "inner_mode must be 'always' or 'angles_only'"
            )
        policy = _IngressPolicy(
            enabled=policy.enabled,
            include_moon=policy.include_moon,
            inner_mode=mode,
        )
    return policy


def _default_bodies(policy: _IngressPolicy) -> tuple[str, ...]:
    bodies: list[str] = [*_BASE_CORE_BODIES]
    if policy.include_moon:
        bodies.insert(1, "moon")
    if policy.inner_mode == "always":
        bodies.insert(1, "venus")
        bodies.insert(1, "mercury")
    return tuple(dict.fromkeys(bodies))


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


def _generate_samples(
    body: str, start_jd: float, end_jd: float, step_days: float
) -> Iterable[_Sample]:
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


def _normalise_cusps(house_cusps: Sequence[float]) -> list[float]:
    values = [float(value) for value in house_cusps]
    if len(values) < 12:
        raise ValueError("house_cusps must contain at least 12 entries")
    return [norm360(value) for value in values[:12]]


def _house_index(longitude: float, cusps: Sequence[float]) -> int:
    lon = norm360(longitude)
    for idx in range(12):
        start = cusps[idx]
        end = cusps[(idx + 1) % 12]
        if start <= end:
            if start <= lon < end:
                return idx + 1
        else:
            if lon >= start or lon < end:
                return idx + 1
    return 12


def _house_label(index: int) -> str:
    return f"House {((index - 1) % 12) + 1}"


def _refine_house_crossing(
    body: str, left_jd: float, right_jd: float, cusp: float
) -> float | None:
    left, right = (left_jd, right_jd) if left_jd <= right_jd else (right_jd, left_jd)

    def fn(jd: float) -> float:
        return delta_deg(body_lon(jd, body), cusp)

    try:
        return solve_zero_crossing(fn, left, right, tol=1e-6, tol_deg=1e-5)
    except ValueError:
        return None


def find_sign_ingresses(
    start_jd: float,
    end_jd: float,
    *,
    bodies: Sequence[str] | None = None,
    include_moon: bool | None = None,
    inner_mode: str | None = None,
    profile: Mapping[str, Any] | None = None,
    step_hours: float = 6.0,
) -> list[IngressEvent]:
    """Detect sign ingress events between ``start_jd`` and ``end_jd`` inclusive."""

    if end_jd <= start_jd:
        return []
    if step_hours <= 0:
        raise ValueError("step_hours must be positive")
    if not _HAS_SWE:
        raise RuntimeError("Swiss ephemeris not available; install astroengine[ephem]")

    policy = _resolve_policy(
        include_moon=include_moon,
        inner_mode=inner_mode,
        profile=profile,
    )
    if not policy.enabled:
        return []

    if bodies is None:
        body_tuple = _default_bodies(policy)
    else:
        body_tuple = tuple(dict.fromkeys(str(body) for body in bodies))

    if not body_tuple:
        return []

    step_days = max(step_hours, 1.0) / 24.0
    events: list[IngressEvent] = []
    seen: set[tuple[str, int]] = set()

    for body_label in body_tuple:
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
            while (direction > 0 and boundary_index <= current_index) or (
                direction < 0 and boundary_index > current_index
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
                speed = abs(_estimate_speed(body_key, jd_root)) * (
                    1 if direction > 0 else -1
                )
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
                        speed_longitude=float(speed),
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


def find_house_ingresses(
    start_jd: float,
    end_jd: float,
    house_cusps: Sequence[float],
    *,
    bodies: Sequence[str] | None = None,
    include_moon: bool | None = None,
    inner_mode: str | None = None,
    profile: Mapping[str, Any] | None = None,
    step_minutes: float = 60.0,
) -> list[IngressEvent]:
    """Return house ingress events for the supplied ``house_cusps``."""

    if end_jd <= start_jd:
        return []
    if not _HAS_SWE:
        raise RuntimeError("Swiss ephemeris not available; install astroengine[ephem]")

    policy = _resolve_policy(
        include_moon=include_moon,
        inner_mode=inner_mode,
        profile=profile,
    )
    if not policy.enabled:
        return []

    cusps = _normalise_cusps(house_cusps)
    if bodies is None:
        body_list = _default_bodies(policy)
    else:
        body_list = tuple(dict.fromkeys(str(body) for body in bodies))
    if not body_list:
        return []
    step_days = max(step_minutes, 1.0) / (24.0 * 60.0)

    events: list[IngressEvent] = []
    seen: set[tuple[str, int, int]] = set()

    for body in body_list:
        prev_jd = start_jd
        prev_lon = norm360(body_lon(prev_jd, body))
        prev_house = _house_index(prev_lon, cusps)

        jd = start_jd + step_days
        while jd <= end_jd + step_days:
            curr_lon = norm360(body_lon(jd, body))
            curr_house = _house_index(curr_lon, cusps)

            if curr_house != prev_house:
                delta = delta_deg(curr_lon, prev_lon)
                direction = 1 if delta >= 0 else -1
                house = prev_house
                left_jd = prev_jd

                while house != curr_house:
                    if direction > 0:
                        next_house = (house % 12) + 1
                        cusp_index = next_house
                    else:
                        next_house = 12 if house == 1 else house - 1
                        cusp_index = house

                    cusp = cusps[cusp_index - 1]
                    root = _refine_house_crossing(body, left_jd, jd, cusp)
                    if root is None:
                        house = curr_house
                        break

                    lon_exact = norm360(body_lon(root, body))
                    speed = _estimate_speed(body, root, hours=max(step_minutes / 60.0, 1.0))
                    retrograde = direction < 0
                    key = (body, int(round(root * 86400)), next_house)
                    if key not in seen and start_jd <= root <= end_jd:
                        events.append(
                            IngressEvent(
                                ts=jd_to_iso(root),
                                jd=root,
                                body=str(body),
                                from_sign=_house_label(house),
                                to_sign=_house_label(next_house),
                                longitude=lon_exact,
                                speed_longitude=float(speed),
                                retrograde=retrograde,
                            )
                        )
                        seen.add(key)

                    house = next_house
                    left_jd = root

                prev_house = curr_house

            prev_jd = jd
            prev_lon = curr_lon
            jd += step_days

    events.sort(key=lambda event: (event.jd, event.body))
    return events
