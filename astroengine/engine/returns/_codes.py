"""Swiss ephemeris body-code helpers shared across the returns engine."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from ...core.bodies import canonical_name

from astroengine.ephemeris.swe import has_swe, swe


@dataclass(frozen=True)
class BodyCode:
    """Resolved Swiss ephemeris code and derived flag."""

    code: int
    derived: bool = False


_HAS_SWE = has_swe()
_SWE_MODULE = swe() if _HAS_SWE else None

_BASE_CODES: dict[str, BodyCode] = {
    "sun": BodyCode(int(getattr(_SWE_MODULE, "SUN", 0)) if _SWE_MODULE else 0),
    "moon": BodyCode(int(getattr(_SWE_MODULE, "MOON", 1)) if _SWE_MODULE else 1),
    "mercury": BodyCode(int(getattr(_SWE_MODULE, "MERCURY", 2)) if _SWE_MODULE else 2),
    "venus": BodyCode(int(getattr(_SWE_MODULE, "VENUS", 3)) if _SWE_MODULE else 3),
    "mars": BodyCode(int(getattr(_SWE_MODULE, "MARS", 4)) if _SWE_MODULE else 4),
    "jupiter": BodyCode(int(getattr(_SWE_MODULE, "JUPITER", 5)) if _SWE_MODULE else 5),
    "saturn": BodyCode(int(getattr(_SWE_MODULE, "SATURN", 6)) if _SWE_MODULE else 6),
    "uranus": BodyCode(int(getattr(_SWE_MODULE, "URANUS", 7)) if _SWE_MODULE else 7),
    "neptune": BodyCode(int(getattr(_SWE_MODULE, "NEPTUNE", 8)) if _SWE_MODULE else 8),
    "pluto": BodyCode(int(getattr(_SWE_MODULE, "PLUTO", 9)) if _SWE_MODULE else 9),
}

if _SWE_MODULE is not None:  # pragma: no cover - depends on pyswisseph build
    for attr, name in (
        ("CERES", "ceres"),
        ("PALLAS", "pallas"),
        ("JUNO", "juno"),
        ("VESTA", "vesta"),
        ("CHIRON", "chiron"),
        ("PHOLUS", "pholus"),
        ("NESSUS", "nessus"),
        ("ERIS", "eris"),
        ("HAUMEA", "haumea"),
        ("MAKEMAKE", "makemake"),
        ("SEDNA", "sedna"),
        ("QUAOAR", "quaoar"),
        ("ORCUS", "orcus"),
        ("IXION", "ixion"),
    ):
        code = getattr(_SWE_MODULE, attr, None)
        if code is not None:
            _BASE_CODES[name] = BodyCode(int(code))


@lru_cache(maxsize=None)
def resolve_body_code(name: str) -> BodyCode:
    """Return the Swiss body code for ``name`` suitable for :class:`EphemerisAdapter`.

    The helper normalises body names via :func:`canonical_name` and raises
    :class:`ValueError` when the target is unavailable from the active Swiss
    build.  The returns engine leans on this helper to guarantee consistent
    mappings regardless of downstream aliases such as ``Sun`` vs ``sun``.
    """

    canonical = canonical_name(name)
    if not canonical:
        raise ValueError("body name must be non-empty")
    try:
        return _BASE_CODES[canonical]
    except KeyError as exc:  # pragma: no cover - exercised in tests
        raise ValueError(f"Unsupported body for return calculations: {name}") from exc


__all__ = ["BodyCode", "resolve_body_code"]
