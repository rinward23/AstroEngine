
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


def _coerce_spec(spec: Any) -> AspectSpec:
    """Normalize aspect specifications to :class:`AspectSpec` objects."""

    if isinstance(spec, AspectSpec):
        return spec
    if isinstance(spec, Mapping):
        angle_value = spec.get("angle")
        if angle_value is None:
            raise ValueError("aspect specification requires an 'angle'")
        name_value = spec.get("name") or spec.get("label") or str(angle_value)
        harmonic_value = spec.get("harmonic")
        harmonic_int = None
        if harmonic_value is not None:
            try:
                harmonic_int = int(harmonic_value)
            except Exception:
                harmonic_int = None
        return AspectSpec(name=str(name_value).strip().lower(), angle=float(angle_value), harmonic=harmonic_int)
    try:
        angle = float(spec)
    except Exception as exc:
        raise TypeError(f"Unsupported aspect specification: {spec!r}") from exc
    if isinstance(spec, str):
        name = spec.strip().lower() or str(angle)
    else:
        name = str(int(angle) if float(angle).is_integer() else angle)

    for base_name, base_angle in BASE_ASPECTS.items():
        try:
            if abs(float(base_angle) - angle) <= 1e-6:
                name = base_name
                break
        except Exception:
            continue

    return AspectSpec(name=name, angle=angle, harmonic=None)


def _resolve_orb_limit(
    orb_policy: Mapping[str, Any] | None,
    spec: AspectSpec | Mapping[str, Any] | float | int | str,
    body_a: str,
    body_b: str,
) -> float:
    spec_obj = _coerce_spec(spec)
    policy = orb_policy or {}
    aspect_limits = policy.get("per_aspect", {}) or {}
    key = spec_obj.name.lower()
    limit = aspect_limits.get(key)
    if limit is None:
        limit = aspect_limits.get(str(spec_obj.angle))
    base_default = policy.get("default") if policy else None
    try:
        if limit is not None:
            limit_val = float(limit)
        elif base_default is not None:
            limit_val = float(base_default)
        else:
            limit_val = 1.0
    except Exception:
        limit_val = 1.0

    per_object = policy.get("per_object", {}) or {}
    for obj in (body_a, body_b):
        try:
            limit_val = max(limit_val, float(per_object.get(obj, 0.0)))
        except Exception:
            continue
    return max(0.0, limit_val)





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
    aspect_specs: Sequence[AspectSpec | Mapping[str, Any] | float | int | str],
    orb_policy: Mapping[str, Any] | None,
    *,
    step_minutes: int = 60,
) -> List[Hit]:
    """Scan a pair of bodies for the provided aspects."""

    hits: List[Hit] = []

    for raw_spec in aspect_specs:
        spec = _coerce_spec(raw_spec)
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

