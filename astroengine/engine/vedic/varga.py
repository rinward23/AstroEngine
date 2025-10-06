
"""Divisional chart helpers for Vedic vargas.

The module originally exposed only Navāṁśa (D9) and Daśāṁśa (D10).  This
revision generalises the implementation so additional vargas can reuse the
same bookkeeping while documenting the sign-subdivision rule that each chart
uses.  Consumers that still call :func:`navamsa_sign` or :func:`dasamsa_sign`
receive the same tuple payloads as before, but richer metadata (including the
source sign that counting began from) is made available via
``compute_varga``.
"""


from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from math import floor
from typing import Literal

from ...detectors.ingresses import ZODIAC_SIGNS, sign_index

__all__ = [
    "rasi_sign",
    "saptamsa_sign",
    "navamsa_sign",
    "dasamsa_sign",
    "trimsamsa_sign",
    "compute_varga",
]



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



def _is_odd_sign(sign_idx: int) -> bool:
    # Aries (index 0) is an odd sign, so use even indices for odd signs.
    return sign_idx % 2 == 0


def _odd_even_start(even_offset: int) -> Callable[[int], int]:
    def _inner(sign_idx: int) -> int:
        if _is_odd_sign(sign_idx):
            return sign_idx
        return (sign_idx + even_offset) % 12

    return _inner


def _drekkana_dest(sign_idx: int, part_index: int) -> int:
    return (sign_idx + (part_index * 4)) % 12


def _sequential_dest(start_fn: Callable[[int], int]) -> Callable[[int, int], int]:
    def _inner(sign_idx: int, part_index: int) -> int:
        return (start_fn(sign_idx) + part_index) % 12

    return _inner


def rasi_sign(longitude: float) -> tuple[int, float, dict[str, int | str]]:
    """Return the rāśi (sign) index for ``longitude`` with metadata."""

    sign_idx = sign_index(longitude)
    lon = _normalize(longitude)
    return sign_idx, lon, {
        "sign": ZODIAC_SIGNS[sign_idx],
        "sign_index": sign_idx,
        "segment_arc_degrees": 30.0,
        "rule": "Base rāśi positions use the natal sign without subdivision.",
    }


def saptamsa_sign(longitude: float) -> tuple[int, float, dict[str, int | str]]:
    """Return the Saptāṁśa (D7) placement metadata for ``longitude``."""

    definition = VARGA_DEFINITIONS["D7"]
    dest_sign, lon, part_index, start_sign = _varga_components(longitude, definition)
    return dest_sign, lon, {
        "saptamsa": part_index,
        "start_sign": ZODIAC_SIGNS[start_sign],
        "start_sign_index": start_sign,
        "segment_arc_degrees": definition.span,
        "rule": definition.rule_description,
    }


@dataclass(frozen=True)
class VargaDefinition:
    code: str
    name: str
    divisions: int
    part_key: str
    start_fn: Callable[[int], int]
    dest_fn: Callable[[int, int], int]
    rule_description: str

    @property
    def span(self) -> float:
        return 30.0 / self.divisions



_ODD_EVEN_7TH = _odd_even_start(6)
_ODD_EVEN_9TH = _odd_even_start(8)
_ODD_EVEN_6TH = _odd_even_start(5)
_ODD_EVEN_5TH = _odd_even_start(4)

VARGA_DEFINITIONS: dict[str, VargaDefinition] = {
    "D3": VargaDefinition(
        code="D3",
        name="Drekkana",
        divisions=3,
        part_key="drekkana",
        start_fn=lambda sign_idx: sign_idx,
        dest_fn=_drekkana_dest,
        rule_description="Triplicity counting: each 10° segment maps to the elemental trine.",
    ),
    "D7": VargaDefinition(
        code="D7",
        name="Saptāṁśa",
        divisions=7,
        part_key="saptamsa",
        start_fn=_ODD_EVEN_7TH,
        dest_fn=_sequential_dest(_ODD_EVEN_7TH),
        rule_description="Odd signs count from the natal sign; even signs count from the 7th sign.",
    ),
    "D9": VargaDefinition(
        code="D9",
        name="Navāṁśa",
        divisions=9,
        part_key="pada",
        start_fn=_modal_start,
        dest_fn=_sequential_dest(_modal_start),
        rule_description="Movable signs count from the natal sign, fixed from the 9th, dual from the 5th.",
    ),
    "D10": VargaDefinition(
        code="D10",
        name="Daśāṁśa",
        divisions=10,
        part_key="part",
        start_fn=_modal_start,
        dest_fn=_sequential_dest(_modal_start),
        rule_description="Movable signs count from the natal sign, fixed from the 9th, dual from the 5th.",
    ),
    "D12": VargaDefinition(
        code="D12",
        name="Dvādāṁśa",
        divisions=12,
        part_key="dwadasamsa",
        start_fn=_ODD_EVEN_7TH,
        dest_fn=_sequential_dest(_ODD_EVEN_7TH),
        rule_description="Odd signs count from the natal sign; even signs count from the 7th sign.",
    ),
    "D16": VargaDefinition(
        code="D16",
        name="Ṣoḍaśāṁśa",
        divisions=16,
        part_key="shodasamsa",
        start_fn=_ODD_EVEN_9TH,
        dest_fn=_sequential_dest(_ODD_EVEN_9TH),
        rule_description="Odd signs count from the natal sign; even signs count from the 9th sign.",
    ),
    "D24": VargaDefinition(
        code="D24",
        name="Siddhāṁśa",
        divisions=24,
        part_key="siddhamsa",
        start_fn=_ODD_EVEN_9TH,
        dest_fn=_sequential_dest(_ODD_EVEN_9TH),
        rule_description="Odd signs count from the natal sign; even signs count from the 9th sign.",
    ),
    "D45": VargaDefinition(
        code="D45",
        name="Akṣavedāṁśa",
        divisions=45,
        part_key="akshavedamsa",
        start_fn=_ODD_EVEN_5TH,
        dest_fn=_sequential_dest(_ODD_EVEN_5TH),
        rule_description="Odd signs count from the natal sign; even signs count from the 5th sign.",
    ),
    "D60": VargaDefinition(
        code="D60",
        name="Ṣaṣṭiāṁśa",
        divisions=60,
        part_key="shashtiamsa",
        start_fn=_ODD_EVEN_6TH,
        dest_fn=_sequential_dest(_ODD_EVEN_6TH),
        rule_description="Odd signs count from the natal sign; even signs count from the 6th sign.",
    ),
}


