"""Aspect detection utilities for coarse scans."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from .core.bodies import body_class
from .infrastructure.paths import profiles_dir
from .utils.angles import classify_applying_separating, delta_angle, is_within_orb

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
    orb_abs: float
    orb_allow: float
    applying_or_separating: str


_DEF_PATH = profiles_dir() / "aspects_policy.json"


def _load_policy(path: str | None = None) -> dict:
    policy_path = Path(path) if path else _DEF_PATH
    raw_lines = policy_path.read_text(encoding="utf-8").splitlines()
    payload = "\n".join(line for line in raw_lines if not line.strip().startswith("#"))
    return json.loads(payload)


def _orb_for(aspect_name: str, a_class: str, b_class: str, policy: dict) -> float:
    orbs = policy.get("orbs_deg", {}).get(aspect_name, {})
    allow_a = float(orbs.get(a_class, orbs.get("default", 2.0)))
    allow_b = float(orbs.get(b_class, orbs.get("default", 2.0)))
    return min(allow_a, allow_b)


def detect_aspects(
    provider,
    iso_ticks: Iterable[str],
    moving: str,
    target: str,
    *,
    policy_path: str | None = None,
) -> List[AspectHit]:
    policy = _load_policy(policy_path)
    enabled = set(policy.get("enabled", [])) | set(policy.get("enabled_minors", []))
    angles_map: Dict[str, float] = {
        key: float(value) for key, value in policy.get("angles_deg", {}).items() if key in enabled
    }

    out: List[AspectHit] = []
    cls_m = body_class(moving)
    cls_t = body_class(target)

    for iso in iso_ticks:
        positions = provider.positions_ecliptic(iso, [moving, target])
        lon_moving = float(positions[moving]["lon"])
        lon_target = float(positions[target]["lon"])
        speed = float(positions[moving].get("speed_lon", 0.0))
        delta_mt = (lon_target - lon_moving) % 360.0

        for aspect_name, angle in angles_map.items():
            orb_allow = _orb_for(aspect_name, cls_m, cls_t, policy)
            separation = delta_angle(delta_mt, angle)
            if abs(separation) <= orb_allow:
                ref_point = (lon_target - angle) % 360.0
                motion = classify_applying_separating(lon_moving, speed, ref_point)
                out.append(
                    AspectHit(
                        kind=f"aspect_{aspect_name}",
                        when_iso=iso,
                        moving=moving,
                        target=target,
                        angle_deg=float(angle),
                        lon_moving=float(lon_moving),
                        lon_target=float(lon_target),
                        orb_abs=float(abs(separation)),
                        orb_allow=float(orb_allow),
                        applying_or_separating=motion,
                    )
                )
    return out
