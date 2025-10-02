"""Divisional chart helpers (Navāṁśa, Daśāṁśa, and related Vargas)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Callable, Literal

from ...detectors.ingresses import ZODIAC_SIGNS, sign_index

__all__ = [
    "rasi_sign",
    "saptamsa_sign",
    "navamsa_sign",
    "dasamsa_sign",
    "trimsamsa_sign",
    "compute_varga",
]

NAVAMSA_SPAN = 30.0 / 9.0
DASAMSA_SPAN = 30.0 / 10.0
SAPTAMSA_SPAN = 30.0 / 7.0

MOVABLE_SIGNS = {0, 3, 6, 9}
FIXED_SIGNS = {1, 4, 7, 10}
DUAL_SIGNS = {2, 5, 8, 11}
ODD_SIGNS = {0, 2, 4, 6, 8, 10}
EVEN_SIGNS = {1, 3, 5, 7, 9, 11}

ODD_TRIMSAMSA = (
    (5.0, 0, "Mars"),
    (5.0, 10, "Saturn"),
    (8.0, 2, "Mercury"),
    (7.0, 6, "Venus"),
    (5.0, 8, "Jupiter"),
)
EVEN_TRIMSAMSA = (
    (5.0, 1, "Venus"),
    (5.0, 11, "Jupiter"),
    (8.0, 9, "Saturn"),
    (7.0, 7, "Mars"),
    (5.0, 5, "Mercury"),
)


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


def rasi_sign(longitude: float) -> tuple[int, float, dict[str, int | str]]:
    """Return the radix (D1) sign placement for ``longitude``."""

    sign_idx = sign_index(longitude)
    return sign_idx, _normalize(longitude), {}


def saptamsa_sign(longitude: float) -> tuple[int, float, dict[str, int | str]]:
    """Return the Saptāṁśa sign index, longitude, and segment for ``longitude``."""

    sign_idx = sign_index(longitude)
    deg = _deg_in_sign(longitude)
    segment = int(deg // SAPTAMSA_SPAN)
    if sign_idx in ODD_SIGNS:
        start_sign = sign_idx
    else:
        start_sign = (sign_idx + 6) % 12
    dest_sign = (start_sign + segment) % 12
    deg_in_segment = deg - (segment * SAPTAMSA_SPAN)
    saptamsa_longitude = (dest_sign * 30.0) + (deg_in_segment * 7.0)
    payload = {"segment": segment + 1}
    return dest_sign, saptamsa_longitude % 360.0, payload


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


def trimsamsa_sign(longitude: float) -> tuple[int, float, dict[str, int | str]]:
    """Return the Triṁśāṁśa sign, longitude, and ruler metadata for ``longitude``."""

    sign_idx = sign_index(longitude)
    deg = _deg_in_sign(longitude)
    segments = ODD_TRIMSAMSA if sign_idx in ODD_SIGNS else EVEN_TRIMSAMSA
    accumulated = 0.0
    for index, (width, dest_sign, ruler) in enumerate(segments, start=1):
        upper = accumulated + width
        if deg < upper or abs(deg - upper) < 1e-9:
            deg_in_segment = deg - accumulated
            scale = 30.0 / width
            trimsamsa_longitude = (dest_sign * 30.0) + (deg_in_segment * scale)
            payload = {"segment": index, "ruler": ruler}
            return dest_sign, trimsamsa_longitude % 360.0, payload
        accumulated = upper
    # Should never be reached, but fall back to final segment.
    width, dest_sign, ruler = segments[-1]
    scale = 30.0 / width
    trimsamsa_longitude = dest_sign * 30.0
    payload = {"segment": len(segments), "ruler": ruler}
    return dest_sign, trimsamsa_longitude % 360.0, payload


def _navamsa_payload(longitude: float) -> tuple[int, float, dict[str, int | str]]:
    sign_idx, lon, pada = navamsa_sign(longitude)
    return sign_idx, lon, {"pada": pada}


def _dasamsa_payload(longitude: float) -> tuple[int, float, dict[str, int | str]]:
    sign_idx, lon, part = dasamsa_sign(longitude)
    return sign_idx, lon, {"part": part}


VARGA_COMPUTERS: Mapping[str, Callable[[float], tuple[int, float, dict[str, int | str]]]] = {
    "D1": rasi_sign,
    "D7": saptamsa_sign,
    "D9": _navamsa_payload,
    "D10": _dasamsa_payload,
    "D30": trimsamsa_sign,
}


def compute_varga(
    natal_positions: Mapping[str, object],
    kind: Literal["D1", "D7", "D9", "D10", "D30"],
    *,
    ascendant: float | None = None,
) -> dict[str, dict[str, float | int | str]]:
    """Compute varga placements for ``natal_positions``."""

    try:
        compute = VARGA_COMPUTERS[kind.upper()]
    except KeyError as exc:  # pragma: no cover - guarded by caller
        raise ValueError("Unsupported varga kind") from exc

    results: dict[str, dict[str, float | int | str]] = {}
    for name, position in natal_positions.items():
        longitude = getattr(position, "longitude", None)
        if longitude is None:
            continue
        sign_idx, lon, extra = compute(longitude)
        payload: dict[str, float | int | str] = {
            "longitude": lon,
            "sign": ZODIAC_SIGNS[sign_idx],
            "sign_index": sign_idx,
        }
        payload.update(extra)
        results[name] = payload

    if ascendant is not None:
        sign_idx, lon, extra = compute(ascendant)
        payload = {
            "longitude": lon,
            "sign": ZODIAC_SIGNS[sign_idx],
            "sign_index": sign_idx,
        }
        payload.update(extra)
        results["Ascendant"] = payload

    return results
