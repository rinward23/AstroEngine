from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, Iterable, List, Optional

from core.aspects_plus.matcher import angular_sep_deg
from core.aspects_plus.orb_policy import orb_limit
from core.aspects_plus.scan import TimeWindow
from core.aspects_plus.harmonics import BASE_ASPECTS
from core.charts_plus.returns import find_returns_in_window, ReturnWindow

# Provider signature
PositionProvider = Callable[[datetime], Dict[str, float]]

# ----------------------------- Helpers -------------------------------------

def _norm360(x: float) -> float:
    v = x % 360.0
    return v + 360.0 if v < 0 else v


def sign_index(lon_deg: float) -> int:
    """Return zodiac sign index 0..11 for longitude in degrees."""
    return int(_norm360(lon_deg) // 30.0)


def _find_root_bisect(f, t0: datetime, t1: datetime, tol_seconds: float = 1.0, max_iter: int = 60) -> datetime:
    a, b = t0, t1
    fa, fb = f(a), f(b)
    if abs(fa) < 1e-12:
        return a
    if abs(fb) < 1e-12:
        return b
    for _ in range(max_iter):
        mid = a + (b - a) / 2
        fm = f(mid)
        if (b - a).total_seconds() <= tol_seconds or abs(fm) < 1e-12:
            return mid
        if (fa <= 0 and fm >= 0) or (fa >= 0 and fm <= 0):
            b, fb = mid, fm
        else:
            a, fa = mid, fm
    return a + (b - a) / 2


# ----------------------------- Sign ingress --------------------------------

def next_sign_ingress(body: str, start_ts: datetime, provider: PositionProvider, step_minutes: int = 120) -> Optional[datetime]:
    """Find when `body` leaves its current sign, assuming monotonic motion over the coarse step.
    Uses coarse stepping to locate a sign change and refines via bisection on
    g(t) = sign_index(λ(t)) - sign0.
    """
    t0 = start_ts.astimezone(timezone.utc)
    sign0 = sign_index(provider(t0)[body])
    step = timedelta(minutes=int(step_minutes))

    def g(ts: datetime) -> int:
        return sign_index(provider(ts)[body]) - sign0

    prev = t0
    t = t0 + step
    max_span = timedelta(days=3)
    steps = max(1, int(max_span / step) + 2)
    for _ in range(steps):
        val = g(t)
        if val != 0:
            # refine root in [prev, t] using integer function → convert to continuous by lon distance to next boundary
            # define f as signed distance to boundary (in degrees)
            boundary = (sign0 + 1) * 30.0
            def f(ts: datetime) -> float:
                lon = _norm360(provider(ts)[body])
                return lon - boundary
            return _find_root_bisect(f, prev, t, tol_seconds=1.0)
        prev, prev_val = t, val
        t = t + step
    return None


# ----------------------------- VoC Moon ------------------------------------
@dataclass
class EventInterval:
    kind: str
    start: datetime
    end: datetime
    meta: Dict[str, object]


def detect_voc_moon(
    window: TimeWindow,
    provider: PositionProvider,
    aspects: Iterable[str],
    policy: Dict,
    other_objects: Iterable[str],
    step_minutes: int = 60,
) -> List[EventInterval]:
    """Detect Void‑of‑Course Moon intervals within the window.

    MVP semantics: Moon is VoC in a sign segment from **last exact hit** (if any) until sign ingress when
    there are **no exact hits** for Moon↔any(other_objects) for the given `aspects` before leaving the sign.
    If the segment contains no hits at all, the VoC interval is the entire segment.
    """
    start = window.start.astimezone(timezone.utc)
    end = window.end.astimezone(timezone.utc)

    res: List[EventInterval] = []
    cursor = start
    while cursor < end:
        # Current sign segment
        moon_lon = provider(cursor)["Moon"]
        sign0 = sign_index(moon_lon)
        ingress = next_sign_ingress("Moon", cursor, provider) or end
        seg_end = min(ingress, end)

        # Find all exact hits inside [cursor, seg_end) by bracketing aspect roots per pair
        hits: List[datetime] = []
        step = timedelta(minutes=int(step_minutes))
        # Precompute target angles
        target_angles = [BASE_ASPECTS[a.lower()] for a in aspects if a.lower() in BASE_ASPECTS]
        # Coarse scan loop
        t_prev = cursor
        # compute f for each pair & angle: f = |Δ| - angle ; we detect sign changes per (pair,angle)
        def delta_abs(ts: datetime, other: str) -> float:
            pos = provider(ts)
            return angular_sep_deg(pos["Moon"], pos[other])

        vals_prev = {(obj, ang): (delta_abs(t_prev, obj) - ang) for obj in other_objects for ang in target_angles}
        t = cursor + step
        while t <= seg_end:
            vals_now = {(obj, ang): (delta_abs(t, obj) - ang) for obj in other_objects for ang in target_angles}
            for key in vals_prev.keys():
                a_prev = vals_prev[key]
                a_now = vals_now[key]
                if (a_prev <= 0 and a_now >= 0) or (a_prev >= 0 and a_now <= 0):
                    other, ang = key
                    # refine root in [t_prev, t]
                    def f(ts: datetime, other=other, ang=ang) -> float:
                        return delta_abs(ts, other) - ang
                    root = _find_root_bisect(f, t_prev, t, tol_seconds=1.0)
                    # Check orb policy at root
                    pos = provider(root)
                    limit = orb_limit("Moon", other, _aspect_name_from_angle(ang), policy)
                    if abs(delta_abs(root, other) - ang) <= limit + 1e-6:
                        hits.append(root)
            t_prev, vals_prev = t, vals_now
            t = t + step

        hits.sort()
        if not hits:
            res.append(EventInterval(kind="voc_moon", start=cursor, end=seg_end, meta={"sign": sign0}))
        else:
            last = hits[-1]
            if last < seg_end:
                res.append(EventInterval(kind="voc_moon", start=last, end=seg_end, meta={"sign": sign0}))

        cursor = seg_end

    return res


_ASPECT_BY_ANGLE = {
    0.0: "conjunction", 60.0: "sextile", 72.0: "quintile", 90.0: "square", 120.0: "trine",
    135.0: "sesquisquare", 144.0: "biquintile", 150.0: "quincunx", 180.0: "opposition",
}

def _aspect_name_from_angle(ang: float) -> str:
    return _ASPECT_BY_ANGLE.get(round(float(ang), 6), str(round(float(ang), 6)))


# ----------------------------- Combust/Cazimi -------------------------------
@dataclass
class CombustCfg:
    cazimi_deg: float = 0.2667  # ≈ 16′
    combust_deg: float = 8.0
    under_beams_deg: float = 15.0


def detect_combust_cazimi(
    window: TimeWindow,
    provider: PositionProvider,
    planet: str,
    sun_name: str = "Sun",
    cfg: CombustCfg = CombustCfg(),
    step_minutes: int = 10,
) -> List[EventInterval]:
    start = window.start.astimezone(timezone.utc)
    end = window.end.astimezone(timezone.utc)
    step = timedelta(minutes=int(step_minutes))

    intervals: List[EventInterval] = []

    def sep(ts: datetime) -> float:
        pos = provider(ts)
        return angular_sep_deg(pos[planet], pos[sun_name])

    # Track state by threshold; nested categories (cazimi ⊂ combust ⊂ under beams)
    def label(d: float) -> Optional[str]:
        if d <= cfg.cazimi_deg:
            return "cazimi"
        if d <= cfg.combust_deg:
            return "combust"
        if d <= cfg.under_beams_deg:
            return "under_beams"
        return None

    t_prev = start
    d_prev = sep(t_prev)
    s_prev = label(d_prev)
    t = start + step

    def root_to_threshold(t0: datetime, t1: datetime, thr: float) -> datetime:
        # bisection on h(t) = sep(t) - thr
        def h(ts: datetime) -> float:
            return sep(ts) - thr
        return _find_root_bisect(h, t0, t1, tol_seconds=1.0)

    open_start: Optional[datetime] = None
    open_kind: Optional[str] = None

    while t <= end:
        d = sep(t)
        s_now = label(d)
        if s_prev != s_now:
            # We crossed a boundary. Close or open intervals appropriately.
            # Determine which threshold was crossed by checking neighbors.
            # We refine exact crossing for each threshold around (t_prev, t).
            # Close current interval if leaving a state.
            if s_prev is not None:
                thr = cfg.cazimi_deg if s_prev == "cazimi" else (cfg.combust_deg if s_prev == "combust" else cfg.under_beams_deg)
                x = root_to_threshold(t_prev, t, thr)
                if open_start is not None and open_kind == s_prev:
                    intervals.append(EventInterval(kind=open_kind, start=open_start, end=x, meta={"min_sep_deg": None}))
                    open_start, open_kind = None, None
            # Open new interval if entering a state
            if s_now is not None:
                thr = cfg.cazimi_deg if s_now == "cazimi" else (cfg.combust_deg if s_now == "combust" else cfg.under_beams_deg)
                x = root_to_threshold(t_prev, t, thr)
                open_start, open_kind = x, s_now
        t_prev, s_prev = t, s_now
        t = t + step

    # Close any open interval at end
    if open_start is not None and open_kind is not None:
        intervals.append(EventInterval(kind=open_kind, start=open_start, end=end, meta={"min_sep_deg": None}))

    # Post-process to compute min separation per interval (optional)
    out: List[EventInterval] = []
    for it in intervals:
        # crude midpoint sampling for min sep (fast; refine later with Brent if needed)
        mid = it.start + (it.end - it.start) / 2
        out.append(EventInterval(kind=it.kind, start=it.start, end=it.end, meta={"min_sep_deg": sep(mid)}))
    return out


# ----------------------------- Returns wrapper -----------------------------

def detect_returns(
    window: TimeWindow,
    provider: PositionProvider,
    body: str,
    target_lon: float,
    step_minutes: int = 720,
) -> List[EventInterval]:
    rw = ReturnWindow(start=window.start, end=window.end)
    results = find_returns_in_window(body, target_lon, rw, provider, step_minutes=step_minutes)
    out: List[EventInterval] = []
    for r in results:
        out.append(EventInterval(kind="return", start=r.exact_time, end=r.exact_time, meta={"orb": r.orb}))
    return out
