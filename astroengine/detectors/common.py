"""Shared helpers for Swiss-ephemeris backed detectors."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from ..ephemeris import BodyPosition, SwissEphemerisAdapter

__all__ = [
    "norm360",
    "delta_deg",
    "jd_to_iso",
    "iso_to_jd",
    "sun_lon",
    "moon_lon",
    "body_lon",
    "body_position",
    "solve_zero_crossing",
]

# --- Angle helpers -----------------------------------------------------------

def norm360(x: float) -> float:
    """Normalise ``x`` into the [0, 360) range."""

    x = math.fmod(x, 360.0)
    return x + 360.0 if x < 0 else x


def delta_deg(a: float, b: float) -> float:
    """Smallest signed angular difference ``a - b`` in degrees in [-180, +180]."""

    d = norm360(a) - norm360(b)
    if d > 180.0:
        d -= 360.0
    elif d < -180.0:
        d += 360.0
    return d


# --- Time helpers ------------------------------------------------------------
UNIX_EPOCH_JD = 2440587.5  # JD at 1970-01-01T00:00:00Z


def jd_to_iso(jd_ut: float) -> str:
    """Convert a Julian day (UT) to an ISO-8601 UTC timestamp."""

    seconds = (jd_ut - UNIX_EPOCH_JD) * 86400.0
    dt = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def iso_to_jd(iso_ts: str) -> float:
    """Convert an ISO-8601 timestamp into a Julian day (UT)."""

    dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    return (dt.timestamp() / 86400.0) + UNIX_EPOCH_JD


# --- Swiss Ephemeris access --------------------------------------------------


@dataclass
class _SwissCtx:
    ok: bool = False


_SWISS = _SwissCtx()

_BODY_CODES = {
    "sun": "SUN",
    "moon": "MOON",
    "mercury": "MERCURY",
    "venus": "VENUS",
    "mars": "MARS",
    "jupiter": "JUPITER",
    "saturn": "SATURN",
    "uranus": "URANUS",
    "neptune": "NEPTUNE",
    "pluto": "PLUTO",
    "ceres": "CERES",
    "pallas": "PALLAS",
    "juno": "JUNO",
    "vesta": "VESTA",
    "chiron": "CHIRON",
}


USE_CACHE = False


def enable_cache(flag: bool = True) -> None:
    """Toggle in-process caching for Swiss longitude helpers."""

    global USE_CACHE
    USE_CACHE = bool(flag)


try:  # pragma: no cover - cache is optional at runtime
    from ..cache.positions_cache import get_lon_daily  # type: ignore
except Exception:  # pragma: no cover - cache is optional
    get_lon_daily = None  # type: ignore


def _ensure_swiss() -> bool:
    """Ensure :mod:`swisseph` is importable and configured."""

    if _SWISS.ok:
        return True
    try:
        import swisseph as swe  # type: ignore

        from ..ephemeris.utils import get_se_ephe_path

        ephe = get_se_ephe_path(None)
        if ephe:
            swe.set_ephe_path(ephe)
        _SWISS.ok = True
        return True
    except Exception:
        return False


def sun_lon(jd_ut: float) -> float:
    """Return the geocentric ecliptic longitude of the Sun at ``jd_ut`` (UT)."""

    if not _ensure_swiss():  # pragma: no cover - exercised via tests
        raise RuntimeError("pyswisseph unavailable; install extras: astroengine[ephem]")
    import swisseph as swe  # type: ignore

    adapter = SwissEphemerisAdapter.get_default_adapter()
    return adapter.body_position(jd_ut, swe.SUN, body_name="Sun").longitude


def moon_lon(jd_ut: float) -> float:
    """Return the geocentric ecliptic longitude of the Moon at ``jd_ut`` (UT)."""

    if not _ensure_swiss():  # pragma: no cover - exercised via tests
        raise RuntimeError("pyswisseph unavailable; install extras: astroengine[ephem]")
    import swisseph as swe  # type: ignore

    adapter = SwissEphemerisAdapter.get_default_adapter()
    return adapter.body_position(jd_ut, swe.MOON, body_name="Moon").longitude


def body_lon(jd_ut: float, body_name: str) -> float:
    """Return the geocentric ecliptic longitude for ``body_name`` at ``jd_ut``."""

    cacheable_bodies = {
        "sun",
        "moon",
        "mercury",
        "venus",
        "mars",
        "jupiter",
        "saturn",
        "uranus",
        "neptune",
        "pluto",
        "ceres",
        "pallas",
        "juno",
        "vesta",
        "chiron",
    }
    adapter = SwissEphemerisAdapter.get_default_adapter()

    if (
        USE_CACHE
        and get_lon_daily is not None
        and body_name.lower() in cacheable_bodies
        and not adapter.is_sidereal
    ):
        return float(get_lon_daily(jd_ut, body_name))

    if not _ensure_swiss():
        raise RuntimeError("Swiss ephemeris unavailable (data files required)")

    import swisseph as swe  # type: ignore

    name = body_name.lower()
    code_name = _BODY_CODES.get(name)
    if code_name is None:
        raise KeyError(name)
    code = getattr(swe, code_name)
    position = adapter.body_position(jd_ut, code, body_name=body_name.title())
    return position.longitude


def body_position(jd_ut: float, body_name: str) -> BodyPosition:
    """Return the canonical body position for ``body_name`` at ``jd_ut``."""

    if not _ensure_swiss():
        raise RuntimeError("Swiss ephemeris unavailable (data files required)")

    import swisseph as swe  # type: ignore

    name = body_name.lower()
    code_name = _BODY_CODES.get(name)
    if code_name is None:
        raise KeyError(name)

    adapter = SwissEphemerisAdapter.get_default_adapter()
    code = getattr(swe, code_name)
    return adapter.body_position(jd_ut, code, body_name=body_name.title())


# --- Root finding ------------------------------------------------------------

def solve_zero_crossing(
    f: Callable[[float], float],
    a: float,
    b: float,
    *,
    max_iter: int = 64,
    tol: float = 1e-6,
    value_tol: float | None = None,
    tol_deg: float | None = None,
) -> float:
    """Return a root of ``f`` bracketed by ``a`` and ``b``."""

    fa = f(a)
    fb = f(b)
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    if fa * fb > 0.0:
        raise ValueError("Root not bracketed")

    left, right = a, b
    f_left, f_right = fa, fb
    root = left

    for _ in range(max_iter):
        if f_right != f_left:
            secant = right - f_right * (right - left) / (f_right - f_left)
        else:
            secant = None

        if secant is None or not (min(left, right) <= secant <= max(left, right)):
            mid = 0.5 * (left + right)
        else:
            mid = secant

        f_mid = f(mid)
        root = mid

        threshold = value_tol
        if threshold is None and tol_deg is not None:
            threshold = tol_deg
        if threshold is None:
            threshold = tol

        if abs(f_mid) <= threshold:
            return root
        if abs(right - left) <= tol:
            return root

        if f_left * f_mid <= 0.0:
            right, f_right = mid, f_mid
        else:
            left, f_left = mid, f_mid

    return root
