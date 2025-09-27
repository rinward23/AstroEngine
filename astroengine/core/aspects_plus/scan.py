

"""Aspect scan dataclasses and helpers used by Plus endpoints."""



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


from datetime import datetime, timedelta
from itertools import combinations
from typing import Any, Callable, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from .harmonics import BASE_ASPECTS, combined_angles


PositionProvider = Callable[[datetime], Mapping[str, float]]


@dataclass(frozen=True)
class TimeWindow:
    """Closed interval used to scan for aspect hits."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:  # pragma: no cover - pydantic already enforces in API
        if self.end <= self.start:
            raise ValueError("end must be after start")

    def clamp(self, ts: datetime) -> bool:
        """Return ``True`` if ``ts`` lies inside the window (inclusive)."""

        return self.start <= ts <= self.end

    @property
    def span(self) -> timedelta:
        """Duration of the window."""

        return self.end - self.start



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


def _angular_separation(delta: float) -> float:
    """Return the smallest angular separation between two positions."""

    normalized = _normalize_angle(delta)
    return normalized if normalized <= 180.0 else 360.0 - normalized


def _signed_sep(delta: float, target: float) -> float:
    """Return signed offset between the actual separation and ``target`` degrees."""

    separation = _angular_separation(delta)
    return separation - target


def _pair_delta(provider: PositionProvider, ts: datetime, primary: str, secondary: str) -> float:
    positions = provider(ts)
    if primary not in positions or secondary not in positions:
        missing = [name for name in (primary, secondary) if name not in positions]
        raise KeyError(f"position provider missing objects: {missing!r}")
    return _normalize_angle(positions[primary] - positions[secondary])


def _aspect_name_for_angle(angle: float) -> Optional[str]:
    for name, base_angle in BASE_ASPECTS.items():
        if abs(base_angle - angle) <= 1e-6:
            return name
    return None


def _orb_limit(
    angle: float,
    orb_policy: Mapping[str, Any] | None,
    primary: str,
    secondary: str,
) -> float:
    if orb_policy is None:
        return 3.0
    limit: Optional[float] = None
    per_aspect = orb_policy.get("per_aspect") if isinstance(orb_policy, Mapping) else None
    name = _aspect_name_for_angle(angle)
    if isinstance(per_aspect, Mapping) and name and name in per_aspect:
        try:
            limit = float(per_aspect[name])
        except (TypeError, ValueError):  # pragma: no cover - defensive
            limit = None
    if limit is None:
        per_object = orb_policy.get("per_object") if isinstance(orb_policy, Mapping) else None
        object_limits: List[float] = []
        if isinstance(per_object, Mapping):
            for key in (primary, secondary):
                if key in per_object:
                    try:
                        object_limits.append(float(per_object[key]))
                    except (TypeError, ValueError):
                        continue
        if object_limits:
            limit = max(object_limits)
    return float(limit if limit is not None else 3.0)


def _refine_hit(
    provider: PositionProvider,
    primary: str,
    secondary: str,
    angle: float,
    t0: datetime,
    t1: datetime,
    d0: float,
    d1: float,
) -> Tuple[datetime, float]:
    a, b = t0, t1
    fa, fb = d0, d1
    for _ in range(24):
        mid = a + (b - a) / 2
        fm = _signed_sep(_pair_delta(provider, mid, primary, secondary), angle)
        if abs(fm) <= 1e-5 or (b - a).total_seconds() <= 30:
            return mid, fm
        if fa == 0.0:
            return a, fa
        if fb == 0.0:
            return b, fb
        if fa * fm <= 0:
            b, fb = mid, fm
        else:
            a, fa = mid, fm
    return mid, fm


def scan_pair_time_range(
    primary: str,
    secondary: str,
    window: TimeWindow,
    position_provider: PositionProvider,
    aspect_angles: Sequence[float],
    orb_policy: Mapping[str, Any] | None = None,
    step_minutes: int = 60,
) -> List[Hit]:
    """Scan ``primary``/``secondary`` pair for aspect hits within ``window``."""

    if window.end <= window.start:
        return []
    if not aspect_angles:
        return []

    step = timedelta(minutes=max(1, int(step_minutes)))
    aspect_angles = sorted({round(float(a), 6) for a in aspect_angles})
    previous: dict[float, tuple[Optional[datetime], Optional[float]]] = {
        angle: (None, None) for angle in aspect_angles
    }
    hits: List[Hit] = []
    recorded: set[tuple[str, str, float, datetime]] = set()

    current = window.start
    while current <= window.end:
        delta = _pair_delta(position_provider, current, primary, secondary)
        for angle in aspect_angles:
            diff = _signed_sep(delta, angle)
            prev_time, prev_diff = previous[angle]
            limit = _orb_limit(angle, orb_policy, primary, secondary)
            if prev_time is None or prev_diff is None:
                if abs(diff) <= limit:
                    key = (primary, secondary, angle, current.replace(second=0, microsecond=0))
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
            if prev_diff == 0.0 and abs(diff) <= abs(prev_diff):
                previous[angle] = (current, diff)
                continue
            if prev_diff * diff <= 0 or abs(diff) < 1e-2:
                hit_time, hit_diff = _refine_hit(
                    position_provider, primary, secondary, angle, prev_time, current, prev_diff, diff
                )
                if window.clamp(hit_time) and abs(hit_diff) <= limit:
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


def scan_time_range(
    *,
    objects: Sequence[str],
    window: TimeWindow,
    position_provider: PositionProvider,
    aspects: Iterable[str],

    harmonics: Iterable[int] | None = None,
    orb_policy: Mapping[str, Any] | None = None,
    pairs: Sequence[Tuple[str, str]] | None = None,
    step_minutes: int = 60,
) -> List[Hit]:
    """Scan all requested pairs for aspect hits within ``window``."""

    if not objects:
        return []
    aspect_angles = combined_angles(aspects, harmonics or [])
    if not aspect_angles:
        return []

    if pairs:
        pair_list = [(a, b) for a, b in pairs]
    else:
        pair_list = list(combinations(objects, 2))

    hits: List[Hit] = []
    for primary, secondary in pair_list:
        hits.extend(
            scan_pair_time_range(
                primary,
                secondary,
                window,
                position_provider,
                aspect_angles,
                orb_policy=orb_policy,

                step_minutes=step_minutes,
            )
        )

    hits.sort(key=lambda h: h.exact_time)
    return hits



__all__ = [
    "TimeWindow",
    "Hit",
    "scan_pair_time_range",
    "scan_time_range",
]


