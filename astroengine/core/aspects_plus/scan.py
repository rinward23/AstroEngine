
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


def _resolve_spec_name(angle: float) -> str:
    for key, base_angle in BASE_ASPECTS.items():
        if abs(float(base_angle) - float(angle)) < 1e-6:
            return key
    return f"{angle:g}"


def _coerce_aspect_spec(entry: Any) -> Optional[AspectSpec]:
    if isinstance(entry, AspectSpec):
        return entry
    if isinstance(entry, Mapping):
        name = entry.get("name") or entry.get("aspect")
        angle = entry.get("angle")
        if angle is None and isinstance(name, str):
            base = BASE_ASPECTS.get(name.strip().lower())
            if base is not None:
                angle = float(base)
        if angle is None and "value" in entry:
            try:
                angle = float(entry["value"])
            except (TypeError, ValueError):
                angle = None
        if angle is None and "angle_deg" in entry:
            try:
                angle = float(entry["angle_deg"])
            except (TypeError, ValueError):
                angle = None
        if angle is None:
            return None
        harmonic = entry.get("harmonic")
        try:
            harmonic_int = int(harmonic) if harmonic is not None else None
        except (TypeError, ValueError):
            harmonic_int = None
        if not name:
            name = _resolve_spec_name(float(angle))
        return AspectSpec(name=str(name).strip().lower(), angle=float(angle), harmonic=harmonic_int)
    if isinstance(entry, str):
        key = entry.strip().lower()
        if key in BASE_ASPECTS:
            return AspectSpec(name=key, angle=float(BASE_ASPECTS[key]))
        try:
            angle = float(entry)
        except ValueError:
            return None
        return AspectSpec(name=_resolve_spec_name(angle), angle=angle)
    if isinstance(entry, (int, float)):
        angle = float(entry)
        return AspectSpec(name=_resolve_spec_name(angle), angle=angle)
    return None


def _normalize_aspect_specs(entries: Sequence[Any]) -> List[AspectSpec]:
    specs: List[AspectSpec] = []
    seen: set[Tuple[str, float, Optional[int]]] = set()
    for entry in entries:
        spec = _coerce_aspect_spec(entry)
        if not spec:
            continue
        signature = (spec.name, round(float(spec.angle), 6), spec.harmonic)
        if signature in seen:
            continue
        seen.add(signature)
        specs.append(spec)
    return specs



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



def _separation(
    provider: Callable[[datetime], Mapping[str, float]],
    ts: datetime,
    a: str,
    b: str,
) -> Optional[float]:
    try:
        positions = provider(ts)
        lon_a = float(positions[a])
        lon_b = float(positions[b])
    except Exception:
        return None
    diff = (lon_a - lon_b + 180.0) % 360.0 - 180.0
    return abs(diff)


def _angle_delta(
    provider: Callable[[datetime], Mapping[str, float]],
    ts: datetime,
    a: str,
    b: str,
    target_angle: float,
) -> Optional[float]:
    sep = _separation(provider, ts, a, b)
    if sep is None:
        return None
    return float(sep) - float(target_angle)


def _resolve_orb_limit(
    orb_policy: Mapping[str, Any] | None,
    spec: AspectSpec,
    body_a: str,
    body_b: str,
) -> float:
    policy = orb_policy or {}
    aspect_limits = policy.get("per_aspect", {}) or {}
    key = spec.name.lower()
    limit = aspect_limits.get(key)
    if limit is None:
        limit = aspect_limits.get(str(spec.angle))
    try:
        limit_val = float(limit) if limit is not None else 0.0
    except Exception:
        limit_val = 0.0

    per_object = policy.get("per_object", {}) or {}
    for obj in (body_a, body_b):
        try:
            limit_val = max(limit_val, float(per_object.get(obj, 0.0)))
        except Exception:
            continue

    if limit_val <= 0.0:
        default_limit = policy.get("default")
        if default_limit is None:
            default_limit = policy.get("default_orb_deg")
        try:
            limit_val = float(default_limit)
        except (TypeError, ValueError):
            limit_val = 1.0
        if limit_val <= 0.0:
            limit_val = 1.0

    return max(0.0, limit_val)


def _bisect_refine(
    provider: Callable[[datetime], Mapping[str, float]],
    a: str,
    b: str,
    target_angle: float,
    left_time: datetime,
    left_delta: float,
    right_time: datetime,
    right_delta: float,
    limit: float,
) -> Optional[Tuple[datetime, float]]:
    best_time = left_time if abs(left_delta) <= abs(right_delta) else right_time
    best_delta = left_delta if abs(left_delta) <= abs(right_delta) else right_delta
    for _ in range(40):
        span = right_time - left_time
        if span.total_seconds() <= 1:
            break
        mid_time = left_time + span / 2
        mid_delta = _angle_delta(provider, mid_time, a, b, target_angle)
        if mid_delta is None:
            break
        if abs(mid_delta) < abs(best_delta):
            best_time, best_delta = mid_time, mid_delta
        if left_delta == 0.0 and right_delta == 0.0:
            break
        if left_delta * mid_delta <= 0:
            right_time, right_delta = mid_time, mid_delta
        else:
            left_time, left_delta = mid_time, mid_delta
    orb = abs(best_delta)
    if orb <= limit + 1e-6:
        return best_time, orb
    return None


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
    aspect_specs: Sequence[Any],
    orb_policy: Mapping[str, Any] | None,
    *,
    step_minutes: int = 60,
) -> List[Hit]:
    """Scan a pair of bodies for the provided aspects."""

    specs = _normalize_aspect_specs(aspect_specs)
    if not specs:
        return []

    hits: List[Hit] = []
    for spec in specs:
        limit = _resolve_orb_limit(orb_policy, spec, body_a, body_b)
        hits.extend(
            _scan_single_spec(body_a, body_b, window, position_provider, spec, limit, step_minutes)
        )
    hits.sort(key=lambda h: (h.exact_time, h.orb))
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

