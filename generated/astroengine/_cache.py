# >>> AUTO-GEN BEGIN: swiss cache utils v1.0
from __future__ import annotations
import os
from functools import lru_cache

_SE_SET = False

def _lazy_import_swe():
    try:
        import swisseph as swe  # type: ignore
        return swe
    except Exception as e:
        raise RuntimeError("pyswisseph unavailable; ensure py311 and pyswisseph installed") from e

def set_ephe_from_env() -> None:
    """Set ephemeris path from SE_EPHE_PATH once (idempotent)."""
    global _SE_SET
    if _SE_SET:
        return
    p = os.getenv("SE_EPHE_PATH")
    if p:
        _lazy_import_swe().set_ephe_path(p)
    _SE_SET = True

@lru_cache(maxsize=200_000)
def calc_ut_lon(jd: float, body: int, flag: int = 0) -> float:
    """
    Cached ecliptic longitude (degrees) for (jd, body, flag).
    Cache key uses exact jd—upstream should quantize ticks if desired.
    """
    swe = _lazy_import_swe()
    lon = swe.calc_ut(jd, body, flag)[0][0]
    return lon % 360.0
# >>> AUTO-GEN END: swiss cache utils v1.0
