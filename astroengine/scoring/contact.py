"""Scoring helpers for contact events (aspects, declinations, mirrors)."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ..core.bodies import body_class

__all__ = ["ScoreInputs", "ScoreResult", "compute_score"]


def _repository_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "profiles" / "scoring_policy.json"
        if candidate.exists():
            return parent
    raise FileNotFoundError(
        "Unable to locate 'profiles/scoring_policy.json' in repository parents."
    )


_DEF_POLICY = _repository_root() / "profiles" / "scoring_policy.json"


@dataclass(frozen=True)
class ScoreInputs:
    kind: str
    orb_abs_deg: float
    orb_allow_deg: float
    moving: str
    target: str
    applying_or_separating: str


@dataclass
class ScoreResult:
    score: float
    components: dict[str, float]


@lru_cache(maxsize=None)
def _load_policy(path: str | None) -> dict:
    policy_path = Path(path) if path else _DEF_POLICY
    raw = policy_path.read_text().splitlines()
    payload = "\n".join(line for line in raw if not line.strip().startswith("#"))
    return json.loads(payload)


def _gaussian(value: float, sigma: float) -> float:
    if sigma <= 0:
        return 0.0
    return math.exp(-0.5 * (value / sigma) ** 2)


def compute_score(inputs: ScoreInputs, *, policy_path: str | None = None) -> ScoreResult:
    policy = _load_policy(policy_path)
    base_weight = float(policy.get("base_weights", {}).get(inputs.kind, 0.0))
    if base_weight <= 0.0 or inputs.orb_allow_deg <= 0:
        return ScoreResult(0.0, {"base_weight": base_weight})

    curve = policy.get("curve", {})
    sigma_frac = float(curve.get("sigma_frac_of_orb", 0.5))
    sigma = max(inputs.orb_allow_deg * sigma_frac, 1e-6)
    min_score = float(curve.get("min_score", 0.0))
    max_score = float(curve.get("max_score", 1.0))
    gaussian_value = _gaussian(inputs.orb_abs_deg, sigma)
    normalized = min_score + (max_score - min_score) * gaussian_value

    cls_m = body_class(inputs.moving)
    cls_t = body_class(inputs.target)
    body_weights = policy.get("body_class_weights", {})
    weight_m = float(body_weights.get(cls_m, 1.0))
    weight_t = float(body_weights.get(cls_t, 1.0))
    pair_key = "-".join(sorted((cls_m, cls_t)))
    pair_matrix = policy.get("pair_matrix", {})
    pair_weight = float(pair_matrix.get(pair_key, 1.0))

    score = base_weight * weight_m * weight_t * pair_weight * normalized

    phase = (inputs.applying_or_separating or "").lower()
    applying_cfg = policy.get("applying_bias", {})
    if applying_cfg.get("enabled") and phase == "applying":
        score *= float(applying_cfg.get("factor", 1.0))

    partile_cfg = policy.get("partile", {})
    if partile_cfg.get("enabled") and inputs.orb_abs_deg <= float(
        partile_cfg.get("threshold_deg", 0.0)
    ):
        score *= float(partile_cfg.get("boost_factor", 1.0))

    score = max(min(score, max_score), min_score)
    components = {
        "base_weight": base_weight,
        "weight_m": weight_m,
        "weight_t": weight_t,
        "pair_weight": pair_weight,
        "gaussian": gaussian_value,
    }
    return ScoreResult(score=score, components=components)
