from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "HousePolicy",
    "HouseResult",
    "compute_houses",
    "list_house_systems",
]


# --------------------------- Angle utils -----------------------------------

def _norm360(x: float) -> float:
    """Normalize an angle to the range [0, 360)."""
    v = x % 360.0
    return v + 360.0 if v < 0 else v


def _sign_index(lon_deg: float) -> int:
    """Return the zero-indexed zodiac sign for the given longitude."""
    return int(_norm360(lon_deg) // 30)


def _forward_arc(a: float, b: float) -> float:
    """Arc from a→b going forward (CCW) in degrees, in (0, 360]."""
    a = _norm360(a)
    b = _norm360(b)
    d = (b - a) % 360.0
    return d if d != 0 else 360.0


def _forward_points(a: float, b: float, n: int) -> list[float]:
    """Return the n-1 interior division points from a→b forward (equal spacing)."""
    arc = _forward_arc(a, b)
    step = arc / float(n)
    return [_norm360(a + step * k) for k in range(1, n)]


# --------------------------- Policy ----------------------------------------


@dataclass
class HousePolicy:
    """Configuration controlling house system fallbacks."""

    extreme_lat_deg: float = 66.0  # Arctic/Antarctic circle ~66.56
    placidus_fallback: str = "porphyry"  # which system to fallback to
    always_fallback_placidus: bool = True  # until full Placidus lands


@dataclass
class HouseResult:
    """Bundle of cusp longitudes and metadata about the computation."""

    cusps: list[float]  # 12 longitudes, cusp 1..12
    meta: dict[str, object]


# --------------------------- Systems ---------------------------------------


def list_house_systems() -> list[str]:
    """Return the house system identifiers supported by this engine."""

    return ["whole_sign", "equal", "porphyry", "placidus"]


def _whole_sign(asc_lon: float) -> list[float]:
    """Compute whole sign house cusps from the Ascendant longitude."""

    # Cusp 1 at 0° of Asc sign; then every 30°
    sign0 = _sign_index(asc_lon)
    cusp1 = sign0 * 30.0
    return [_norm360(cusp1 + 30.0 * i) for i in range(12)]


def _equal(asc_lon: float) -> list[float]:
    """Compute equal houses by stepping 30° from the Ascendant."""

    return [_norm360(asc_lon + 30.0 * i) for i in range(12)]


def _porphyry(asc_lon: float, mc_lon: float) -> list[float]:
    """Compute Porphyry houses by trisecting the quadrants between angles."""

    # Angles
    H1 = _norm360(asc_lon)
    H10 = _norm360(mc_lon)
    H7 = _norm360(H1 + 180.0)
    H4 = _norm360(H10 + 180.0)

    # Quadrant divisions: start→end (Asc→IC), (IC→Desc), (Desc→MC), (MC→Asc)
    q1 = [H1, *_forward_points(H1, H4, 3), H4]
    q2 = [H4, *_forward_points(H4, H7, 3), H7]
    q3 = [H7, *_forward_points(H7, H10, 3), H10]
    q4 = [H10, *_forward_points(H10, H1, 3), H1]

    # Assemble cusps in order 1..12 (avoid duplicating the starting cusp at the end)
    C1, C2, C3, C4 = q1[0], q1[1], q1[2], q1[3]
    C5, C6, C7 = q2[1], q2[2], q2[3]
    C8, C9, C10 = q3[1], q3[2], q3[3]
    C11, C12 = q4[1], q4[2]
    return [C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12]


def _placidus_with_fallback(
    asc_lon: float, mc_lon: float, lat_deg: float, policy: HousePolicy
) -> tuple[list[float], dict[str, object]]:
    """Placeholder Placidus implementation honoring fallback policy."""

    meta: dict[str, object] = {"system": "placidus"}
    # MVP: Always fallback (or if extreme latitude), to avoid invalid cusps in polar regions
    if policy.always_fallback_placidus or abs(lat_deg) >= policy.extreme_lat_deg:
        sys = policy.placidus_fallback
        meta["fallback"] = f"placidus→{sys}"
        if sys == "porphyry":
            return _porphyry(asc_lon, mc_lon), meta
        if sys == "equal":
            return _equal(asc_lon), meta
        # default to equal if unknown fallback
        return _equal(asc_lon), meta
    # Placeholder for future true Placidus implementation
    return _porphyry(asc_lon, mc_lon), meta


# --------------------------- Public API ------------------------------------


def compute_houses(
    system: str,
    asc_lon: float,
    mc_lon: float,
    lat_deg: float,
    policy: HousePolicy | None = None,
) -> HouseResult:
    """Compute house cusps for the requested system."""

    system = (system or "").lower()
    pol = policy or HousePolicy()
    if system == "whole_sign":
        cusps = _whole_sign(asc_lon)
        meta: dict[str, object] = {"system": system}
    elif system == "equal":
        cusps = _equal(asc_lon)
        meta = {"system": system}
    elif system == "porphyry":
        cusps = _porphyry(asc_lon, mc_lon)
        meta = {"system": system}
    elif system == "placidus":
        cusps, meta = _placidus_with_fallback(asc_lon, mc_lon, lat_deg, pol)
    else:
        raise ValueError(f"Unsupported house system: {system}")
    return HouseResult(cusps=cusps, meta=meta)
