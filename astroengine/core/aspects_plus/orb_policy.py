from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PreparedOrbPolicy:
    """Normalized, ready-to-use view of an orb policy."""

    per_object: dict[str, float]
    per_aspect: dict[str, float]
    adaptive_rules: dict[str, Any]


def prepare_policy(policy: Mapping[str, Any] | None) -> PreparedOrbPolicy:
    """Return a :class:`PreparedOrbPolicy` with consistent mapping defaults."""

    if isinstance(policy, PreparedOrbPolicy):
        return policy

    source: Mapping[str, Any] = policy or {}
    per_object = dict((source.get("per_object") or {}).items())
    per_aspect = dict((source.get("per_aspect") or {}).items())
    adaptive_rules = dict((source.get("adaptive_rules") or {}).items())
    return PreparedOrbPolicy(
        per_object=per_object,
        per_aspect=per_aspect,
        adaptive_rules=adaptive_rules,
    )

# Built-in aspect defaults (deg). Adjust later via policy.per_aspect.
ASPECT_DEFAULTS: dict[str, float] = {
    "conjunction": 8.0,
    "opposition": 7.0,
    "square": 6.0,
    "trine": 6.0,
    "sextile": 4.0,
    "quincunx": 3.0,
    "semisextile": 2.0,
    "semisquare": 2.0,
    "sesquisquare": 2.0,
    "quintile": 2.0,
    "biquintile": 2.0,
    "semiquintile": 2.0,
    "novile": 1.0,
    "binovile": 1.0,
    "septile": 1.0,
    "biseptile": 1.0,
    "triseptile": 1.0,
    "tredecile": 1.5,
    "undecile": 1.0,
}

LUMINARIES = {"Sun", "Moon"}
OUTERS = {"Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}
MINOR_ASPECTS = {
    "quincunx",
    "semisextile",
    "semisquare",
    "sesquisquare",
    "quintile",
    "biquintile",
    "semiquintile",
}
HARMONIC_ASPECTS = {
    "novile",
    "binovile",
    "septile",
    "biseptile",
    "triseptile",
    "tredecile",
    "undecile",
}


def _base_orb(aspect_name: str, per_aspect: dict[str, float]) -> float:
    aspect_key = aspect_name.lower()
    return per_aspect.get(aspect_key, ASPECT_DEFAULTS.get(aspect_key, 3.0))


def _object_orb(object_a: str, object_b: str, base: float, per_object: dict[str, float]) -> float:
    # Use the max of overrides as a starting point (most permissive among the pair)
    oa = per_object.get(object_a, base)
    ob = per_object.get(object_b, base)
    return max(base, oa, ob)


def _adaptive_multiplier(object_a: str, object_b: str, aspect_name: str, rules: dict[str, Any]) -> float:
    # Default multipliers = 1.0 (no change)
    lum_factor = float(rules.get("luminaries_factor", 1.0))
    out_factor = float(rules.get("outers_factor", 1.0))
    minor_factor = float(rules.get("minor_aspect_factor", 1.0))
    harmonic_factor = float(rules.get("harmonic_aspect_factor", minor_factor))

    m = 1.0
    if object_a in LUMINARIES or object_b in LUMINARIES:
        m *= lum_factor
    if object_a in OUTERS or object_b in OUTERS:
        m *= out_factor
    aspect_key = aspect_name.lower()
    if aspect_key in MINOR_ASPECTS:
        m *= minor_factor
    elif aspect_key in HARMONIC_ASPECTS:
        m *= harmonic_factor
    return m


def orb_limit(object_a: str, object_b: str, aspect_name: str, policy: dict[str, Any]) -> float:
    """
    Compute allowed orb in degrees for a given pair and aspect using a policy dict.

    policy dict shape (JSON-safe):
      {
        "per_object": {"Sun": 8.0, "Moon": 6.0, ...},
        "per_aspect": {"conjunction": 8.0, "sextile": 3.0, ...},
        "adaptive_rules": {"luminaries_factor": 0.8, "outers_factor": 1.2, "minor_aspect_factor": 0.9}
      }
    """
    per_object = policy.get("per_object", {}) or {}
    per_aspect = policy.get("per_aspect", {}) or {}
    rules = policy.get("adaptive_rules", {}) or {}

    base = _base_orb(aspect_name, per_aspect)
    start = _object_orb(object_a, object_b, base, per_object)
    mult = _adaptive_multiplier(object_a, object_b, aspect_name, rules)

    # Ensure positive and reasonable
    final = max(0.1, start * mult)
    return float(final)


def orb_limit_prepared(
    object_a: str,
    object_b: str,
    aspect_name: str,
    policy: PreparedOrbPolicy,
) -> float:
    """Specialized orb computation for pre-normalized policies."""

    base = _base_orb(aspect_name, policy.per_aspect)
    start = _object_orb(object_a, object_b, base, policy.per_object)
    mult = _adaptive_multiplier(object_a, object_b, aspect_name, policy.adaptive_rules)
    final = max(0.1, start * mult)
    return float(final)
