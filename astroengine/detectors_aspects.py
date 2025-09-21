# >>> AUTO-GEN BEGIN: AE Longitudinal Aspect Detectors v1.0
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from .utils.angles import norm360, delta_angle, classify_applying_separating
from .core.bodies import body_class
import json
from pathlib import Path


@dataclass
class AspectHit:
    kind: str               # e.g., 'aspect_trine'
    when_iso: str
    moving: str
    target: str
    angle_deg: float        # exact aspect angle
    lon_moving: float
    lon_target: float
    orb_abs: float
    applying_or_separating: str


_DEF_PATH = Path(__file__).resolve().parent.parent / "profiles" / "aspects_policy.json"


def _load_policy(path: str | None = None) -> dict:
    p = Path(path) if path else _DEF_PATH
    raw = p.read_text().splitlines()
    payload = "\n".join(line for line in raw if not line.strip().startswith("#"))
    return json.loads(payload)


def _aspect_name_for(angle: float, angles_map: Dict[str, float]) -> str:
    for name, a in angles_map.items():
        if abs(((a - angle + 180) % 360) - 180) < 1e-6:
            return name
    return f"angle_{angle:g}"


def _orb_for(aspect_name: str, a_class: str, b_class: str, policy: dict) -> float:
    orbs = policy["orbs_deg"][aspect_name]
    return min(float(orbs.get(a_class, 2.0)), float(orbs.get(b_class, 2.0)))


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
    angles_map: Dict[str, float] = {k: float(v) for k, v in policy["angles_deg"].items() if k in enabled}

    out: List[AspectHit] = []
    cls_m = body_class(moving)
    cls_t = body_class(target)

    for t in iso_ticks:
        pos = provider.positions_ecliptic(t, [moving, target])
        lm = pos[moving]["lon"]
        lt = pos[target]["lon"]
        spd = pos[moving].get("speed_lon", 0.0)
        dmt = (lt - lm) % 360.0
        for name, ang in angles_map.items():
            target_point = (lt - ang) % 360.0
            delta = delta_angle(dmt, ang)
            orb_allow = _orb_for(name, cls_m, cls_t, policy)
            if abs(delta) <= orb_allow:
                out.append(AspectHit(
                    kind=f"aspect_{name}",
                    when_iso=t,
                    moving=moving,
                    target=target,
                    angle_deg=float(ang),
                    lon_moving=lm,
                    lon_target=lt,
                    orb_abs=abs(delta),
                    applying_or_separating=classify_applying_separating(lm, spd, target_point),
                ))
    return out
# >>> AUTO-GEN END: AE Longitudinal Aspect Detectors v1.0
