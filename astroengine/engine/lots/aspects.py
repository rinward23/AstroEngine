"""Aspect utilities between planetary bodies and calculated Lots."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Mapping

from ...scoring.policy import OrbPolicy

__all__ = ["AspectHit", "aspects_to_lots"]


@dataclass(frozen=True)
class AspectHit:
    body: str
    lot: str
    angle: float
    orb: float
    separation: float
    severity: float
    applying: bool | None


def _get_longitude(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value) % 360.0
    longitude = getattr(value, "longitude", None)
    if longitude is None:
        raise TypeError(f"Cannot resolve longitude from {value!r}")
    return float(longitude) % 360.0


def _get_speed(value: object) -> float | None:
    speed = getattr(value, "speed_longitude", None)
    if speed is None:
        return None
    try:
        return float(speed)
    except (TypeError, ValueError):
        return None


def _angular_separation(body: float, lot: float) -> float:
    diff = (body - lot + 180.0) % 360.0 - 180.0
    return diff


def _resolve_orb(policy: OrbPolicy, body: str, angle: float) -> float:
    data = policy.to_mapping()
    per_body = data.get("per_body")
    if isinstance(per_body, Mapping):
        entry = per_body.get(body)
        if isinstance(entry, Mapping):
            angle_key = str(int(round(angle)))
            if angle_key in entry:
                try:
                    return float(entry[angle_key])
                except (TypeError, ValueError):
                    pass
            default = entry.get("default")
            if default is not None:
                try:
                    return float(default)
                except (TypeError, ValueError):
                    pass
        elif entry is not None:
            try:
                return float(entry)
            except (TypeError, ValueError):
                pass
    defaults = data.get("defaults")
    if isinstance(defaults, Mapping):
        angle_key = str(int(round(angle)))
        if angle_key in defaults:
            try:
                return float(defaults[angle_key])
            except (TypeError, ValueError):
                pass
        default = defaults.get("default")
        if default is not None:
            try:
                return float(default)
            except (TypeError, ValueError):
                pass
    return 3.0


def _angles_from_harmonics(harmonics: Iterable[int]) -> list[float]:
    angles: set[float] = set()
    for harmonic in harmonics:
        if harmonic <= 0:
            continue
        base = 360.0 / float(harmonic)
        limit = harmonic // 2
        for k in range(0, limit + 1):
            angle = round(base * k, 6)
            if angle <= 180.0:
                angles.add(angle)
    return sorted(angles)


def _severity(orb: float, allowance: float) -> float:
    if allowance <= 0.0:
        return 0.0
    tightness = max(0.0, 1.0 - orb / allowance)
    return round(tightness, 6)


def aspects_to_lots(
    lots: Mapping[str, float],
    bodies_positions: Mapping[str, object],
    policy: OrbPolicy,
    harmonics: Iterable[int],
) -> list[AspectHit]:
    """Return aspect hits for ``bodies_positions`` relative to ``lots``."""

    angles = _angles_from_harmonics(harmonics)
    hits: list[AspectHit] = []
    for body_name, value in bodies_positions.items():
        body_long = _get_longitude(value)
        body_speed = _get_speed(value)
        for lot_name, lot_long in lots.items():
            delta = _angular_separation(body_long, lot_long)
            separation = abs(delta)
            for angle in angles:
                orb = abs(separation - angle)
                allowance = _resolve_orb(policy, body_name, angle)
                if orb <= allowance:
                    applying: bool | None = None
                    if body_speed is not None:
                        target = angle if abs(delta - angle) <= abs(delta + angle) else -angle
                        diff = delta - target
                        if diff > 0:
                            applying = body_speed < 0
                        elif diff < 0:
                            applying = body_speed > 0
                        else:
                            applying = None
                    severity = _severity(orb, allowance)
                    hits.append(
                        AspectHit(
                            body=body_name,
                            lot=lot_name,
                            angle=angle,
                            orb=orb,
                            separation=separation,
                            severity=severity,
                            applying=applying,
                        )
                    )
                    break
    return sorted(hits, key=lambda hit: (hit.lot, hit.body, hit.angle, hit.orb))
