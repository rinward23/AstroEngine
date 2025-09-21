# >>> AUTO-GEN BEGIN: AE Scoring v1.0
"""Scoring utilities exposed at the package level."""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Optional

from ..core.bodies import body_class
from ..core.scoring import compute_domain_factor
from ..scoring_legacy import DEFAULT_ASPECTS, OrbCalculator, load_dignities, lookup_dignities

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


# Policy loader
_DEFAULT_POLICY_PATH = (
    Path(__file__).resolve().parents[2] / "profiles" / "scoring_policy.json"
)


def _load_policy(custom_path: Optional[str] = None) -> dict:
    path = Path(custom_path) if custom_path else _DEFAULT_POLICY_PATH
    if path.exists():
        raw = path.read_text()
        cleaned = "\n".join(
            line for line in raw.splitlines() if not line.strip().startswith("#")
        ).strip()
        data = json.loads(cleaned) if cleaned else {}
    else:
        data = {
            "curve": {
                "kind": "gaussian",
                "sigma_frac_of_orb": 0.5,
                "min_score": 0.0,
                "max_score": 1.0,
            },
            "applying_bias": {"enabled": True, "factor": 1.10},
            "partile": {
                "enabled": True,
                "threshold_deg": 0.1667,
                "boost_factor": 1.25,
            },
            "base_weights": {
                "decl_parallel": 0.70,
                "decl_contra": 0.65,
                "antiscia": 0.55,
                "contra_antiscia": 0.50,
            },
            "body_class_weights": {
                "luminary": 1.0,
                "personal": 0.95,
                "social": 0.9,
                "outer": 0.85,
            },
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
    clamped = max(0.0, min(1.0, x))
    if kind == "linear":
        y = 1.0 - clamped
    elif kind == "cosine":
        y = 0.5 * (1.0 + math.cos(math.pi * clamped))
    elif kind == "logistic":
        y = 1.0 / (1.0 + math.exp(10.0 * (clamped - 0.5)))
    else:  # gaussian
        z = clamped / 0.5  # sigma = 0.5
        y = math.exp(-0.5 * z * z)
    return min_v + (max_v - min_v) * y


@dataclass
class ScoreInputs:
    """Inputs for a scoring evaluation."""

    kind: str
    orb_abs_deg: float
    orb_allow_deg: float
    moving: str
    target: str
    applying_or_separating: str


@dataclass
class ScoreResult:
    """Structured score output."""

    score: float
    details: dict


def compute_score(inp: ScoreInputs, *, policy_path: Optional[str] = None) -> ScoreResult:
    policy = _load_policy(policy_path)

    # 1) Normalized distance within orb
    ratio = inp.orb_abs_deg / max(inp.orb_allow_deg, 1e-9)
    distance = min(1.0, max(0.0, ratio))
    curve = policy["curve"]
    score = _curve_score(
        curve.get("kind", "gaussian"),
        distance,
        min_v=curve.get("min_score", _DEF_MIN),
        max_v=curve.get("max_score", _DEF_MAX),
    )

    # 2) Base weight by contact kind
    score *= float(policy["base_weights"].get(inp.kind, 1.0))

    # 3) Body/Pair weights
    moving_class = body_class(inp.moving)
    target_class = body_class(inp.target)
    score *= float(policy["body_class_weights"].get(moving_class, 1.0))
    score *= float(policy["body_class_weights"].get(target_class, 1.0))
    pair_key = f"{moving_class}-{target_class}" if moving_class <= target_class else f"{target_class}-{moving_class}"
    score *= float(policy["pair_matrix"].get(pair_key, 1.0))

    # 4) Applying bias
    if policy.get("applying_bias", {}).get("enabled", True) and inp.applying_or_separating == "applying":
        score *= float(policy["applying_bias"].get("factor", 1.1))

    # 5) Partile boost
    partile = policy.get("partile", {})
    if partile.get("enabled", True) and inp.orb_abs_deg <= float(partile.get("threshold_deg", 0.1667)):
        score *= float(partile.get("boost_factor", 1.25))

    # Clamp
    score = max(0.0, min(1.0, score))

    return ScoreResult(
        score=score,
        details={
            "distance": distance,
            "curve": curve.get("kind", "gaussian"),
            "base": policy["base_weights"].get(inp.kind, 1.0),
            "classes": {"moving": moving_class, "target": target_class},
            "applying": inp.applying_or_separating,
        },
    )


for _legacy in ("dignity", "orb"):
    module = import_module(f"astroengine.scoring_legacy.{_legacy}")
    sys.modules[f"{__name__}.{_legacy}"] = module


def __getattr__(name: str):  # pragma: no cover - legacy attribute loader
    try:
        return sys.modules[f"{__name__}.{name}"]
    except KeyError as exc:  # pragma: no cover - compat path
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'") from exc


# >>> AUTO-GEN END: AE Scoring v1.0
