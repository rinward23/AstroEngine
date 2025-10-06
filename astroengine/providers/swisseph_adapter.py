"""Swiss Ephemeris helpers for variant-sensitive bodies (nodes, Lilith)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Tuple

logger = logging.getLogger(__name__)

from astroengine.ephemeris.swe import has_swe, swe

if not has_swe():  # pragma: no cover - optional dependency in some environments
    logger.info(
        "pyswisseph not installed",
        extra={"err_code": "SWISSEPH_IMPORT"},
        exc_info=True,
    )

from ..core.bodies import canonical_name
from ..ephemeris.cache import calc_ut_cached

SE_SUN = int(getattr(swe(), "SUN", 0)) if has_swe() else 0
SE_MOON = int(getattr(swe(), "MOON", 1)) if has_swe() else 1
SE_MEAN_NODE = int(getattr(swe(), "MEAN_NODE", 10)) if has_swe() else 10
SE_TRUE_NODE = int(getattr(swe(), "TRUE_NODE", 11)) if has_swe() else 11
SE_MEAN_APOG = int(getattr(swe(), "MEAN_APOG", 12)) if has_swe() else 12
SE_OSCU_APOG = int(getattr(swe(), "OSCU_APOG", 13)) if has_swe() else 13


@dataclass(frozen=True)
class VariantConfig:
    nodes_variant: str = "mean"
    lilith_variant: str = "mean"


def se_body_id_for(name: str, vc: VariantConfig) -> Tuple[int, bool]:
    """Return ``(id, derived)`` for ``name`` respecting variant config."""

    canonical = canonical_name(name)
    if canonical in {"mean_node", "north_node", "node"}:
        return (SE_TRUE_NODE if vc.nodes_variant == "true" else SE_MEAN_NODE, False)
    if canonical == "true_node":
        return SE_TRUE_NODE, False
    if canonical in {"south_node", "sn"}:
        code = SE_TRUE_NODE if vc.nodes_variant == "true" else SE_MEAN_NODE
        return code, True
    if canonical in {"lilith", "black_moon_lilith", "mean_lilith"}:
        return (SE_OSCU_APOG if vc.lilith_variant == "true" else SE_MEAN_APOG, False)
    if canonical == "true_lilith":
        return SE_OSCU_APOG, False
    return -1, False


def position_vec(body_id: int, jd_ut: float, *, flags: int = 0):
    if swe is None:
        raise RuntimeError("pyswisseph not available")
    values, ret_flag = calc_ut_cached(jd_ut, body_id, flags)
    if ret_flag < 0:
        raise RuntimeError(f"Swiss ephemeris returned error code {ret_flag}")
    return tuple(values)


def position_with_variants(name: str, jd_ut: float, vc: VariantConfig, *, flags: int = 0):
    """Return Swiss ephemeris vector for ``name`` considering variants."""

    body_id, derived = se_body_id_for(name, vc)
    if body_id < 0:
        raise LookupError(name)
    values = position_vec(body_id, jd_ut, flags=flags)
    if not derived:
        return values
    lon, lat, dist, lon_spd, lat_spd, dist_spd = values
    lon = (lon + 180.0) % 360.0
    lat = -lat
    lon_spd = lon_spd
    lat_spd = -lat_spd
    return lon, lat, dist, lon_spd, lat_spd, dist_spd


__all__ = [
    "VariantConfig",
    "position_vec",
    "position_with_variants",
    "se_body_id_for",
]
