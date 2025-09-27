from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import sin, radians
from typing import Callable, Dict, Optional, List

# Provider signature: provider(ts) -> {name: ecliptic_longitude_deg [0..360)}
PositionProvider = Callable[[datetime], Dict[str, float]]


# ----------------------------- Angle helpers -------------------------------

def _norm360(x: float) -> float:
    v = x % 360.0
    return v + 360.0 if v < 0 else v


def _angle_diff_signed(a: float, b: float) -> float:
    """Return signed minimal angular difference a-b in (-180,180]."""
    d = (_norm360(a) - _norm360(b) + 180.0) % 360.0 - 180.0
    return d


# ----------------------------- Data classes --------------------------------

@dataclass
class ReturnWindow:
    start: datetime
    end: datetime

@dataclass
class ReturnResult:
    body: str
    target_lon: float
    exact_time: datetime
    orb: float  # absolute separation at solution (should be tiny)


# ----------------------------- Root finding --------------------------------

def _f_halfangle(body: str, target: float, provider: PositionProvider, ts: datetime) -> float:
    """Root function for returns using half-angle sine:
    f(t) = sin((λ_body(t) - λ_target)/2)
    Zeros occur at Δ=0° (and 360°), but **not** at 180°.
    """
    lon = provider(ts)[body]
    d = _angle_diff_signed(lon, target)  # (-180,180]
    return sin(radians(d / 2.0))


def _refine_bisection(f, t0: datetime, t1: datetime, tol_seconds: float = 1.0, max_iter: int = 60) -> datetime:
    a, b = t0, t1
    fa, fb = f(a), f(b)
    # If an endpoint is already near root
    if abs(fa) < 1e-12:
        return a
    if abs(fb) < 1e-12:
        return b
    for _ in range(max_iter):
        mid = a + (b - a) / 2
        fm = f(mid)
        if (b - a).total_seconds() <= tol_seconds or abs(fm) < 1e-12:
            return mid
        # Choose subinterval with sign change
        if (fa <= 0 and fm >= 0) or (fa >= 0 and fm <= 0):
            b, fb = mid, fm
        else:
            a, fa = mid, fm
    return a + (b - a) / 2


# ----------------------------- Public API ----------------------------------

def find_next_return(
    body: str,
    target_lon_deg: float,
    window: ReturnWindow,
    provider: PositionProvider,
    step_minutes: int = 1440,  # 1 day
    tol_seconds: float = 1.0,
) -> Optional[ReturnResult]:
    """Find the next time within `window` when body returns to `target_lon_deg`.

    Strategy: sample f(t)=sin((Δ)/2) on a coarse grid to locate a **sign change**
    around the root, then refine with bisection. Uses UTC internally.
    """
    start = window.start.astimezone(timezone.utc)
    end = window.end.astimezone(timezone.utc)
    step = timedelta(minutes=int(step_minutes))

    # Ensure start < end
    if start >= end:
        return None

    f = lambda ts: _f_halfangle(body, target_lon_deg, provider, ts)

    # Iterate across window looking for sign changes
    prev_t: Optional[datetime] = None
    prev_f: Optional[float] = None

    t = start
    while t <= end:
        ft = f(t)
        # Direct hit on the grid
        if abs(ft) < 1e-9:
            lon_root = provider(t)[body]
            orb = abs(_angle_diff_signed(lon_root, target_lon_deg))
            return ReturnResult(body=body, target_lon=target_lon_deg, exact_time=t, orb=orb)
        if prev_t is not None and prev_f is not None:
            # If we bracket a zero, refine
            if ((prev_f <= 0 and ft >= 0) or (prev_f >= 0 and ft <= 0)) and (
                min(abs(prev_f), abs(ft)) <= 0.5
            ):
                refine_tol = min(tol_seconds, 0.1)
                root = _refine_bisection(f, prev_t, t, tol_seconds=refine_tol)
                # Compute orb at root (absolute minimal separation)
                lon_root = provider(root)[body]
                orb = abs(_angle_diff_signed(lon_root, target_lon_deg))
                return ReturnResult(body=body, target_lon=target_lon_deg, exact_time=root, orb=orb)
        prev_t, prev_f = t, ft
        t = t + step

    return None


def find_returns_in_window(
    body: str,
    target_lon_deg: float,
    window: ReturnWindow,
    provider: PositionProvider,
    step_minutes: int = 1440,
    tol_seconds: float = 1.0,
) -> List[ReturnResult]:
    """Return **all** returns in window by rolling the search forward.
    Useful for long windows or fast bodies (e.g., Moon).
    """
    results: List[ReturnResult] = []
    cursor = window.start
    while True:
        res = find_next_return(body, target_lon_deg, ReturnWindow(start=cursor, end=window.end), provider, step_minutes, tol_seconds)
        if not res:
            break
        results.append(res)
        # Advance cursor slightly past the found root to avoid re-finding it
        cursor = res.exact_time + timedelta(seconds=tol_seconds + 1)
        if cursor >= window.end:
            break
    return results
