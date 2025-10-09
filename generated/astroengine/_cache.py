# >>> AUTO-GEN BEGIN: swiss cache utils v1.0
from __future__ import annotations

from functools import lru_cache

from astroengine.engine.ephe_runtime import init_ephe


def _lazy_import_swe():
    try:
        from astroengine.ephemeris.swe import swe

        return swe
    except Exception as e:
        raise RuntimeError(
            "pyswisseph unavailable; ensure py311 and pyswisseph installed"
        ) from e


def ensure_ephe_initialized() -> int:
    """Initialise Swiss ephemeris runtime and return default flags."""

    return init_ephe()


@lru_cache(maxsize=200_000)
def calc_ut_lon(jd: float, body: int, flag: int = 0) -> float:
    """
    Cached ecliptic longitude (degrees) for (jd, body, flag).
    Cache key uses exact jd—upstream should quantize ticks if desired.
    """
    swe = _lazy_import_swe()
    flags = flag | ensure_ephe_initialized()
    lon = swe().calc_ut(jd, body, flags)[0][0]
    return lon % 360.0


# >>> AUTO-GEN END: swiss cache utils v1.0
