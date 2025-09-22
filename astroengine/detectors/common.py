
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
import math
from datetime import datetime, timezone, timedelta

__all__ = [
    "norm360",
    "delta_deg",
    "jd_to_iso",
    "iso_to_jd",
    "sun_lon",
    "moon_lon",
    "body_lon",
    "solve_zero_crossing",
]

# --- Angle helpers -----------------------------------------------------------

def norm360(x: float) -> float:
    x = math.fmod(x, 360.0)
    return x + 360.0 if x < 0 else x


def delta_deg(a: float, b: float) -> float:
    """Signed smallest angular difference a-b in degrees in [-180, +180]."""
    d = norm360(a) - norm360(b)
    if d > 180.0:
        d -= 360.0
    elif d < -180.0:
        d += 360.0
    return d


# --- Time helpers ------------------------------------------------------------
UNIX_EPOCH_JD = 2440587.5  # JD at 1970-01-01T00:00:00Z


def jd_to_iso(jd_ut: float) -> str:
    seconds = (jd_ut - UNIX_EPOCH_JD) * 86400.0
    dt = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)
    return dt.replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def iso_to_jd(iso_ts: str) -> float:
    dt = datetime.fromisoformat(iso_ts.replace('Z', '+00:00')).astimezone(timezone.utc)
    return (dt.timestamp() / 86400.0) + UNIX_EPOCH_JD




# --- Swiss Ephemeris access --------------------------------------------------
@dataclass
class _SwissCtx:
    ok: bool


_SWISS = _SwissCtx(ok=False)

# >>> AUTO-GEN BEGIN: detector-common-cache-toggle v1.0
USE_CACHE = False


def enable_cache(flag: bool = True) -> None:
    global USE_CACHE
    USE_CACHE = bool(flag)
# >>> AUTO-GEN END: detector-common-cache-toggle v1.0

# >>> AUTO-GEN BEGIN: detector-common-cached-body v1.0
try:
    from ..cache.positions_cache import get_lon_daily  # type: ignore
except Exception:  # pragma: no cover
    get_lon_daily = None  # type: ignore
# >>> AUTO-GEN END: detector-common-cached-body v1.0


def _ensure_swiss() -> bool:
    if _SWISS.ok:
        return True
    try:
        import swisseph as swe  # type: ignore
        from ..ephemeris.utils import get_se_ephe_path  # local helper
        ephe = get_se_ephe_path(None)
        if ephe:
            swe.set_ephe_path(ephe)
        _SWISS.ok = True
        return True
    except Exception:
        return False


def sun_lon(jd_ut: float) -> float:
    if not _ensure_swiss():
        raise RuntimeError("pyswisseph unavailable; install extras: astroengine[ephem]")
    import swisseph as swe  # type: ignore
    lon, lat, dist, speed_lon = swe.calc_ut(jd_ut, swe.SUN)
    return float(lon)


def moon_lon(jd_ut: float) -> float:
    if not _ensure_swiss():
        raise RuntimeError("pyswisseph unavailable; install extras: astroengine[ephem]")
    import swisseph as swe  # type: ignore
    lon, lat, dist, speed_lon = swe.calc_ut(jd_ut, swe.MOON)
    return float(lon)



def body_lon(jd_ut: float, body_name: str) -> float:  # replace previous block if present
    if USE_CACHE and get_lon_daily is not None and body_name.lower() in {"sun","moon","mercury","venus","mars","jupiter","saturn","uranus","neptune","pluto"}:
        return float(get_lon_daily(jd_ut, body_name))
    # fallback to strict Swiss path below
    if not _ensure_swiss():
        raise RuntimeError("Swiss ephemeris unavailable (data files required)")
    import swisseph as swe  # type: ignore
    name = body_name.lower()
    code = {
        'sun': swe.SUN, 'moon': swe.MOON,
        'mercury': swe.MERCURY, 'venus': swe.VENUS, 'mars': swe.MARS,
        'jupiter': swe.JUPITER, 'saturn': swe.SATURN, 'uranus': swe.URANUS, 'neptune': swe.NEPTUNE, 'pluto': swe.PLUTO,
    }[name]
    lon, lat, dist, speed_lon = swe.calc_ut(jd_ut, code)
    return float(lon)


# --- Root finding ------------------------------------------------------------


def solve_zero_crossing(
    f: Callable[[float], float],
    a: float,
    b: float,
    *,
    tol_deg: float = 1e-5,
    max_iter: int = 64,
) -> float:
    """Return the root of ``f`` inside ``[a, b]`` using a safe secant/bisection mix."""

    fa = f(a)
    fb = f(b)
    if math.isnan(fa) or math.isnan(fb):
        raise ValueError("Root function returned NaN for bracket endpoints")
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    if fa * fb > 0:
        raise ValueError("Root bracket does not straddle zero")

    x0, f0 = a, fa
    x1, f1 = b, fb
    for _ in range(max_iter):
        # Attempt a secant update first for faster convergence.
        if f1 != f0:
            x2 = x1 - f1 * (x1 - x0) / (f1 - f0)
        else:
            x2 = 0.5 * (x0 + x1)

        # Ensure the candidate remains inside the bracket; fall back to bisection.
        if not (min(x0, x1) <= x2 <= max(x0, x1)):
            x2 = 0.5 * (x0 + x1)

        f2 = f(x2)
        if abs(f2) <= tol_deg:
            return x2

        if f0 * f2 <= 0:
            x1, f1 = x2, f2
        else:
            x0, f0 = x2, f2

    return 0.5 * (x0 + x1)

