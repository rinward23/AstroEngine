# >>> AUTO-GEN BEGIN: performance core v1.0
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from ._cache import calc_ut_lon, ensure_ephe_initialized  # ENSURE-LINE

try:
    from astroengine.ephemeris.swe import swe
except Exception:  # pragma: no cover
    swe = None


def _jd_from_utc(ts: dt.datetime) -> float:
    """UTC naive/aware -> Julian Day."""
    if ts.tzinfo is not None:
        ts = ts.astimezone(dt.UTC).replace(tzinfo=None)
    y, m, d = ts.year, ts.month, ts.day
    h = ts.hour + ts.minute / 60 + (ts.second + ts.microsecond / 1e6) / 3600
    if swe is None:
        return 0.0
    ensure_ephe_initialized()
    return swe().julday(y, m, d, h)


def _angnorm(a: float) -> float:
    return a % 360.0


def _signed_delta(a: float, b: float) -> float:
    """Smallest signed diff a-b in [-180,180]."""
    d = (a - b + 540.0) % 360.0 - 180.0
    return d


@dataclass(frozen=True)
class ScanConfig:
    body: int  # e.g., swe().SUN
    natal_lon_deg: float  # 0..360
    aspect_angle_deg: float  # e.g., 0,60,90,120,180
    orb_deg: float = 6.0
    tick_minutes: int = 60  # coarse tick
    refine_max_iter: int = 24
    refine_tol_deg: float = 1e-4  # ~0.0001° (~0.36")
    flags: int = 0


def _bracket_zero(
    jd0: float, jd1: float, cfg: ScanConfig
) -> tuple[float, float] | None:
    """Return (jda, jdb) if signed delta crosses zero in [jd0,jd1]."""
    ensure_ephe_initialized()
    a0 = calc_ut_lon(jd0, cfg.body, cfg.flags)
    a1 = calc_ut_lon(jd1, cfg.body, cfg.flags)
    target = _angnorm(cfg.natal_lon_deg + cfg.aspect_angle_deg)
    d0 = _signed_delta(a0, target)
    d1 = _signed_delta(a1, target)
    if d0 == 0.0:
        return (jd0, jd0)
    if d1 == 0.0:
        return (jd1, jd1)
    if (d0 > 0 and d1 < 0) or (d0 < 0 and d1 > 0):
        return (jd0, jd1)
    return None


def _bisection(jda: float, jdb: float, cfg: ScanConfig) -> float:
    """Bisection to solve signed_delta=0."""
    ensure_ephe_initialized()
    target = _angnorm(cfg.natal_lon_deg + cfg.aspect_angle_deg)

    def delta(jd: float) -> float:
        return _signed_delta(calc_ut_lon(jd, cfg.body, cfg.flags), target)

    a, b = jda, jdb
    fa = delta(a)
    for _ in range(cfg.refine_max_iter):
        m = 0.5 * (a + b)
        fm = delta(m)
        if abs(fm) <= cfg.refine_tol_deg:
            return m
        if (fa > 0 and fm < 0) or (fa < 0 and fm > 0):
            b = m
        else:
            a, fa = m, fm
    return 0.5 * (a + b)


def fast_scan(
    start_utc: dt.datetime, end_utc: dt.datetime, cfg: ScanConfig
) -> list[tuple[dt.datetime, float]]:
    """
    Fast aspect scan:
      - coarse ticks at cfg.tick_minutes
      - only refine when sign change
      - filter by orb at tick time (cheap early gate)
    Returns list of (exact_utc, delta_deg_at_tick) for each hit.
    """
    if swe is None:
        raise RuntimeError("Swiss not available; ensure py311 + pyswisseph installed.")
    ensure_ephe_initialized()
    tick_minutes = max(1, int(cfg.tick_minutes))
    step_days = tick_minutes / (60 * 24)
    jd = _jd_from_utc(start_utc)
    jd_end = _jd_from_utc(end_utc)
    target = _angnorm(cfg.natal_lon_deg + cfg.aspect_angle_deg)

    hits: list[tuple[dt.datetime, float]] = []
    prev_jd: float | None = None

    while jd <= jd_end + 1e-12:
        lon = calc_ut_lon(jd, cfg.body, cfg.flags)
        d = abs(_signed_delta(lon, target))
        if d <= cfg.orb_deg and prev_jd is not None:
            br = _bracket_zero(prev_jd, jd, cfg)
            if br:
                jx = _bisection(br[0], br[1], cfg)
                y, m, d_, h = swe().revjul(jx, 1)
                hh = int(h)
                mm = int((h - hh) * 60)
                ss = int(round(((h - hh) * 60 - mm) * 60))
                hits.append((dt.datetime(y, m, d_, hh, mm, ss), d))
        prev_jd = jd
        jd += step_days

    return hits


# >>> AUTO-GEN END: performance core v1.0
