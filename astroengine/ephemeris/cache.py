from __future__ import annotations

from functools import lru_cache

from .swe import swe


def _init_ephe(*args, **kwargs):
    from astroengine.engine.ephe_runtime import init_ephe as _init

    return _init(*args, **kwargs)


@lru_cache(maxsize=200_000)
def calc_ut_cached(jd: float, ipl: int, flags: int = 0):
    """Cached wrapper for swe().calc_ut; speeds up transit/electional scans."""
    base_flags = _init_ephe()
    return swe().calc_ut(jd, ipl, flags | base_flags)


@lru_cache(maxsize=200_000)
def julday_cached(y: int, m: int, d: int, ut: float):
    """Cached wrapper for swe().julday; avoids recomputing repeated JDs."""
    _init_ephe()
    return swe().julday(y, m, d, ut)
