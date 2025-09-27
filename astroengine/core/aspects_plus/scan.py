"""Time window scanner for aspect alignments with bisection refinement."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from .harmonics import combined_angles
from .matcher import angular_sep_deg
from .orb_policy import orb_limit

# ----------------------------------------------------------------------------
# Provider protocol
# ----------------------------------------------------------------------------
# position_provider(ts) -> {name: ecliptic_longitude_deg}
PositionProvider = Callable[[datetime], Dict[str, float]]


# ----------------------------------------------------------------------------
# Data structures
# ----------------------------------------------------------------------------
@dataclass
class TimeWindow:
    start: datetime
    end: datetime


@dataclass
class Hit:
    a: str
    b: str
    aspect_angle: float  # degrees (e.g., 60.0)
    exact_time: datetime
    orb: float  # |Δ - aspect_angle| at exact_time (should be small)
    orb_limit: float


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _date_iter(start: datetime, end: datetime, step: timedelta) -> Iterable[datetime]:
    t = start
    while t <= end:
        yield t
        t = t + step


def _signed_diff(delta_abs: float, target_angle: float) -> float:
    """Return f(Δ) = |Δ| - target; negative when inside, positive when outside."""

    return float(delta_abs) - float(target_angle)


def _refine_bisection(
    f: Callable[[datetime], float],
    t0: datetime,
    t1: datetime,
    max_iter: int = 40,
    tol_seconds: float = 1.0,
) -> datetime:
    """Binary search for root of f(t)=0 within [t0, t1]."""

    a, b = t0, t1
    fa, fb = f(a), f(b)

    # If either endpoint is already precise enough, return it immediately.
    if abs(fa) < 1e-6:
        return a
    if abs(fb) < 1e-6:
        return b

    for _ in range(max_iter):
        mid = a + (b - a) / 2
        fm = f(mid)
        if (b - a).total_seconds() <= tol_seconds or abs(fm) < 1e-6:
            return mid
        if (fa <= 0 and fm >= 0) or (fa >= 0 and fm <= 0):
            b, fb = mid, fm
        else:
            a, fa = mid, fm

    return a + (b - a) / 2


# ----------------------------------------------------------------------------
# Core: scan a single pair across time for multiple target angles
# ----------------------------------------------------------------------------

def scan_pair_time_range(
    a_name: str,
    b_name: str,
    window: TimeWindow,
    position_provider: PositionProvider,
    aspect_angles: Iterable[float],
    orb_policy: Dict,
    step_minutes: int = 60,
    dedup_minutes: int = 30,
) -> List[Hit]:
    """Scan [start, end] for times when |Δ(t) - angle| crosses zero."""

    start = window.start.astimezone(timezone.utc)
    end = window.end.astimezone(timezone.utc)
    step = timedelta(minutes=int(step_minutes))

    aspect_angles = sorted({float(x) for x in aspect_angles})
    hits: List[Hit] = []
    last_hit_time: Dict[float, datetime] = {}

    def delta_abs_at(ts: datetime) -> float:
        pos = position_provider(ts)
        return angular_sep_deg(pos[a_name], pos[b_name])

    for angle in aspect_angles:
        prev_t: Optional[datetime] = None
        prev_f: Optional[float] = None

        for t in _date_iter(start, end, step):
            d = delta_abs_at(t)
            f = _signed_diff(d, angle)

            if prev_t is not None and prev_f is not None:
                sign_change = (prev_f <= 0 and f >= 0) or (prev_f >= 0 and f <= 0)
                if sign_change:
                    root = _refine_bisection(
                        lambda x, target=angle: _signed_diff(delta_abs_at(x), target),
                        prev_t,
                        t,
                    )
                    root = min(max(root, start), end)

                    last = last_hit_time.get(angle)
                    if last and abs((root - last).total_seconds()) < dedup_minutes * 60:
                        prev_t, prev_f = t, f
                        continue

                    d_root = delta_abs_at(root)
                    orb = abs(d_root - angle)
                    limit = orb_limit(
                        a_name,
                        b_name,
                        _aspect_name_from_angle(angle),
                        orb_policy,
                    )
                    if orb <= limit + 1e-6:
                        hits.append(
                            Hit(
                                a=a_name,
                                b=b_name,
                                aspect_angle=angle,
                                exact_time=root,
                                orb=orb,
                                orb_limit=float(limit),
                            )
                        )
                        last_hit_time[angle] = root

            prev_t, prev_f = t, f

    hits.sort(key=lambda h: h.exact_time)
    return hits


_ASPECT_LOOKUP = {
    0.0: "conjunction",
    60.0: "sextile",
    72.0: "quintile",
    90.0: "square",
    120.0: "trine",
    135.0: "sesquisquare",
    144.0: "biquintile",
    150.0: "quincunx",
    180.0: "opposition",
}


def _aspect_name_from_angle(angle: float) -> str:
    rounded = round(angle, 6)
    return _ASPECT_LOOKUP.get(rounded, str(rounded))


# ----------------------------------------------------------------------------
# Top-level multi-pair scan
# ----------------------------------------------------------------------------

def scan_time_range(
    objects: Iterable[str],
    window: TimeWindow,
    position_provider: PositionProvider,
    aspects: Iterable[str],
    harmonics: Iterable[int],
    orb_policy: Dict,
    pairs: Optional[Iterable[Tuple[str, str]]] = None,
    step_minutes: int = 60,
) -> List[Hit]:
    names = list(objects)
    if pairs is None:
        from itertools import combinations

        pairs_iter = combinations(names, 2)
    else:
        pairs_iter = pairs

    angles = combined_angles(aspects, harmonics)

    all_hits: List[Hit] = []
    for a, b in pairs_iter:
        pair_hits = scan_pair_time_range(
            a,
            b,
            window,
            position_provider,
            angles,
            orb_policy,
            step_minutes=step_minutes,
        )
        all_hits.extend(pair_hits)

    all_hits.sort(key=lambda h: h.exact_time)
    return all_hits


__all__ = [
    "TimeWindow",
    "Hit",
    "scan_pair_time_range",
    "scan_time_range",
]
