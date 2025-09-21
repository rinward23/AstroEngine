# >>> AUTO-GEN BEGIN: AE Valence Module v1.0
from __future__ import annotations
import json
from pathlib import Path
from typing import Literal, Optional, Tuple

Valence = Literal["positive", "neutral", "negative"]

_DEF = Path(__file__).resolve().parent.parent / "profiles" / "valence_policy.json"


def _load(path: Optional[str] = None) -> dict:
    p = Path(path) if path else _DEF
    if p.exists():
        raw = p.read_text()
        clean = "\n".join(line for line in raw.splitlines() if not line.strip().startswith("# >>>"))
        return json.loads(clean)
    return {
        "scale": {"positive": 1, "neutral": 0, "negative": -1},
        "neutral_effects": {"amplify_factor": 1.15, "attenuate_factor": 0.85},
        "bodies": {}, "aspects": {}, "contacts": {}, "overrides": {}
    }


def body_valence(name: str, pol: dict) -> Tuple[Valence, float, str]:
    b = pol.get("bodies", {}).get(name.lower(), {"valence": "neutral", "weight": 1.0, "neutral_mode": "amplify"})
    return b.get("valence", "neutral"), float(b.get("weight", 1.0)), b.get("neutral_mode", "amplify")


def aspect_valence(name: str, pol: dict) -> Tuple[Valence, float, str]:
    a = pol.get("aspects", {}).get(name.lower(), {"valence": "neutral", "weight": 1.0, "neutral_mode": "amplify"})
    return a.get("valence", "neutral"), float(a.get("weight", 1.0)), a.get("neutral_mode", "amplify")


def contact_valence(name: str, pol: dict) -> Tuple[Valence, float, str]:
    c = pol.get("contacts", {}).get(name, {"valence": "neutral", "weight": 1.0, "neutral_mode": "amplify"})
    return c.get("valence", "neutral"), float(c.get("weight", 1.0)), c.get("neutral_mode", "amplify")


def combine_valence(
    *,
    moving: str,
    target: str,
    contact_kind: str,             # e.g., 'aspect_trine' or 'decl_parallel' or 'antiscia'
    aspect_name: str | None,       # e.g., 'trine' when contact_kind startswith 'aspect_'
    policy_path: Optional[str] = None,
) -> Tuple[Valence, float]:
    """Return (valence, factor) for an event, where factor >= 0 scales magnitude.
    - Non-neutral valence yields factor = bodies_weight * aspect/contact weight.
    - Neutral valence yields factor multiplied by amplify/attenuate factor per policy.
    """
    pol = _load(policy_path)
    scale = pol.get("scale", {"positive": 1, "neutral": 0, "negative": -1})
    ne = pol.get("neutral_effects", {"amplify_factor": 1.15, "attenuate_factor": 0.85})

    # Bodies
    vm, wm, nm_m = body_valence(moving, pol)
    vt, wt, nm_t = body_valence(target, pol)

    # Contact/aspect
    if contact_kind.startswith("aspect_"):
        va, wa, nm_a = aspect_valence(aspect_name or contact_kind.split("_", 1)[-1], pol)
    else:
        va, wa, nm_a = contact_valence(contact_kind, pol)

    # Conjunction body overrides
    if contact_kind == "aspect_conjunction":
        ov = pol.get("overrides", {}).get("conjunction_body_bias", {})
        if moving.lower() in ov:
            va = ov[moving.lower()]

    # Combine signs: aspect/contact dominates when non-neutral; otherwise bodies vote
    def sign_of(v: Valence) -> int: return int(scale.get(v, 0))
    s_a = sign_of(va)
    if s_a != 0:
        sign = s_a
    else:
        s_m, s_t = sign_of(vm), sign_of(vt)
        if s_m == s_t:
            sign = s_m
        else:
            sign = 0  # mixed -> neutral

    # Base factor: product of weights
    factor = wm * wt * wa

    # Neutral handling -> amplify/attenuate but do not introduce direction
    if sign == 0:
        mode = nm_a if s_a == 0 else (nm_m if s_m == 0 else nm_t)
        factor *= ne.get("amplify_factor" if mode == "amplify" else "attenuate_factor", 1.0)
        return "neutral", max(0.0, factor)

    return ("positive" if sign > 0 else "negative"), max(0.0, factor)
# >>> AUTO-GEN END: AE Valence Module v1.0
