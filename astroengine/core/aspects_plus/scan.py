
"""Aspect scan dataclasses for search/ranking pipelines."""


from __future__ import annotations

from dataclasses import dataclass

from datetime import datetime, timedelta
from itertools import combinations
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Sequence

from astroengine.core.aspects_plus.harmonics import BASE_ASPECTS, combined_angles

# Provide a reverse lookup for aspect names by base angle.
_ANGLE_TO_NAME = {round(angle, 6): name for name, angle in BASE_ASPECTS.items()}


@dataclass(slots=True)
class TimeWindow:
    start: datetime
    end: datetime

    def clamp(self, dt: datetime) -> datetime:
        if dt < self.start:
            return self.start
        if dt > self.end:
            return self.end
        return dt


@dataclass(slots=True)
class Hit:
    """Raw aspect hit emitted by scanning routines.

    Attributes:
        a: Primary actor identifier (planet/body name).
        b: Secondary actor identifier.
        aspect_angle: Exact aspect angle in degrees.
        exact_time: Timestamp of the aspect hit (timezone-aware preferred).
        orb: Absolute orb distance in degrees.
        orb_limit: Maximum orb allowed for this aspect pairing.
        meta: Optional mutable mapping for downstream annotations.
    """

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


def _circular_delta(a: float, b: float) -> float:
    diff = (float(a) - float(b)) % 360.0
    if diff > 180.0:
        diff = 360.0 - diff
    return abs(diff)


def _orb_limit_for(aspect_name: str, orb_policy: Mapping[str, Any]) -> float:
    per_aspect = orb_policy.get("per_aspect", {}) if orb_policy else {}
    try:
        return float(per_aspect.get(aspect_name, 0.0))
    except Exception:
        return 0.0


def _aspect_name(angle: float) -> str:
    key = round(float(angle), 6)
    if key in _ANGLE_TO_NAME:
        return _ANGLE_TO_NAME[key]
    # Fallback to numeric representation if not a known base aspect.
    return f"angle_{key:g}"


def _refine_hit(
    obj_a: str,
    obj_b: str,
    angle: float,
    window: TimeWindow,
    provider,
    t0: datetime,
    v0: float,
    t1: datetime,
    v1: float,
) -> tuple[datetime, float]:
    """Binary search for the timestamp where the separation matches ``angle``."""

    start, end = t0, t1
    val_start, val_end = v0, v1
    last_sep: float | None = None
    for _ in range(28):
        mid = start + (end - start) / 2
        positions = provider(mid)
        sep = _circular_delta(positions[obj_a], positions[obj_b])
        val_mid = sep - angle
        last_sep = sep
        if abs(val_mid) <= 1e-6 or (end - start).total_seconds() <= 1:
            return window.clamp(mid), sep
        if val_start == 0.0:
            start, val_start = mid, val_mid
            continue
        if val_end == 0.0:
            end, val_end = mid, val_mid
            continue
        if (val_start < 0 <= val_mid) or (val_start > 0 >= val_mid):
            end, val_end = mid, val_mid
        else:
            start, val_start = mid, val_mid
    mid = start + (end - start) / 2
    if last_sep is None:
        positions = provider(mid)
        last_sep = _circular_delta(positions[obj_a], positions[obj_b])
    return window.clamp(mid), last_sep


def scan_pair_time_range(
    obj_a: str,
    obj_b: str,
    window: TimeWindow,
    position_provider,
    aspect_angles: Sequence[float],
    orb_policy: Mapping[str, Any],
    *,
    step_minutes: int = 60,
) -> List[Hit]:
    """Scan a pair of objects over ``window`` for supplied aspect angles."""

    if window.end <= window.start:
        return []

    step = timedelta(minutes=max(1, int(step_minutes)))
    results: List[Hit] = []
    state: dict[float, tuple[datetime, float]] = {}

    current = window.start
    while current <= window.end:
        positions = position_provider(current)
        lon_a = positions[obj_a]
        lon_b = positions[obj_b]
        separation = _circular_delta(lon_a, lon_b)

        for angle in aspect_angles:
            aspect_value = separation - angle
            prev = state.get(angle)
            if prev is not None:
                prev_time, prev_value = prev
            else:
                prev_time, prev_value = None, None  # type: ignore[assignment]

            if abs(aspect_value) <= 1e-6:
                aspect_name = _aspect_name(angle)
                orb_limit = _orb_limit_for(aspect_name, orb_policy)
                if orb_limit <= 0 or 0.0 <= orb_limit + 1e-6:
                    results.append(
                        Hit(
                            a=obj_a,
                            b=obj_b,
                            aspect_angle=angle,
                            exact_time=window.clamp(current),
                            orb=0.0,
                            orb_limit=orb_limit if orb_limit > 0 else float("inf"),
                            meta=None,
                        )
                    )
                state[angle] = (current, aspect_value)
                continue

            hit_detected = False
            if prev_value is not None and prev_time is not None:
                if prev_value * aspect_value < 0:
                    hit_detected = True

            if hit_detected and prev_time is not None and prev_value is not None:
                if abs(prev_value) <= 1e-6:
                    prev_positions = position_provider(prev_time)
                    sep = _circular_delta(prev_positions[obj_a], prev_positions[obj_b])
                    exact_time = window.clamp(prev_time)
                elif abs(aspect_value) <= 1e-6:
                    sep = separation
                    exact_time = window.clamp(current)
                else:
                    exact_time, sep = _refine_hit(
                        obj_a,
                        obj_b,
                        angle,
                        window,
                        position_provider,
                        prev_time,
                        prev_value,
                        current,
                        aspect_value,
                    )
                aspect_name = _aspect_name(angle)
                orb_limit = _orb_limit_for(aspect_name, orb_policy)
                orb = abs(sep - angle)
                if orb_limit <= 0 or orb <= orb_limit + 1e-6:
                    results.append(
                        Hit(
                            a=obj_a,
                            b=obj_b,
                            aspect_angle=angle,
                            exact_time=exact_time,
                            orb=orb,
                            orb_limit=orb_limit if orb_limit > 0 else float("inf"),
                            meta=None,
                        )
                    )
                    state[angle] = (current, aspect_value)
                    continue

            state[angle] = (current, aspect_value)

        current += step

    results.sort(key=lambda h: h.exact_time)
    return results


def scan_time_range(
    *,
    objects: Sequence[str],
    window: TimeWindow,
    position_provider,
    aspects: Sequence[str],
    harmonics: Sequence[int],
    orb_policy: Mapping[str, Any],
    pairs: Optional[Iterable[Sequence[str]]] = None,
    step_minutes: int = 60,
) -> List[Hit]:
    """Scan all requested pairs for aspect hits."""

    angles = combined_angles(aspects, harmonics)
    if not angles:
        return []

    if pairs:
        pair_list = [tuple(p) for p in pairs]
    else:
        pair_list = list(combinations(objects, 2))

    hits: List[Hit] = []
    for a, b in pair_list:
        hits.extend(
            scan_pair_time_range(
                str(a),
                str(b),
                window,
                position_provider,
                angles,
                orb_policy,
                step_minutes=step_minutes,
            )
        )

    hits.sort(key=lambda h: h.exact_time)
    return hits


__all__ = ["Hit", "TimeWindow", "scan_pair_time_range", "scan_time_range"]

