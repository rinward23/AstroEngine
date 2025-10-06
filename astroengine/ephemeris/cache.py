"""Swiss Ephemeris call caches."""

from __future__ import annotations

from functools import lru_cache

from .swe import swe

__all__ = ["calc_ut_cached"]


@lru_cache(maxsize=200_000)
def calc_ut_cached(jd: float, ipl: int, flags: int = 0):
    """Return cached :func:`swisseph.calc_ut` results for ``(jd, ipl, flags)``."""

    return swe().calc_ut(jd, ipl, flags)
