"""Aspect attachment helpers for return charts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations

from ...core.angles import signed_delta
from ...core.bodies import body_class, canonical_name
from ...detectors_aspects import AspectHit
from ...scoring.policy import OrbPolicy

__all__ = [
    "AspectDefinition",
    "attach_transiting_aspects",
    "attach_aspects_to_natal",
]


@dataclass(frozen=True)
class AspectDefinition:
    """Static aspect description used by the returns engine."""

    name: str
    angle_deg: float
    harmonic: int
    family: str


# Core library covering the aspects used by the lab. Harmonics align with common
# interpretive practice: harmonic 1 → conjunction, 2 → opposition, 3 → trine, etc.
_ASPECT_LIBRARY: tuple[AspectDefinition, ...] = (
    AspectDefinition("conjunction", 0.0, 1, "major"),
    AspectDefinition("opposition", 180.0, 2, "major"),
    AspectDefinition("trine", 120.0, 3, "major"),
    AspectDefinition("square", 90.0, 4, "major"),
    AspectDefinition("sextile", 60.0, 6, "minor"),
    AspectDefinition("quincunx", 150.0, 6, "minor"),
    AspectDefinition("semisextile", 30.0, 12, "minor"),
    AspectDefinition("semisquare", 45.0, 8, "minor"),
    AspectDefinition("sesquisquare", 135.0, 8, "minor"),
    AspectDefinition("quintile", 72.0, 5, "harmonic"),
    AspectDefinition("biquintile", 144.0, 5, "harmonic"),
)


def _normalize_timestamp(positions: Mapping[str, object]) -> str:
    ts = positions.get("timestamp")
    if isinstance(ts, str):
        return ts
    if isinstance(ts, datetime):
        return ts.astimezone().isoformat()
    raise ValueError("positions payload must include 'timestamp' key")


def _positions_map(positions: Mapping[str, object]) -> Mapping[str, Mapping[str, float]]:
    body_map = positions.get("bodies")
    if not isinstance(body_map, Mapping):
        raise ValueError("positions payload must include 'bodies' mapping")
    normalized: dict[str, Mapping[str, float]] = {}
    for name, payload in body_map.items():
        if not isinstance(payload, Mapping):
            continue
        normalized[name.lower()] = payload
    return normalized


def _orb_allowance(policy: OrbPolicy, a: str, b: str) -> float:
    data = policy.data if isinstance(policy.data, Mapping) else {}
    longitudinal = data.get("longitudinal", {})
    class_a = body_class(a)
    class_b = body_class(b)
    default_orb = float(longitudinal.get("outer", 3.0))
    orb_a = float(longitudinal.get(class_a, default_orb))
    orb_b = float(longitudinal.get(class_b, default_orb))
    return min(orb_a, orb_b)


def _enabled_aspects(harmonics: Sequence[int]) -> Iterable[AspectDefinition]:
    allowed = {int(h) for h in harmonics} if harmonics else set()
    if not allowed:
        return _ASPECT_LIBRARY
    return tuple(aspect for aspect in _ASPECT_LIBRARY if aspect.harmonic in allowed)


def _build_aspect(
    when_iso: str,
    moving: str,
    target: str,
    aspect: AspectDefinition,
    *,
    lon_moving: float,
    lon_target: float,
    speed_moving: float,
    speed_target: float,
    orb_allow: float,
) -> AspectHit:
    separation = signed_delta(lon_moving - lon_target)
    offset = signed_delta(separation - aspect.angle_deg)
    retrograde = speed_moving < 0.0 or speed_target < 0.0
    relative_speed = speed_moving - speed_target
    state = "stationary"
    if abs(relative_speed) > 1e-6:
        state = "applying" if offset * relative_speed < 0 else "separating"
    return AspectHit(
        kind=f"aspect_{aspect.name}",
        when_iso=when_iso,
        moving=moving,
        target=target,
        angle_deg=float(aspect.angle_deg),
        lon_moving=float(lon_moving % 360.0),
        lon_target=float(lon_target % 360.0),
        delta_lambda_deg=float(separation),
        offset_deg=float(offset),
        orb_abs=float(abs(offset)),
        orb_allow=float(orb_allow),
        is_partile=abs(offset) <= 0.1667,
        applying_or_separating=state,
        family=aspect.family,
        corridor_width_deg=float(max(orb_allow, 0.1)),
        corridor_profile="gaussian",
        speed_deg_per_day=float(relative_speed),
        retrograde=retrograde,
        domain_weights=None,
    )


def attach_transiting_aspects(
    positions: Mapping[str, object],
    policy: OrbPolicy,
    harmonics: Sequence[int] | None,
) -> list[AspectHit]:
    """Compute transiting aspect hits for the supplied position snapshot."""

    if not positions:
        return []
    iso = _normalize_timestamp(positions)
    body_map = _positions_map(positions)
    enabled = tuple(_enabled_aspects(harmonics))
    hits: list[AspectHit] = []
    for moving, target in combinations(sorted(body_map), 2):
        pos_m = body_map[moving]
        pos_t = body_map[target]
        lon_m = float(pos_m.get("lon", 0.0))
        lon_t = float(pos_t.get("lon", 0.0))
        speed_m = float(pos_m.get("speed_lon", 0.0))
        speed_t = float(pos_t.get("speed_lon", 0.0))
        orb_allow = _orb_allowance(policy, moving, target)
        for aspect in enabled:
            offset = abs(signed_delta((lon_m - lon_t) - aspect.angle_deg))
            if offset <= orb_allow:
                hits.append(
                    _build_aspect(
                        iso,
                        moving,
                        target,
                        aspect,
                        lon_moving=lon_m,
                        lon_target=lon_t,
                        speed_moving=speed_m,
                        speed_target=speed_t,
                        orb_allow=orb_allow,
                    )
                )
    return hits


def attach_aspects_to_natal(
    transiting: Mapping[str, object],
    natal_positions: Mapping[str, float],
    policy: OrbPolicy,
    harmonics: Sequence[int] | None,
) -> list[AspectHit]:
    """Return aspect hits between transiting bodies and natal positions."""

    iso = _normalize_timestamp(transiting)
    body_map = _positions_map(transiting)
    enabled = tuple(_enabled_aspects(harmonics))
    hits: list[AspectHit] = []
    for moving, payload in body_map.items():
        lon_m = float(payload.get("lon", 0.0))
        speed_m = float(payload.get("speed_lon", 0.0))
        for natal_name, natal_lon in natal_positions.items():
            canonical = canonical_name(natal_name)
            orb_allow = _orb_allowance(policy, moving, canonical)
            for aspect in enabled:
                offset = abs(signed_delta((lon_m - natal_lon) - aspect.angle_deg))
                if offset <= orb_allow:
                    hits.append(
                        _build_aspect(
                            iso,
                            moving,
                            f"natal_{canonical}",
                            aspect,
                            lon_moving=lon_m,
                            lon_target=float(natal_lon),
                            speed_moving=speed_m,
                            speed_target=0.0,
                            orb_allow=orb_allow,
                        )
                    )
    return hits
