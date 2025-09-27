"""Aspect detection utilities for coarse scans."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .core.angles import DeltaLambdaTracker, classify_relative_motion, signed_delta
from .core.bodies import body_class
from .infrastructure.paths import profiles_dir
from .refine import adaptive_corridor_width
from .utils.io import load_json_document
from .vca.houses import (
    HouseSystem,
    DomainW,
    blend as blend_domains,
    load_house_profile,
    weights_for_body,
)

__all__ = ["AspectHit", "detect_aspects"]


@dataclass(frozen=True)
class AspectHit:
    """Represents a single longitudinal aspect detection."""

    kind: str
    when_iso: str
    moving: str
    target: str
    angle_deg: float
    lon_moving: float
    lon_target: float
    delta_lambda_deg: float
    offset_deg: float
    orb_abs: float
    orb_allow: float
    is_partile: bool
    applying_or_separating: str
    family: str
    corridor_width_deg: float | None = None
    corridor_profile: str | None = None
    speed_deg_per_day: float | None = None
    retrograde: bool | None = None
    domain_weights: DomainW | None = None


_DEF_PATH = profiles_dir() / "aspects_policy.json"

_DEFAULT_PARTILE_THRESHOLD_DEG = 10.0 / 60.0

_MAJOR_NAMES = {"conjunction", "sextile", "square", "trine", "opposition"}

_MINOR_NAMES = {
    "semisextile",
    "semisquare",
    "sesquisquare",
    "quincunx",
    "quintile",
    "biquintile",
    "semiquintile",
}

_HARMONIC_NAMES = {
    "septile",
    "biseptile",
    "triseptile",
    "novile",
    "binovile",
    "undecile",
    "tredecile",
}

_OPTIONAL_ANGLE_OVERRIDES: dict[str, float] = {
    "semisextile": 30.0,
    "semisquare": 45.0,
    "sesquisquare": 135.0,
    "quincunx": 150.0,
    "quintile": 72.0,
    "biquintile": 144.0,
    "semiquintile": 36.0,
    "tredecile": 108.0,
    "septile": 51.4286,
    "biseptile": 102.8571,
    "triseptile": 154.2857,
    "novile": 40.0,
    "binovile": 80.0,
    "undecile": 32.7273,
}

_HARMONIC_FAMILY_TO_NAMES: dict[int, tuple[str, ...]] = {
    5: ("quintile", "biquintile"),
    6: ("sextile", "trine", "opposition"),
    7: ("septile", "biseptile", "triseptile"),
    8: ("semisquare", "sesquisquare"),
    9: ("novile", "binovile"),
    10: ("semiquintile", "quintile", "biquintile", "tredecile"),
    11: ("undecile",),
    12: ("semisextile", "quincunx", "sextile", "square", "trine", "opposition"),
}


def _load_policy(path: str | None = None) -> dict:
    policy_path = Path(path) if path else _DEF_PATH
    return load_json_document(policy_path)


def _normalize_name(name: str) -> str:
    return str(name).strip().lower()


def _family_for(name: str) -> str:
    lowered = _normalize_name(name)
    if lowered in _MAJOR_NAMES:
        return "major"
    if lowered in _MINOR_NAMES:
        return "minor"
    if lowered in _HARMONIC_NAMES:
        return "harmonic"
    return "harmonic"


def _orb_for(
    aspect_name: str, family: str, a_class: str, b_class: str, policy: dict
) -> float:
    orbs = policy.get("orbs_deg", {}).get(aspect_name, {})

    if isinstance(orbs, int | float):
        return float(orbs)

    pair_key = f"{a_class}-{b_class}"
    if pair_key in orbs:
        return float(orbs[pair_key])

    pair_key_rev = f"{b_class}-{a_class}"
    if pair_key_rev in orbs:
        return float(orbs[pair_key_rev])

    if orbs:
        default = float(orbs.get("default", policy.get("default_orb_deg", 2.0)))
        allow_a = float(orbs.get(a_class, default))
        allow_b = float(orbs.get(b_class, default))
        return min(allow_a, allow_b)

    family_defaults = policy.get("orb_defaults", {}).get(family, {})
    if family_defaults:
        default = float(
            family_defaults.get("default", policy.get("default_orb_deg", 2.0))
        )
        allow_a = float(family_defaults.get(a_class, default))
        allow_b = float(family_defaults.get(b_class, default))
        return min(allow_a, allow_b)

    fallback = policy.get("default_orb_deg")
    if fallback is not None:
        return float(fallback)

    return 2.0


def _resolve_enabled(policy: dict) -> dict[str, tuple[float, str]]:
    base_angles = {
        _normalize_name(name): float(angle)
        for name, angle in policy.get("angles_deg", {}).items()
    }

    enabled: set[str] = set()
    for name in policy.get("enabled", []):
        enabled.add(_normalize_name(name))

    for name in policy.get("enabled_minors", []):
        enabled.add(_normalize_name(name))

    for entry in policy.get("enabled_harmonics", []):
        if isinstance(entry, int | float) or (
            isinstance(entry, str) and entry.strip().isdigit()
        ):
            try:
                harmonic = int(entry)
            except (TypeError, ValueError):
                continue
            for name in _HARMONIC_FAMILY_TO_NAMES.get(
                harmonic, ()
            ):  # ensure optional families
                enabled.add(_normalize_name(name))
        else:
            enabled.add(_normalize_name(entry))

    angle_defs: dict[str, tuple[float, str]] = {}
    for name in enabled:
        if name in base_angles:
            angle = base_angles[name]
        elif name in _OPTIONAL_ANGLE_OVERRIDES:
            angle = _OPTIONAL_ANGLE_OVERRIDES[name]
        else:
            continue
        angle_defs[name] = (float(angle), _family_for(name))

    return angle_defs


def detect_aspects(
    provider,
    iso_ticks: Iterable[str],
    moving: str,
    target: str,
    *,
    policy_path: str | None = None,
    natal_chart=None,
    house_system: str | None = None,
) -> list[AspectHit]:
    policy = _load_policy(policy_path)
    angles_map = _resolve_enabled(policy)
    if not angles_map:
        return []

    partile_threshold = float(
        policy.get("partile_threshold_deg", _DEFAULT_PARTILE_THRESHOLD_DEG)
    )
    corridor_cfg = policy.get("corridor", {})
    corridor_profile = str(corridor_cfg.get("profile", "gaussian"))
    corridor_minimum = float(corridor_cfg.get("minimum_deg", 0.1))
    default_orb = float(policy.get("default_orb_deg", 2.0))
    delta_tracker = DeltaLambdaTracker()
    out: list[AspectHit] = []
    cls_m = body_class(moving)
    cls_t = body_class(target)

    domain_profile: dict[int, DomainW] | None = None
    domain_meta: dict[str, dict] = {}
    domain_target: DomainW | None = None
    domain_system = house_system
    domain_location = None
    domain_alphas: Sequence[float] | None = None

    if natal_chart is not None:
        domain_profile, domain_meta = load_house_profile()
        houses = getattr(natal_chart, "houses", None)
        if domain_system is None and houses is not None:
            domain_system = getattr(houses, "system", None)
        if domain_system is None:
            domain_system = HouseSystem.PLACIDUS
        domain_system = str(domain_system).lower()
        try:
            domain_target = weights_for_body(
                natal_chart, target, domain_system, profile=domain_profile
            )
        except Exception:
            domain_target = None
        domain_location = getattr(natal_chart, "location", None)
        blend_spec = domain_meta.get("blend", {})
        alphas = blend_spec.get("natal_vs_transit")
        if isinstance(alphas, Sequence) and alphas:
            try:
                domain_alphas = tuple(float(value) for value in alphas)
            except (TypeError, ValueError):
                domain_alphas = None

    for iso in iso_ticks:
        positions = provider.positions_ecliptic(iso, [moving, target])
        lon_moving = float(positions[moving]["lon"])
        lon_target = float(positions[target]["lon"])
        speed_moving = float(positions[moving].get("speed_lon", 0.0))
        speed_target = float(positions[target].get("speed_lon", 0.0))
        retrograde = speed_moving < 0 or speed_target < 0

        delta_lambda = delta_tracker.update(lon_target, lon_moving)
        for aspect_name, (angle, family) in angles_map.items():
            orb_allow = _orb_for(aspect_name, family, cls_m, cls_t, policy)
            offset = signed_delta(delta_lambda - angle)
            if abs(offset) <= orb_allow:
                separation_for_motion = angle + offset
                motion = classify_relative_motion(
                    separation_for_motion,
                    angle,
                    speed_moving,
                    speed_target,
                )
                is_partile = abs(offset) <= partile_threshold
                aspect_strength = max(orb_allow / max(default_orb, 1e-9), 0.25)
                corridor_width = adaptive_corridor_width(
                    orb_allow,
                    speed_moving,
                    speed_target,
                    aspect_strength=aspect_strength,
                    retrograde=retrograde,
                    minimum_orb_deg=corridor_minimum,
                )
                domain_weights = None
                if domain_profile is not None and domain_target is not None:
                    weights_to_blend: list[DomainW] = [domain_target]
                    moving_pos = positions.get(moving)
                    if domain_location is not None and moving_pos is not None:
                        lat = getattr(domain_location, "latitude", None)
                        lon = getattr(domain_location, "longitude", None)
                        if lat is not None and lon is not None:
                            transit_chart = {
                                "ts": iso,
                                "lat": float(lat),
                                "lon": float(lon),
                                "positions": {moving: moving_pos},
                            }
                            try:
                                transit_weights = weights_for_body(
                                    transit_chart,
                                    moving,
                                    domain_system or HouseSystem.PLACIDUS,
                                    profile=domain_profile,
                                )
                            except Exception:
                                transit_weights = None
                            if transit_weights is not None:
                                weights_to_blend.append(transit_weights)
                    if len(weights_to_blend) == 1:
                        domain_weights = weights_to_blend[0]
                    else:
                        domain_weights = blend_domains(
                            weights_to_blend,
                            alphas=domain_alphas,
                        )

                out.append(
                    AspectHit(
                        kind=f"aspect_{aspect_name}",
                        when_iso=iso,
                        moving=moving,
                        target=target,
                        angle_deg=float(angle),
                        lon_moving=float(lon_moving),
                        lon_target=float(lon_target),
                        delta_lambda_deg=float(delta_lambda),
                        offset_deg=float(offset),
                        orb_abs=float(abs(offset)),
                        orb_allow=float(orb_allow),
                        is_partile=bool(is_partile),
                        applying_or_separating=motion.state,
                        family=family,
                        corridor_width_deg=float(corridor_width),
                        corridor_profile=corridor_profile,
                        speed_deg_per_day=float(motion.relative_speed_deg_per_day),
                        retrograde=retrograde,
                        domain_weights=domain_weights,
                    )
                )
    return out
