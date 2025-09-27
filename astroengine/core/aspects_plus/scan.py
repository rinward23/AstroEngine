
"""Aspect scanning utilities for AstroEngine Plus."""


from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from itertools import combinations
from typing import Any, Callable, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from astroengine.core.aspects_plus.harmonics import BASE_ASPECTS, harmonic_angles



@dataclass(slots=True)
class TimeWindow:

    """Inclusive start/exclusive end window used for scans."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValueError("end must be after start")

    def clamp(self, ts: datetime) -> datetime:
        if ts < self.start:
            return self.start
        if ts > self.end:
            return self.end
        return ts


@dataclass(frozen=True)
class AspectSpec:
    """Normalized definition of an aspect angle to scan for."""

    name: str
    angle: float
    harmonic: Optional[int] = None



@dataclass(slots=True)
class Hit:
    """Raw aspect hit emitted by scanning routines."""

    a: str
    b: str
    aspect_angle: float
    exact_time: datetime
    orb: float
    orb_limit: float
    meta: Optional[MutableMapping[str, Any]] = None

    def as_mapping(self) -> Mapping[str, Any]:
        base = {
            "a": self.a,
            "b": self.b,
            "aspect_angle": self.aspect_angle,
            "exact_time": self.exact_time,
            "orb": self.orb,
            "orb_limit": self.orb_limit,
        }
        if self.meta:
            base.update(self.meta)
        return base




def _normalize_angle(angle: float) -> float:
    return float(angle) % 360.0


def _signed_sep(delta: float, target: float) -> float:
    """Return signed difference between ``delta`` and ``target`` in degrees."""

    normalized = _normalize_angle(delta)
    base = ((normalized - target + 180.0) % 360.0) - 180.0
    if target not in (0.0, 180.0):
        alternate = 360.0 - target
        alt = ((normalized - alternate + 180.0) % 360.0) - 180.0
        if abs(alt) < abs(base):
            return alt
    return base




def _scan_single_spec(
    body_a: str,
    body_b: str,
    window: TimeWindow,
    provider: Callable[[datetime], Mapping[str, float]],
    spec: AspectSpec,
    limit: float,
    step_minutes: int,
) -> List[Hit]:
    if limit <= 0.0:
        return []
    step = timedelta(minutes=max(1, int(step_minutes)))
    hits: List[Hit] = []

    prev_time = window.start
    prev_delta_opt = _angle_delta(provider, prev_time, body_a, body_b, spec.angle)
    if prev_delta_opt is None:
        return hits
    last_recorded: Optional[datetime] = None

    while prev_time < window.end:
        next_time = prev_time + step
        if next_time > window.end:
            next_time = window.end
        next_delta_opt = _angle_delta(provider, next_time, body_a, body_b, spec.angle)
        if next_delta_opt is None:
            prev_time = next_time
            prev_delta_opt = None
            continue

        candidate: Optional[Tuple[datetime, float]] = None

        if prev_delta_opt == 0.0:
            candidate = (prev_time, 0.0)
        elif next_delta_opt == 0.0:
            candidate = (next_time, 0.0)
        elif prev_delta_opt * next_delta_opt <= 0:
            refined = _bisect_refine(
                provider,
                body_a,
                body_b,
                spec.angle,
                prev_time,
                prev_delta_opt,
                next_time,
                next_delta_opt,
                limit,
            )
            if refined:
                candidate = refined

        if candidate:
            hit_time, orb = candidate
            hit_time = window.clamp(hit_time)
            if orb <= limit + 1e-6:
                if last_recorded is None or abs((hit_time - last_recorded).total_seconds()) > 30:
                    hits.append(
                        Hit(
                            a=body_a,
                            b=body_b,
                            aspect_angle=spec.angle,
                            exact_time=hit_time,
                            orb=orb,
                            orb_limit=limit,
                            meta={"aspect": spec.name, "harmonic": spec.harmonic},
                        )
                    )
                    last_recorded = hit_time

        prev_time = next_time
        prev_delta_opt = next_delta_opt

    return hits


def scan_pair_time_range(
    body_a: str,
    body_b: str,
    window: TimeWindow,
    position_provider: Callable[[datetime], Mapping[str, float]],
    aspect_specs: Sequence[AspectSpec],
    orb_policy: Mapping[str, Any] | None,
    *,
    step_minutes: int = 60,
) -> List[Hit]:
    """Scan a pair of bodies for the provided aspects."""

    hits: List[Hit] = []

    recorded: set[tuple[str, str, float, datetime]] = set()

    current = window.start
    while current <= window.end:
        delta = _pair_delta(position_provider, current, primary, secondary)
        for angle in aspect_angles:
            diff = _signed_sep(delta, angle)
            prev_time, prev_diff = previous[angle]
            if prev_time is None and abs(diff) <= 1e-6:
                limit = _orb_limit(angle, orb_policy, primary, secondary)
                if abs(diff) <= limit:
                    key = (
                        primary,
                        secondary,
                        angle,
                        current.replace(second=0, microsecond=0),
                    )
                    if key not in recorded:
                        hits.append(
                            Hit(
                                a=primary,
                                b=secondary,
                                aspect_angle=angle,
                                exact_time=current,
                                orb=abs(diff),
                                orb_limit=limit,
                                meta={"pair": (primary, secondary)},
                            )
                        )
                        recorded.add(key)
                previous[angle] = (current, diff)
                continue
            if prev_time is not None and prev_diff is not None:
                if prev_diff == 0.0 and abs(diff) <= abs(prev_diff):
                    continue
                if prev_diff * diff <= 0 or abs(diff) < 1e-2:
                    hit_time, hit_diff = _refine_hit(
                        position_provider, primary, secondary, angle, prev_time, current, prev_diff, diff
                    )
                    if window.clamp(hit_time):
                        limit = _orb_limit(angle, orb_policy, primary, secondary)
                        if abs(hit_diff) <= limit:
                            key = (primary, secondary, angle, hit_time.replace(second=0, microsecond=0))
                            if key not in recorded:
                                hits.append(
                                    Hit(
                                        a=primary,
                                        b=secondary,
                                        aspect_angle=angle,
                                        exact_time=hit_time,
                                        orb=abs(hit_diff),
                                        orb_limit=limit,
                                        meta={"pair": (primary, secondary)},
                                    )
                                )
                                recorded.add(key)
            previous[angle] = (current, diff)
        current += step


    hits.sort(key=lambda h: h.exact_time)

    return hits


def _pair_iter(objects: Sequence[str], pairs: Optional[Iterable[Tuple[str, str]]]) -> Iterable[Tuple[str, str]]:
    if pairs:
        for p in pairs:
            if not p or len(p) < 2:
                continue
            yield p[0], p[1]
    else:
        yield from combinations(objects, 2)


def _build_specs(aspects: Sequence[str], harmonics: Sequence[int]) -> List[AspectSpec]:
    specs: List[AspectSpec] = []
    seen: set[Tuple[str, float, Optional[int]]] = set()

    for name in aspects:
        key = (name or "").strip().lower()
        if key not in BASE_ASPECTS:
            continue
        angle = float(BASE_ASPECTS[key])
        signature = (key, angle, None)
        if signature in seen:
            continue
        seen.add(signature)
        specs.append(AspectSpec(name=key, angle=angle, harmonic=None))

    for order in harmonics:
        try:
            order_int = int(order)
        except Exception:
            continue
        if order_int <= 1:
            continue
        for angle in harmonic_angles(order_int):
            signature = (f"harmonic_{order_int}", float(angle), order_int)
            if signature in seen:
                continue
            seen.add(signature)
            specs.append(AspectSpec(name=f"harmonic_{order_int}", angle=float(angle), harmonic=order_int))

    return specs



def scan_time_range(
    *,
    objects: Sequence[str],
    window: TimeWindow,

    position_provider: Callable[[datetime], Mapping[str, float]],
    aspects: Sequence[str],
    harmonics: Sequence[int],
    orb_policy: Mapping[str, Any] | None,
    pairs: Optional[Iterable[Tuple[str, str]]] = None,
    step_minutes: int = 60,
) -> List[Hit]:
    """Scan a set of objects for matching aspect hits."""

    specs = _build_specs(aspects, harmonics)
    if not specs:
        return []

    hits: List[Hit] = []
    for a, b in _pair_iter(objects, pairs):
        hits.extend(
            scan_pair_time_range(
                a,
                b,
                window,
                position_provider,
                specs,
                orb_policy,
                step_minutes=step_minutes,
            )
        )
    hits.sort(key=lambda h: (h.exact_time, h.orb))
    return hits


__all__ = [
    "AspectSpec",
    "Hit",
    "TimeWindow",
    "scan_pair_time_range",
    "scan_time_range",
]

