"""Divisional chart helpers (Navāṁśa and Daśāṁśa)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from ...detectors.ingresses import ZODIAC_SIGNS, sign_index

__all__ = ["navamsa_sign", "dasamsa_sign", "compute_varga"]

NAVAMSA_SPAN = 30.0 / 9.0
DASAMSA_SPAN = 30.0 / 10.0

MOVABLE_SIGNS = {0, 3, 6, 9}
FIXED_SIGNS = {1, 4, 7, 10}
DUAL_SIGNS = {2, 5, 8, 11}


def _normalize(longitude: float) -> float:
    return float(longitude) % 360.0


def _deg_in_sign(longitude: float) -> float:
    return _normalize(longitude) % 30.0


def _modal_start(sign_idx: int) -> int:
    if sign_idx in MOVABLE_SIGNS:
        return sign_idx
    if sign_idx in FIXED_SIGNS:
        return (sign_idx + 8) % 12
    return (sign_idx + 4) % 12  # dual signs


def navamsa_sign(longitude: float) -> tuple[int, float, int]:
    """Return the Navāṁśa sign index, longitude, and pada for ``longitude``."""

    sign_idx = sign_index(longitude)
    deg = _deg_in_sign(longitude)
    pada_index = int(deg // NAVAMSA_SPAN)
    start_sign = _modal_start(sign_idx)
    dest_sign = (start_sign + pada_index) % 12
    deg_in_pada = deg - (pada_index * NAVAMSA_SPAN)
    navamsa_longitude = (dest_sign * 30.0) + (deg_in_pada * 9.0)
    return dest_sign, navamsa_longitude % 360.0, pada_index + 1


def dasamsa_sign(longitude: float) -> tuple[int, float, int]:
    """Return the Daśāṁśa sign index, longitude, and decan for ``longitude``."""

    sign_idx = sign_index(longitude)
    deg = _deg_in_sign(longitude)
    part_index = int(deg // DASAMSA_SPAN)
    start_sign = _modal_start(sign_idx)
    dest_sign = (start_sign + part_index) % 12
    deg_in_part = deg - (part_index * DASAMSA_SPAN)
    dasamsa_longitude = (dest_sign * 30.0) + (deg_in_part * 10.0)
    return dest_sign, dasamsa_longitude % 360.0, part_index + 1


def compute_varga(
    natal_positions: Mapping[str, object],
    kind: Literal["D9", "D10"],
    *,
    ascendant: float | None = None,
) -> dict[str, dict[str, float | int | str]]:
    """Compute varga placements for ``natal_positions``."""

    results: dict[str, dict[str, float | int | str]] = {}
    for name, position in natal_positions.items():
        longitude = getattr(position, "longitude", None)
        if longitude is None:
            continue
        if kind.upper() == "D9":
            sign_idx, lon, pada = navamsa_sign(longitude)
            results[name] = {
                "longitude": lon,
                "sign": ZODIAC_SIGNS[sign_idx],
                "sign_index": sign_idx,
                "pada": pada,
            }
        elif kind.upper() == "D10":
            sign_idx, lon, part = dasamsa_sign(longitude)
            results[name] = {
                "longitude": lon,
                "sign": ZODIAC_SIGNS[sign_idx],
                "sign_index": sign_idx,
                "part": part,
            }
        else:  # pragma: no cover - guarded by caller
            raise ValueError("Unsupported varga kind")

    if ascendant is not None:
        if kind.upper() == "D9":
            sign_idx, lon, pada = navamsa_sign(ascendant)
            results["Ascendant"] = {
                "longitude": lon,
                "sign": ZODIAC_SIGNS[sign_idx],
                "sign_index": sign_idx,
                "pada": pada,
            }
        else:
            sign_idx, lon, part = dasamsa_sign(ascendant)
            results["Ascendant"] = {
                "longitude": lon,
                "sign": ZODIAC_SIGNS[sign_idx],
                "sign_index": sign_idx,
                "part": part,
            }

    return results
