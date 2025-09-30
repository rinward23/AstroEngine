"""Swiss ephemeris body-code helpers shared across the returns engine."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from ...core.bodies import canonical_name

try:  # pragma: no cover - optional dependency guard
    import swisseph as swe  # type: ignore
except Exception:  # pragma: no cover - fallback for test environments
    swe = None  # type: ignore


@dataclass(frozen=True)
class BodyCode:
    """Resolved Swiss ephemeris code and derived flag."""

    code: int
    derived: bool = False


_BASE_CODES: dict[str, BodyCode] = {
    "sun": BodyCode(int(getattr(swe, "SUN", 0)) if swe else 0),
    "moon": BodyCode(int(getattr(swe, "MOON", 1)) if swe else 1),
    "mercury": BodyCode(int(getattr(swe, "MERCURY", 2)) if swe else 2),
    "venus": BodyCode(int(getattr(swe, "VENUS", 3)) if swe else 3),
    "mars": BodyCode(int(getattr(swe, "MARS", 4)) if swe else 4),
    "jupiter": BodyCode(int(getattr(swe, "JUPITER", 5)) if swe else 5),
    "saturn": BodyCode(int(getattr(swe, "SATURN", 6)) if swe else 6),
    "uranus": BodyCode(int(getattr(swe, "URANUS", 7)) if swe else 7),
    "neptune": BodyCode(int(getattr(swe, "NEPTUNE", 8)) if swe else 8),
    "pluto": BodyCode(int(getattr(swe, "PLUTO", 9)) if swe else 9),
}

if swe is not None:  # pragma: no cover - depends on pyswisseph build
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
        code = getattr(swe, attr, None)
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
