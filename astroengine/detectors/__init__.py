from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from ..astro.declination import (
    antiscia_lon,
    contra_antiscia_lon,
    ecl_to_dec,
    is_contraparallel,
    is_parallel,
)
from ..utils.angles import (
    classify_applying_separating,
    delta_angle,
    is_within_orb,
)
from .common import jd_to_iso  # ENSURE-LINE noqa: F401
from .common import norm360, delta_deg, refine_zero_secant_bisect  # ENSURE-LINE noqa: F401

from .lunations import find_lunations  # noqa: F401
from .returns import solar_lunar_returns  # noqa: F401
from .stations import find_stations  # noqa: F401

__all__ = [
    "CoarseHit",
    "detect_decl_contacts",
    "detect_antiscia_contacts",
    "find_lunations",
    "find_stations",
    "solar_lunar_returns",
]


@dataclass
class CoarseHit:
    kind: str  # 'decl_parallel', 'decl_contra', 'antiscia', 'contra_antiscia'
    when_iso: str
    moving: str
    target: str
    lon_moving: float
    lon_target: float
    dec_moving: float
    dec_target: float
    delta: float  # signed longitudinal delta for mirrors; decl delta for decl aspects
    applying_or_separating: str


def detect_decl_contacts(
    provider,
    iso_ticks: Iterable[str],
    moving: str,
    target: str,
    orb_deg_parallel: float = 0.5,
    orb_deg_contra: float = 0.5,
) -> List[CoarseHit]:
    out: List[CoarseHit] = []
    for t in iso_ticks:
        pos = provider.positions_ecliptic(t, [moving, target])
        lm = pos[moving]["lon"]
        lt = pos[target]["lon"]
        dm = ecl_to_dec(lm)
        dt = ecl_to_dec(lt)
        if is_parallel(dm, dt, orb_deg_parallel):
            out.append(
                CoarseHit(
                    "decl_parallel",
                    t,
                    moving,
                    target,
                    lm,
                    lt,
                    dm,
                    dt,
                    dm - dt,
                    classify_applying_separating(
                        lm,
                        pos[moving].get("speed_lon", 0.0),
                        lt,
                    ),
                )
            )
        elif is_contraparallel(dm, dt, orb_deg_contra):
            out.append(
                CoarseHit(
                    "decl_contra",
                    t,
                    moving,
                    target,
                    lm,
                    lt,
                    dm,
                    dt,
                    dm + dt,
                    classify_applying_separating(
                        lm,
                        pos[moving].get("speed_lon", 0.0),
                        lt,
                    ),
                )
            )
    return out


def detect_antiscia_contacts(
    provider,
    iso_ticks: Iterable[str],
    moving: str,
    target: str,
    orb_deg_antiscia: float = 2.0,
    orb_deg_contra: float = 2.0,
) -> List[CoarseHit]:
    out: List[CoarseHit] = []
    for t in iso_ticks:
        pos = provider.positions_ecliptic(t, [moving, target])
        lm = pos[moving]["lon"]
        lt = pos[target]["lon"]
        anti = antiscia_lon(lm)
        contra = contra_antiscia_lon(lm)
        d_anti = delta_angle(anti, lt)
        d_contra = delta_angle(contra, lt)
        spd = pos[moving].get("speed_lon", 0.0)
        if is_within_orb(d_anti, orb_deg_antiscia):
            out.append(
                CoarseHit(
                    "antiscia",
                    t,
                    moving,
                    target,
                    lm,
                    lt,
                    ecl_to_dec(lm),
                    ecl_to_dec(lt),
                    d_anti,
                    classify_applying_separating(anti, spd, lt),
                )
            )
        if is_within_orb(d_contra, orb_deg_contra):
            out.append(
                CoarseHit(
                    "contra_antiscia",
                    t,
                    moving,
                    target,
                    lm,
                    lt,
                    ecl_to_dec(lm),
                    ecl_to_dec(lt),
                    d_contra,
                    classify_applying_separating(contra, spd, lt),
                )
            )
    return out
