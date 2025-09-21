# >>> AUTO-GEN BEGIN: AE Scoring v1.0
from __future__ import annotations
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .core.bodies import body_class


# Policy loader
_DEFAULT_POLICY_PATH = Path(__file__).resolve().parent.parent / "profiles" / "scoring_policy.json"


def _load_policy(custom_path: Optional[str] = None) -> dict:
    p = Path(custom_path) if custom_path else _DEFAULT_POLICY_PATH
    if p.exists():
        raw = p.read_text()
        cleaned = "\n".join(
            line for line in raw.splitlines() if not line.strip().startswith("#")
        ).strip()
        data = json.loads(cleaned) if cleaned else {}
    else:
        data = {
            "curve": {"kind": "gaussian", "sigma_frac_of_orb": 0.5, "min_score": 0.0, "max_score": 1.0},
            "applying_bias": {"enabled": True, "factor": 1.10},
            "partile": {"enabled": True, "threshold_deg": 0.1667, "boost_factor": 1.25},
            "base_weights": {"decl_parallel": 0.70, "decl_contra": 0.65, "antiscia": 0.55, "contra_antiscia": 0.50},
            "body_class_weights": {"luminary": 1.0, "personal": 0.95, "social": 0.9, "outer": 0.85},
            "pair_matrix": {
                "luminary-personal": 1.0,
                "luminary-social": 0.95,
                "luminary-outer": 0.95,
                "personal-personal": 1.0,
                "personal-social": 0.95,
                "personal-outer": 0.90,
                "social-social": 0.90,
                "social-outer": 0.90,
                "outer-outer": 0.85,
            },
        }
    return data


# Curves
_DEF_MIN, _DEF_MAX = 0.0, 1.0


def _curve_score(kind: str, x: float, *, min_v: float, max_v: float) -> float:
    x = max(0.0, min(1.0, x))
    if kind == "linear":
        y = 1.0 - x
    elif kind == "cosine":
        y = 0.5 * (1.0 + math.cos(math.pi * x))
    elif kind == "logistic":
        y = 1.0 / (1.0 + math.exp(10.0 * (x - 0.5)))  
    else:  # gaussian
        # Map x∈[0,1] to z = x / 0.5 (sigma=0.5) and apply exp(-0.5 z^2)
        z = x / 0.5
        y = math.exp(-0.5 * z * z)
    return min_v + (max_v - min_v) * y


@dataclass
class ScoreInputs:
    kind: str  # 'decl_parallel' | 'decl_contra' | 'antiscia' | 'contra_antiscia' | 'aspect_...'
    orb_abs_deg: float
    orb_allow_deg: float
    moving: str
    target: str
    applying_or_separating: str  # 'applying' | 'separating'


@dataclass
class ScoreResult:
    score: float
    details: dict


def compute_score(inp: ScoreInputs, *, policy_path: Optional[str] = None) -> ScoreResult:
    p = _load_policy(policy_path)

    # 1) Normalized distance within orb
    x = min(1.0, max(0.0, inp.orb_abs_deg / max(inp.orb_allow_deg, 1e-9)))
    curve = p["curve"]
    s = _curve_score(curve.get("kind", "gaussian"), x, min_v=curve.get("min_score", _DEF_MIN), max_v=curve.get("max_score", _DEF_MAX))

    # 2) Base weight by contact kind
    s *= float(p["base_weights"].get(inp.kind, 1.0))

    # 3) Body/Pair weights
    bc_m = body_class(inp.moving)
    bc_t = body_class(inp.target)
    s *= float(p["body_class_weights"].get(bc_m, 1.0))
    s *= float(p["body_class_weights"].get(bc_t, 1.0))
    pair_key = f"{bc_m}-{bc_t}" if bc_m <= bc_t else f"{bc_t}-{bc_m}"
    s *= float(p["pair_matrix"].get(pair_key, 1.0))

    # 4) Applying bias
    if p.get("applying_bias", {}).get("enabled", True) and inp.applying_or_separating == "applying":
        s *= float(p["applying_bias"].get("factor", 1.1))

    # 5) Partile boost
    part = p.get("partile", {})
    if part.get("enabled", True) and inp.orb_abs_deg <= float(part.get("threshold_deg", 0.1667)):
        s *= float(part.get("boost_factor", 1.25))

    # Clamp
    s = max(0.0, min(1.0, s))

    return ScoreResult(score=s, details={
        "x": x, "curve": curve.get("kind", "gaussian"), "base": p["base_weights"].get(inp.kind, 1.0),
        "classes": {"moving": bc_m, "target": bc_t}, "applying": inp.applying_or_separating,
    })
# >>> AUTO-GEN END: AE Scoring v1.0

from importlib import import_module
import sys

from .core.scoring import compute_domain_factor
from .scoring_legacy import DEFAULT_ASPECTS, OrbCalculator, load_dignities, lookup_dignities

__all__ = [
    "ScoreInputs",
    "ScoreResult",
    "compute_score",
    "compute_domain_factor",
    "DEFAULT_ASPECTS",
    "OrbCalculator",
    "load_dignities",
    "lookup_dignities",
]

for _legacy in ("dignity", "orb"):
    module = import_module(f"astroengine.scoring_legacy.{_legacy}")
    sys.modules[f"{__name__}.{_legacy}"] = module


def __getattr__(name: str):  # pragma: no cover - legacy attribute loader
    try:
        return sys.modules[f"{__name__}.{name}"]
    except KeyError as exc:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'") from exc
