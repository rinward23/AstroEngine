
"""Aspect scan dataclasses and utilities for search/ranking pipelines."""


from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import (
    Any,
    Callable,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
)

from .harmonics import BASE_ASPECTS, combined_angles
from .orb_policy import orb_limit as compute_orb_limit


PositionProvider = Callable[[datetime], Mapping[str, float]]


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
        """Return a shallow mapping representation of this hit."""

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


@dataclass(slots=True)
class TimeWindow:
    """Closed interval representing the scan window."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValueError("TimeWindow end must be after start")


def _raw_angle_difference(lon_a: float, lon_b: float, target_angle: float) -> float:
    """Return signed separation delta minus the target angle."""

    separation = abs(((float(lon_a) - float(lon_b) + 180.0) % 360.0) - 180.0)
    return separation - float(target_angle)


def _unwrap(value: float, anchor: Optional[float]) -> float:
    """Adjust ``value`` by ±360° so it remains close to ``anchor``."""

    if anchor is None:
        return value
    result = value
    while result - anchor > 180.0:
        result -= 360.0
    while result - anchor < -180.0:
        result += 360.0
    return result


def _difference(
    ts: datetime,
    angle: float,
    provider: PositionProvider,
    object_a: str,
    object_b: str,
    anchor: Optional[float] = None,
) -> tuple[float, float]:
    """Compute unwrapped difference and absolute orb at ``ts``."""

    positions = provider(ts)
    if object_a not in positions or object_b not in positions:
        missing = object_a if object_a not in positions else object_b
        raise KeyError(f"Position provider missing body '{missing}'")
    raw = _raw_angle_difference(positions[object_a], positions[object_b], angle)
    unwrapped = _unwrap(raw, anchor)
    orb = abs(raw)
    return unwrapped, orb


def _aspect_name_for_angle(angle: float) -> str:
    for name, base in BASE_ASPECTS.items():
        if abs(float(base) - float(angle)) <= 1e-6:
            return name
    return f"angle_{float(angle):.3f}"


def _refine_root(
    left_time: datetime,
    left_val: float,
    left_orb: float,
    right_time: datetime,
    right_val: float,
    right_orb: float,
    angle: float,
    provider: PositionProvider,
    object_a: str,
    object_b: str,
    tolerance: float,
) -> tuple[datetime, float]:
    """Bisection refinement of a bracketed root."""

    a, fa, oa = left_time, left_val, left_orb
    b, fb, ob = right_time, right_val, right_orb
    best_time = a if oa <= ob else b
    best_orb = oa if oa <= ob else ob
    for _ in range(40):
        anchor = fa if abs(fa) <= abs(fb) else fb
        mid = a + (b - a) / 2
        fm, orb = _difference(mid, angle, provider, object_a, object_b, anchor=anchor)
        best_time, best_orb = mid, orb
        if abs(fm) <= tolerance or (b - a).total_seconds() <= 1.0:
            break
        if fa * fm <= 0:
            b, fb, ob = mid, fm, orb
        else:
            a, fa, oa = mid, fm, orb
    return best_time, best_orb


def _scan_pair_for_angle(
    object_a: str,
    object_b: str,
    window: TimeWindow,
    provider: PositionProvider,
    angle: float,
    aspect_name: str,
    orb_policy: Mapping[str, Any],
    step_minutes: int,
    tolerance: float,
) -> List[Hit]:
    hits: List[Hit] = []
    orb_limit = compute_orb_limit(object_a, object_b, aspect_name, orb_policy)
    step = timedelta(minutes=max(1, int(step_minutes)))

    try:
        prev_val, prev_orb = _difference(
            window.start, angle, provider, object_a, object_b
        )
    except KeyError:
        return hits

    if prev_orb <= tolerance:
        hits.append(
            Hit(
                a=object_a,
                b=object_b,
                aspect_angle=float(angle),
                exact_time=window.start,
                orb=prev_orb,
                orb_limit=orb_limit,
                meta=None,
            )
        )

    prev_time = window.start
    current_time = window.start + step

    while current_time <= window.end:
        curr_val, curr_orb = _difference(
            current_time, angle, provider, object_a, object_b, anchor=prev_val
        )

        crossed_zero = prev_val * curr_val < 0.0
        hits_zero_now = curr_orb <= tolerance and prev_orb > tolerance

        if crossed_zero or hits_zero_now:
            exact_time, orb = _refine_root(
                prev_time,
                prev_val,
                prev_orb,
                current_time,
                curr_val,
                curr_orb,
                angle,
                provider,
                object_a,
                object_b,
                tolerance,
            )
            hits.append(
                Hit(
                    a=object_a,
                    b=object_b,
                    aspect_angle=float(angle),
                    exact_time=exact_time,
                    orb=orb,
                    orb_limit=orb_limit,
                    meta=None,
                )
            )

        prev_time = current_time
        prev_val = curr_val
        prev_orb = curr_orb
        current_time += step

    hits.sort(key=lambda h: h.exact_time)
    return hits


def scan_pair_time_range(
    object_a: str,
    object_b: str,
    window: TimeWindow,
    position_provider: PositionProvider,
    aspect_angles: Sequence[float],
    orb_policy: Mapping[str, Any],
    step_minutes: int = 60,
) -> List[Hit]:
    """Scan a pair of bodies for aspect hits across ``aspect_angles``."""

    if step_minutes <= 0:
        raise ValueError("step_minutes must be positive")

    tolerance = 1e-6
    hits: List[Hit] = []
    for angle in sorted(float(a) for a in aspect_angles):
        aspect_name = _aspect_name_for_angle(angle)
        hits.extend(
            _scan_pair_for_angle(
                object_a,
                object_b,
                window,
                position_provider,
                angle,
                aspect_name,
                orb_policy,
                step_minutes,
                tolerance,
            )
        )
    hits.sort(key=lambda h: h.exact_time)
    return hits


def scan_time_range(
    *,
    objects: Sequence[str],
    window: TimeWindow,
    position_provider: PositionProvider,
    aspects: Iterable[str],
    harmonics: Iterable[int],
    orb_policy: Mapping[str, Any],
    pairs: Optional[Sequence[Sequence[str]]] = None,
    step_minutes: int = 60,
) -> List[Hit]:
    """Scan multiple objects/pairs and return sorted aspect hits."""

    if len(objects) < 2 and not pairs:
        return []

    target_angles = combined_angles(aspects, harmonics)
    if not target_angles:
        return []

    if pairs:
        pair_list = [(str(a), str(b)) for a, b in pairs]
    else:
        from itertools import combinations

        pair_list = [(a, b) for a, b in combinations(objects, 2)]

    hits: List[Hit] = []
    for a, b in pair_list:
        hits.extend(
            scan_pair_time_range(
                a,
                b,
                window,
                position_provider,
                target_angles,
                orb_policy,
                step_minutes=step_minutes,
            )
        )

    hits.sort(key=lambda h: h.exact_time)
    return hits


__all__ = ["Hit", "TimeWindow", "scan_pair_time_range", "scan_time_range"]

