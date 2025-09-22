"""Scoring helpers for contact events (aspects, declinations, mirrors)."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Mapping

from ..core.bodies import body_class
from ..infrastructure.paths import profiles_dir
from ..refine import fuzzy_membership
from ..plugins import apply_score_extensions

__all__ = [
    "ScoreInputs",
    "ScoreResult",
    "compute_score",
    "compute_uncertainty_confidence",
]
_DEF_POLICY = profiles_dir() / "scoring_policy.json"


@dataclass(frozen=True)
class ScoreInputs:
    kind: str
    orb_abs_deg: float
    orb_allow_deg: float
    moving: str
    target: str
    applying_or_separating: str
    corridor_width_deg: float | None = None
    corridor_profile: str = "gaussian"
    resonance_weights: Mapping[str, float] | None = None
    observers: int = 1
    overlap_count: int = 1


@dataclass
class ScoreResult:
    score: float
    components: dict[str, float]
    confidence: float = 1.0


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


def _resonance_factor(inputs: ScoreInputs) -> float:
    weights = inputs.resonance_weights or {}
    if not weights:
        return 1.0
    mind = float(weights.get("mind", 1.0))
    body = float(weights.get("body", 1.0))
    spirit = float(weights.get("spirit", 1.0))
    if inputs.corridor_width_deg is None or inputs.corridor_width_deg >= inputs.orb_allow_deg:
        numerator = mind + body
    else:
        numerator = mind + spirit
    denominator = max(mind + body + spirit, 1e-9)
    return max(numerator / denominator, 0.0)


def compute_uncertainty_confidence(
    orb_allow_deg: float,
    corridor_width_deg: float | None,
    *,
    observers: int = 1,
    overlap_count: int = 1,
) -> float:
    """Return a 0–1 confidence score mixing orb width and observer effects."""

    width = max(float(orb_allow_deg), 1e-9)
    corridor = float(corridor_width_deg) if corridor_width_deg else width
    corridor_ratio = width / (width + corridor)
    observer_penalty = 1.0 / (1.0 + math.log1p(max(0, observers - 1)))
    overlap_penalty = 1.0 / (1.0 + max(0, overlap_count - 1) * 0.5)
    confidence = corridor_ratio * observer_penalty * overlap_penalty
    return max(0.0, min(confidence, 1.0))


def compute_score(inputs: ScoreInputs, *, policy_path: str | None = None) -> ScoreResult:
    policy = _load_policy(policy_path)
    base_weight = float(policy.get("base_weights", {}).get(inputs.kind, 0.0))
    if base_weight <= 0.0 or inputs.orb_allow_deg <= 0:
        confidence = compute_uncertainty_confidence(
            inputs.orb_allow_deg,
            inputs.corridor_width_deg,
            observers=inputs.observers,
            overlap_count=inputs.overlap_count,
        )
        result = ScoreResult(0.0, {"base_weight": base_weight}, confidence)
        return apply_score_extensions(inputs, result)

    curve = policy.get("curve", {})
    sigma_frac = float(curve.get("sigma_frac_of_orb", 0.5))
    sigma = max(inputs.orb_allow_deg * sigma_frac, 1e-6)
    min_score = float(curve.get("min_score", 0.0))
    max_score = float(curve.get("max_score", 1.0))
    gaussian_value = _gaussian(inputs.orb_abs_deg, sigma)
    corridor_factor = 1.0
    if inputs.corridor_width_deg:
        corridor_factor = fuzzy_membership(
            inputs.orb_abs_deg,
            float(inputs.corridor_width_deg),
            profile=inputs.corridor_profile,
            softness=sigma_frac,
        )
    normalized = min_score + (max_score - min_score) * gaussian_value * corridor_factor

    cls_m = body_class(inputs.moving)
    cls_t = body_class(inputs.target)
    body_weights = policy.get("body_class_weights", {})
    weight_m = float(body_weights.get(cls_m, 1.0))
    weight_t = float(body_weights.get(cls_t, 1.0))
    pair_key = "-".join(sorted((cls_m, cls_t)))
    pair_matrix = policy.get("pair_matrix", {})
    pair_weight = float(pair_matrix.get(pair_key, 1.0))

    resonance_factor = _resonance_factor(inputs)
    score = base_weight * weight_m * weight_t * pair_weight * normalized * resonance_factor

    phase = (inputs.applying_or_separating or "").lower()
    applying_cfg = policy.get("applying_bias", {})
    if applying_cfg.get("enabled") and phase == "applying":
        score *= float(applying_cfg.get("factor", 1.0))

    partile_cfg = policy.get("partile", {})
    if partile_cfg.get("enabled") and inputs.orb_abs_deg <= float(
        partile_cfg.get("threshold_deg", 0.0)
    ):
        score *= float(partile_cfg.get("boost_factor", 1.0))

    confidence = compute_uncertainty_confidence(
        inputs.orb_allow_deg,
        inputs.corridor_width_deg,
        observers=inputs.observers,
        overlap_count=inputs.overlap_count,
    )
    score *= max(confidence, 1e-9)
    score = max(min(score, max_score), min_score)
    components = {
        "base_weight": base_weight,
        "weight_m": weight_m,
        "weight_t": weight_t,
        "pair_weight": pair_weight,
        "gaussian": gaussian_value,
        "corridor_factor": corridor_factor,
        "resonance_factor": resonance_factor,
        "confidence": confidence,
    }
    result = ScoreResult(score=score, components=components, confidence=confidence)
    return apply_score_extensions(inputs, result)
