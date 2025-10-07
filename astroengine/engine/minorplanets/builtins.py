"""Curated minor planet definitions and Lilith longitude helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

from astroengine.core.time import ensure_utc, julian_day
from astroengine.ephemeris.cache import calc_ut_cached
from astroengine.ephemeris.swisseph_adapter import get_swisseph

__all__ = [
    "CuratedMinorPlanet",
    "DEFAULT_MINOR_BODY_ORBS",
    "CURATED_MINOR_PLANETS",
    "lilith_mean",
    "lilith_true",
]


_SWE_INITIALISED: bool = False


def _ensure_swisseph_path() -> None:
    """Initialise Swiss Ephemeris with the bundled stub data."""

    global _SWE_INITIALISED
    if _SWE_INITIALISED:
        return
    swe = get_swisseph()
    from pathlib import Path

    ephe_dir = Path(__file__).resolve().parents[3] / "datasets" / "swisseph_stub"
    swe().set_ephe_path(str(ephe_dir))
    _SWE_INITIALISED = True


def _calc_apogee_longitude(moment: datetime, body: int) -> float:
    """Return the ecliptic longitude for the requested apogee variant."""

    swe = get_swisseph()
    _ensure_swisseph_path()
    utc_moment = ensure_utc(moment)
    jd_ut = julian_day(utc_moment)
    xx, ret_flag = calc_ut_cached(jd_ut, int(body), 0)
    if ret_flag < 0:
        raise RuntimeError(f"Swiss ephemeris returned error code {ret_flag}")
    longitude = xx[0] % 360.0
    if longitude < 0.0:
        longitude += 360.0
    return float(longitude)


def lilith_mean(moment: datetime) -> float:
    """Return the mean Black Moon Lilith longitude in degrees."""

    swe = get_swisseph()
    return _calc_apogee_longitude(moment, swe().MEAN_APOG)


def lilith_true(moment: datetime) -> float:
    """Return the oscillating Black Moon Lilith longitude in degrees."""

    swe = get_swisseph()
    return _calc_apogee_longitude(moment, swe().OSCU_APOG)


@dataclass(frozen=True, slots=True)
class CuratedMinorPlanet:
    """Metadata describing curated non-MPC bodies."""

    name: str
    designation: str
    kind: str
    default_orb: float


DEFAULT_MINOR_BODY_ORBS: Final[dict[str, float]] = {
    "chiron": 2.0,
    "eris": 1.0,
    "sedna": 1.0,
    "haumea": 1.0,
    "makemake": 1.0,
    "ceres": 2.0,
    "pallas": 2.0,
    "juno": 2.0,
    "vesta": 2.0,
    "mean_lilith": 2.0,
    "true_lilith": 2.0,
    "large_numbered": 1.5,
    "default": 1.0,
}


CURATED_MINOR_PLANETS: Final[tuple[CuratedMinorPlanet, ...]] = (
    CuratedMinorPlanet("Chiron", "2060 Chiron", "centaur", DEFAULT_MINOR_BODY_ORBS["chiron"]),
    CuratedMinorPlanet("Eris", "136199 Eris", "tno", DEFAULT_MINOR_BODY_ORBS["eris"]),
    CuratedMinorPlanet("Sedna", "90377 Sedna", "tno", DEFAULT_MINOR_BODY_ORBS["sedna"]),
    CuratedMinorPlanet("Haumea", "136108 Haumea", "tno", DEFAULT_MINOR_BODY_ORBS["haumea"]),
    CuratedMinorPlanet("Makemake", "136472 Makemake", "tno", DEFAULT_MINOR_BODY_ORBS["makemake"]),
    CuratedMinorPlanet("Ceres", "1 Ceres", "dwarf", DEFAULT_MINOR_BODY_ORBS["ceres"]),
    CuratedMinorPlanet("Pallas", "2 Pallas", "asteroid", DEFAULT_MINOR_BODY_ORBS["pallas"]),
    CuratedMinorPlanet("Juno", "3 Juno", "asteroid", DEFAULT_MINOR_BODY_ORBS["juno"]),
    CuratedMinorPlanet("Vesta", "4 Vesta", "asteroid", DEFAULT_MINOR_BODY_ORBS["vesta"]),
    CuratedMinorPlanet("Black Moon Lilith (Mean)", "mean_lilith", "point", DEFAULT_MINOR_BODY_ORBS["mean_lilith"]),
    CuratedMinorPlanet("Black Moon Lilith (True)", "true_lilith", "point", DEFAULT_MINOR_BODY_ORBS["true_lilith"]),
)
