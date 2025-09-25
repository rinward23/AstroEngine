"""High-level detector helpers exposed by :mod:`astroengine`."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from ..astro.declination import (
    DEFAULT_ANTISCIA_AXIS,
    antiscia_lon,
    contra_antiscia_lon,
    ecl_to_dec,
    is_contraparallel,
    is_parallel,
)
from ..refine import adaptive_corridor_width
from ..utils.angles import classify_applying_separating, delta_angle, is_within_orb

__all__ = [
    "CoarseHit",
    "detect_decl_contacts",
    "detect_antiscia_contacts",
    "find_lunations",
    "find_eclipses",
    "find_stations",
    "find_sign_ingresses",
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
    mirror_lon: float | None = None
    axis: str | None = None
    orb_allow: float | None = None
    corridor_width_deg: float | None = None
    corridor_profile: str | None = None


def _extract_declination(data: Mapping[str, float], fallback_lon: float) -> float:
    for key in ("declination", "dec", "decl"):
        if key in data:
            try:
                return float(data[key])
            except (TypeError, ValueError):  # pragma: no cover - defensive
                continue
    return ecl_to_dec(fallback_lon)


def detect_decl_contacts(
    provider,
    iso_ticks: Iterable[str],
    moving: str,
    target: str,
    orb_deg_parallel: float = 0.5,
    orb_deg_contra: float = 0.5,
) -> list[CoarseHit]:
    """Detect declination parallels/contraparallels across ``iso_ticks``."""

    out: list[CoarseHit] = []
    allow_parallel = float(orb_deg_parallel if orb_deg_parallel is not None else 0.5)
    allow_contra = float(orb_deg_contra if orb_deg_contra is not None else 0.5)
    corridor_profile = "gaussian"
    for iso in iso_ticks:
        positions = provider.positions_ecliptic(iso, [moving, target])
        pos_moving = positions.get(moving)
        pos_target = positions.get(target)
        if not pos_moving or not pos_target:
            continue

        lon_moving = float(pos_moving.get("lon", 0.0))
        lon_target = float(pos_target.get("lon", 0.0))
        dec_moving = _extract_declination(pos_moving, lon_moving)
        dec_target = _extract_declination(pos_target, lon_target)
        speed_moving = float(pos_moving.get("speed_lon", 0.0))
        speed_target = float(pos_target.get("speed_lon", 0.0))
        retrograde = speed_moving < 0 or speed_target < 0

        if is_parallel(dec_moving, dec_target, orb_deg_parallel):
            delta = dec_moving - dec_target
            motion = classify_applying_separating(lon_moving, speed_moving, lon_target)
            corridor_width = adaptive_corridor_width(
                allow_parallel,
                speed_moving,
                speed_target,
                retrograde=retrograde,
                aspect_strength=1.0,
                minimum_orb_deg=0.1,
            )
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
                    orb_allow=allow_parallel,
                    corridor_width_deg=corridor_width,
                    corridor_profile=corridor_profile,
                )
            )
        elif is_contraparallel(dec_moving, dec_target, orb_deg_contra):
            delta = dec_moving + dec_target
            motion = classify_applying_separating(lon_moving, speed_moving, lon_target)
            corridor_width = adaptive_corridor_width(
                allow_contra,
                speed_moving,
                speed_target,
                retrograde=retrograde,
                aspect_strength=1.0,
                minimum_orb_deg=0.1,
            )
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
                    orb_allow=allow_contra,
                    corridor_width_deg=corridor_width,
                    corridor_profile=corridor_profile,
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
    *,
    axis: str = DEFAULT_ANTISCIA_AXIS,
) -> list[CoarseHit]:
    """Detect antiscia and contra-antiscia contacts across ``iso_ticks``."""

    out: list[CoarseHit] = []
    allow_antiscia = float(orb_deg_antiscia if orb_deg_antiscia is not None else 2.0)
    allow_contra = float(orb_deg_contra if orb_deg_contra is not None else 2.0)
    corridor_profile = "gaussian"
    for iso in iso_ticks:
        positions = provider.positions_ecliptic(iso, [moving, target])
        pos_moving = positions.get(moving)
        pos_target = positions.get(target)
        if not pos_moving or not pos_target:
            continue

        lon_moving = float(pos_moving.get("lon", 0.0))
        lon_target = float(pos_target.get("lon", 0.0))
        speed_moving = float(pos_moving.get("speed_lon", 0.0))
        speed_target = float(pos_target.get("speed_lon", 0.0))
        retrograde = speed_moving < 0 or speed_target < 0
        dec_moving = _extract_declination(pos_moving, lon_moving)
        dec_target = _extract_declination(pos_target, lon_target)

        anti_lon = antiscia_lon(lon_moving, axis=axis)
        contra_lon = contra_antiscia_lon(lon_moving, axis=axis)

        d_anti = delta_angle(anti_lon, lon_target)
        if is_within_orb(d_anti, orb_deg_antiscia):
            motion = classify_applying_separating(lon_moving, speed_moving, anti_lon)
            corridor_width = adaptive_corridor_width(
                allow_antiscia,
                speed_moving,
                speed_target,
                retrograde=retrograde,
                aspect_strength=1.0,
                minimum_orb_deg=0.1,
            )
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
                    mirror_lon=anti_lon,
                    axis=axis,
                    orb_allow=allow_antiscia,
                    corridor_width_deg=corridor_width,
                    corridor_profile=corridor_profile,
                )
            )

        d_contra = delta_angle(contra_lon, lon_target)
        if is_within_orb(d_contra, orb_deg_contra):
            motion = classify_applying_separating(lon_moving, speed_moving, contra_lon)
            corridor_width = adaptive_corridor_width(
                allow_contra,
                speed_moving,
                speed_target,
                retrograde=retrograde,
                aspect_strength=1.0,
                minimum_orb_deg=0.1,
            )
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
                    mirror_lon=contra_lon,
                    axis=axis,
                    orb_allow=allow_contra,
                    corridor_width_deg=corridor_width,
                    corridor_profile=corridor_profile,
                )
            )
    return out


from .directions import solar_arc_directions  # noqa: E402
from .eclipses import find_eclipses  # noqa: E402

_INGRESS_IMPORT_ERROR: SyntaxError | None = None

try:  # pragma: no cover - optional when ingress module is syntactically unavailable
    from .ingresses import find_sign_ingresses  # noqa: E402
except SyntaxError as exc:  # pragma: no cover - defensive for partial builds
    _INGRESS_IMPORT_ERROR = exc

    def find_sign_ingresses(*_args, **_kwargs):  # type: ignore

        raise RuntimeError(
            "sign ingress detector unavailable"
        ) from _INGRESS_IMPORT_ERROR



from .lunations import find_lunations  # noqa: E402
from .out_of_bounds import find_out_of_bounds  # noqa: E402
from .progressions import secondary_progressions  # noqa: E402
from .returns import solar_lunar_returns  # noqa: E402
from .stations import find_stations  # noqa: E402

__all__ = sorted(set(__all__))
