"""Swiss Ephemeris helpers for variant-sensitive bodies (nodes, Lilith)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

try:  # pragma: no cover - optional dependency in some environments
    import swisseph as swe
except Exception:  # pragma: no cover
    swe = None

from ..core.bodies import canonical_name

SE_SUN = getattr(swe, "SUN", 0) if swe else 0
SE_MOON = getattr(swe, "MOON", 1) if swe else 1
SE_MEAN_NODE = getattr(swe, "MEAN_NODE", 10) if swe else 10
SE_TRUE_NODE = getattr(swe, "TRUE_NODE", 11) if swe else 11
SE_MEAN_APOG = getattr(swe, "MEAN_APOG", 12) if swe else 12
SE_OSCU_APOG = getattr(swe, "OSCU_APOG", 13) if swe else 13


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
    values, rc = swe.calc_ut(jd_ut, body_id, flags)
    if rc < 0:
        raise RuntimeError(f"swe.calc_ut failed with code {rc}")
    return values


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
