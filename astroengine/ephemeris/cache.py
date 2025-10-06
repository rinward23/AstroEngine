from __future__ import annotations

from functools import lru_cache

from .swe import swe


@lru_cache(maxsize=200_000)
def calc_ut_cached(jd: float, ipl: int, flags: int = 0):
    """Cached wrapper for swe().calc_ut; speeds up transit/electional scans."""
    return swe().calc_ut(jd, ipl, flags)


@lru_cache(maxsize=200_000)
def julday_cached(y: int, m: int, d: int, ut: float):
    """Cached wrapper for swe().julday; avoids recomputing repeated JDs."""
    return swe().julday(y, m, d, ut)