def _part_index(degrees_in_sign: float, divisions: int) -> int:
    span = 30.0 / divisions
    # ``floor`` is more stable than ``//`` for floats that are very close to
    # a boundary (e.g. 10° with a 3°20' span).
    raw = floor((degrees_in_sign / span) + 1e-9)
    if raw >= divisions:
        return divisions - 1
    return int(raw)


def _varga_components(longitude: float, definition: VargaDefinition) -> tuple[int, float, int, int]:
    sign_idx = sign_index(longitude)
    deg = _deg_in_sign(longitude)
    part_index = _part_index(deg, definition.divisions)
    start_sign = definition.start_fn(sign_idx)
    dest_sign = definition.dest_fn(sign_idx, part_index)
    deg_in_part = deg - (part_index * definition.span)
    varga_longitude = (dest_sign * 30.0) + (deg_in_part * definition.divisions)
    return dest_sign, varga_longitude % 360.0, part_index + 1, start_sign


def rasi_sign(longitude: float) -> tuple[int, float, dict[str, int | str]]:
    """Return the base Rāśi sign index and longitude for ``longitude``."""

    sign_idx = sign_index(longitude)
    return sign_idx, longitude % 360.0, {}


def navamsa_sign(longitude: float) -> tuple[int, float, int]:
    """Return the Navāṁśa sign index, longitude, and pada for ``longitude``."""

    dest_sign, lon, pada, _ = _varga_components(longitude, VARGA_DEFINITIONS["D9"])
    return dest_sign, lon, pada


def saptamsa_sign(longitude: float) -> tuple[int, float, int]:
    """Return the Saptāṁśa sign index, longitude, and part for ``longitude``."""

    dest_sign, lon, part, _ = _varga_components(longitude, VARGA_DEFINITIONS["D7"])
    return dest_sign, lon, part


def dasamsa_sign(longitude: float) -> tuple[int, float, int]:
    """Return the Daśāṁśa sign index, longitude, and decan for ``longitude``."""

    dest_sign, lon, part, _ = _varga_components(longitude, VARGA_DEFINITIONS["D10"])
    return dest_sign, lon, part


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

    kind: Literal["D3", "D7", "D9", "D10", "D12", "D16", "D24", "D45", "D60"],

    *,
    ascendant: float | None = None,
) -> dict[str, dict[str, float | int | str]]:
    """Compute varga placements for ``natal_positions``.

    The ``kind`` parameter accepts the standard ``D`` notation (e.g. ``"D9"``
    for Navāṁśa).  Each supported chart uses the Parasari counting rule noted
    in :data:`VARGA_DEFINITIONS` to determine which sign a subdivision maps to.
    """


    definition = VARGA_DEFINITIONS.get(kind.upper())
    if definition is None:  # pragma: no cover - guarded by caller
        raise ValueError("Unsupported varga kind")

    results: dict[str, dict[str, float | int | str]] = {}
    for name, position in natal_positions.items():
        longitude = getattr(position, "longitude", None)
        if longitude is None:
            continue

        sign_idx, lon, part_index, start_sign = _varga_components(longitude, definition)
        results[name] = {
            "longitude": lon,
            "sign": ZODIAC_SIGNS[sign_idx],
            "sign_index": sign_idx,
            definition.part_key: part_index,
            "start_sign": ZODIAC_SIGNS[start_sign],
            "start_sign_index": start_sign,
            "segment_arc_degrees": definition.span,
            "rule": definition.rule_description,
        }

    if ascendant is not None:
        sign_idx, lon, part_index, start_sign = _varga_components(ascendant, definition)
        results["Ascendant"] = {
            "longitude": lon,
            "sign": ZODIAC_SIGNS[sign_idx],
            "sign_index": sign_idx,
            definition.part_key: part_index,
            "start_sign": ZODIAC_SIGNS[start_sign],
            "start_sign_index": start_sign,
            "segment_arc_degrees": definition.span,
            "rule": definition.rule_description,
        }


    return results
