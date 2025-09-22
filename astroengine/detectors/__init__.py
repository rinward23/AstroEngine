"""High-level detector helpers exposed by :mod:`astroengine`."""

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
from ..utils.angles import classify_applying_separating, delta_angle, is_within_orb

__all__ = [
    "CoarseHit",
    "detect_decl_contacts",
    "detect_antiscia_contacts",
    "find_lunations",
    "find_eclipses",
    "find_stations",
    "find_out_of_bounds",
    "secondary_progressions",
    "solar_arc_directions",
    "solar_lunar_returns",
]


@dataclass(frozen=True)
class CoarseHit:
    """Represents a coarse declination/antiscia contact hit."""

    kind: str
    when_iso: str
    moving: str
    target: str
    lon_moving: float
    lon_target: float
    dec_moving: float
    dec_target: float
    delta: float
    applying_or_separating: str


def detect_decl_contacts(
    provider,
    iso_ticks: Iterable[str],
    moving: str,
    target: str,
    orb_deg_parallel: float = 0.5,
    orb_deg_contra: float = 0.5,
) -> List[CoarseHit]:
    """Detect declination parallels/contraparallels across ``iso_ticks``."""

    out: List[CoarseHit] = []
    for iso in iso_ticks:
        positions = provider.positions_ecliptic(iso, [moving, target])
        lon_moving = float(positions[moving]["lon"])
        lon_target = float(positions[target]["lon"])
        dec_moving = ecl_to_dec(lon_moving)
        dec_target = ecl_to_dec(lon_target)
        speed = float(positions[moving].get("speed_lon", 0.0))

        if is_parallel(dec_moving, dec_target, orb_deg_parallel):
            delta = dec_moving - dec_target
            motion = classify_applying_separating(lon_moving, speed, lon_target)
            out.append(
                CoarseHit(
                    kind="decl_parallel",
                    when_iso=iso,
                    moving=moving,
                    target=target,
                    lon_moving=lon_moving,
                    lon_target=lon_target,
                    dec_moving=dec_moving,
                    dec_target=dec_target,
                    delta=delta,
                    applying_or_separating=motion,
                )
            )
        elif is_contraparallel(dec_moving, dec_target, orb_deg_contra):
            delta = dec_moving + dec_target
            motion = classify_applying_separating(lon_moving, speed, lon_target)
            out.append(
                CoarseHit(
                    kind="decl_contra",
                    when_iso=iso,
                    moving=moving,
                    target=target,
                    lon_moving=lon_moving,
                    lon_target=lon_target,
                    dec_moving=dec_moving,
                    dec_target=dec_target,
                    delta=delta,
                    applying_or_separating=motion,
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
    """Detect antiscia and contra-antiscia contacts across ``iso_ticks``."""

    out: List[CoarseHit] = []
    for iso in iso_ticks:
        positions = provider.positions_ecliptic(iso, [moving, target])
        lon_moving = float(positions[moving]["lon"])
        lon_target = float(positions[target]["lon"])
        speed = float(positions[moving].get("speed_lon", 0.0))
        dec_moving = ecl_to_dec(lon_moving)
        dec_target = ecl_to_dec(lon_target)

        anti_lon = antiscia_lon(lon_moving)
        contra_lon = contra_antiscia_lon(lon_moving)

        d_anti = delta_angle(anti_lon, lon_target)
        if is_within_orb(d_anti, orb_deg_antiscia):
            motion = classify_applying_separating(lon_moving, speed, anti_lon)
            out.append(
                CoarseHit(
                    kind="antiscia",
                    when_iso=iso,
                    moving=moving,
                    target=target,
                    lon_moving=lon_moving,
                    lon_target=lon_target,
                    dec_moving=dec_moving,
                    dec_target=dec_target,
                    delta=d_anti,
                    applying_or_separating=motion,
                )
            )

        d_contra = delta_angle(contra_lon, lon_target)
        if is_within_orb(d_contra, orb_deg_contra):
            motion = classify_applying_separating(lon_moving, speed, contra_lon)
            out.append(
                CoarseHit(
                    kind="contra_antiscia",
                    when_iso=iso,
                    moving=moving,
                    target=target,
                    lon_moving=lon_moving,
                    lon_target=lon_target,
                    dec_moving=dec_moving,
                    dec_target=dec_target,
                    delta=d_contra,
                    applying_or_separating=motion,
                )
            )
    return out


from .directions import solar_arc_directions  # noqa: E402
from .eclipses import find_eclipses  # noqa: E402
from .lunations import find_lunations  # noqa: E402
from .out_of_bounds import find_out_of_bounds  # noqa: E402
from .progressions import secondary_progressions  # noqa: E402
from .returns import solar_lunar_returns  # noqa: E402
from .stations import find_stations  # noqa: E402

__all__ = sorted(set(__all__))
