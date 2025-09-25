"""Scoring helpers for contact events (aspects, declinations, mirrors)."""

from __future__ import annotations

import math
from collections.abc import Mapping
from collections.abc import Mapping as MappingType
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from ..core.bodies import body_class
from ..infrastructure.paths import profiles_dir
from ..plugins import apply_score_extensions
from ..refine import branch_sensitive_angles, fuzzy_membership
from ..utils import deep_merge, load_json_document
from ..utils.angles import delta_angle
from .tradition import get_tradition_spec

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
    severity_modifiers: Mapping[str, float] | None = None
    dignity_modifiers: Mapping[str, float] | None = None
    retrograde: bool = False
    combust_state: str | None = None
    out_of_bounds: bool = False
    custom_modifiers: Mapping[str, float] | None = None
    angle_deg: float | None = None
    tradition_profile: str | None = None
    chart_sect: str | None = None
    uncertainty_bias: Mapping[str, str] | None = None


@dataclass
class ScoreResult:
    score: float
    components: dict[str, float]
    confidence: float = 1.0


@cache
def _load_policy(path: str | None) -> dict:
    policy_path = Path(path) if path else _DEF_POLICY
    return load_json_document(policy_path)


def _resolve_policy(
    policy: Mapping[str, object] | None, policy_path: str | None
) -> dict:
    if policy is not None:
        return {key: value for key, value in policy.items()}
    return _load_policy(policy_path)


def _gaussian(value: float, sigma: float) -> float:
    if sigma <= 0:
        return 0.0
    return math.exp(-0.5 * (value / sigma) ** 2)


def _dignity_factor(
    policy: Mapping[str, object], inputs: ScoreInputs
) -> tuple[float, dict[str, float]]:
    modifiers = inputs.dignity_modifiers or {}
    factor = 1.0
    applied: dict[str, float] = {}
    table: dict[str, float] = {}
    base = policy.get("dignity_weights", {})
    if isinstance(base, Mapping):
        table = {str(name).lower(): float(weight) for name, weight in base.items()}
    for key, value in modifiers.items():
        label = str(key)
        if isinstance(value, str):
            numeric = table.get(value.lower())
            if numeric is None:
                continue
            label = f"{key}:{value.lower()}"
        else:
            numeric = float(value)
        factor *= float(numeric)
        applied[label] = float(numeric)
    return max(factor, 0.0), applied


def _condition_factor(
    policy: Mapping[str, object], inputs: ScoreInputs
) -> tuple[float, dict[str, float]]:
    base = policy.get("condition_modifiers", {})
    table: dict[str, float] = {}
    if isinstance(base, Mapping):
        for key, value in base.items():
            if isinstance(value, int | float):
                table[key] = float(value)
    if inputs.severity_modifiers:
        for key, value in inputs.severity_modifiers.items():
            table[key] = float(value)

    factor = 1.0
    applied: dict[str, float] = {}

    if inputs.retrograde:
        value = table.get("retrograde", 1.0)
        factor *= value
        applied["retrograde"] = value

    state = (inputs.combust_state or "").lower()
    for key in ("cazimi", "combust", "under_beams"):
        if state == key:
            value = table.get(key, 1.0)
            factor *= value
            applied[key] = value
            break

    if inputs.out_of_bounds:
        value = table.get("out_of_bounds", 1.0)
        factor *= value
        applied["out_of_bounds"] = value

    if inputs.custom_modifiers:
        for key, value in inputs.custom_modifiers.items():
            numeric = float(value)
            factor *= numeric
            applied[key] = numeric

    sect_table = policy.get("sect_bias", {})
    chart_sect = (inputs.chart_sect or "").lower()
    if chart_sect and isinstance(sect_table, Mapping):
        sect_entry = sect_table.get(chart_sect)
        if isinstance(sect_entry, Mapping):
            for group_name, payload in sect_entry.items():
                if not isinstance(payload, Mapping):
                    continue
                if inputs.moving in payload:
                    numeric = float(payload[inputs.moving])
                    factor *= numeric
                    applied[f"sect:{inputs.moving}:{group_name}"] = numeric
                if inputs.target in payload:
                    numeric = float(payload[inputs.target])
                    factor *= numeric
                    applied[f"sect:{inputs.target}:{group_name}"] = numeric

    return max(factor, 0.0), applied


def _normalize_weights(weights: Mapping[str, float]) -> dict[str, float]:
    positive = {key: max(float(value), 0.0) for key, value in weights.items()}
    total = sum(positive.values())
    if total <= 0.0:
        return {"mind": 1 / 3, "body": 1 / 3, "spirit": 1 / 3}
    return {key: value / total for key, value in positive.items()}


def _resonance_factor(inputs: ScoreInputs) -> tuple[float, dict[str, float]]:
    weights = inputs.resonance_weights or {}
    if not weights:
        return 1.0, {}
    normalized = _normalize_weights(
        {
            "mind": float(weights.get("mind", 1.0)),
            "body": float(weights.get("body", 1.0)),
            "spirit": float(weights.get("spirit", 1.0)),
        }
    )
    corridor = inputs.corridor_width_deg or inputs.orb_allow_deg
    ratio = corridor / max(inputs.orb_allow_deg, 1e-9)
    bias_map = inputs.uncertainty_bias or {}
    if ratio < 1.0:
        focus_key = str(bias_map.get("narrow", "spirit")) or "spirit"
    elif ratio > 1.5:
        focus_key = str(bias_map.get("broad", "body")) or "body"
    else:
        focus_key = str(bias_map.get("standard", "mind")) or "mind"
    focus_key = focus_key.lower()
    baseline = 1.0 / 3.0
    emphasis = normalized.get(focus_key, baseline)
    factor = 1.0 + (emphasis - baseline) * 0.5
    components = {
        "focus": focus_key,
        "ratio": ratio,
        "mind": normalized.get("mind", baseline),
        "body": normalized.get("body", baseline),
        "spirit": normalized.get("spirit", baseline),
    }
    return max(factor, 0.0), components


def _tradition_factor(
    policy: Mapping[str, object], inputs: ScoreInputs
) -> tuple[float, dict[str, float]]:
    name = (inputs.tradition_profile or "").strip().lower()
    if not name:
        return 1.0, {}
    spec = get_tradition_spec(name)
    if spec is None:
        return 1.0, {}

    components: dict[str, float] = {"profile": 1.0}
    factor = 1.0
    if inputs.angle_deg is not None:
        angles = spec.drishti_angles(inputs.moving)
        if angles:
            corridor = inputs.corridor_width_deg or inputs.orb_allow_deg
            if corridor <= 0.0:
                corridor = inputs.orb_allow_deg
            memberships: list[float] = []
            for angle in angles:
                delta = abs(delta_angle(float(inputs.angle_deg), angle))
                membership = fuzzy_membership(
                    delta,
                    corridor,
                    profile=inputs.corridor_profile,
                    softness=float(
                        policy.get("curve", {}).get("sigma_frac_of_orb", 0.5)
                    ),
                )
                components[f"drishti:{inputs.moving}:{angle:.1f}"] = membership
                memberships.append(membership)
            if memberships:
                average = sum(memberships) / len(memberships)
                severity_weights = policy.get("body_severity_weights", {})
                severity = 1.0
                if isinstance(severity_weights, MappingType):
                    severity = float(severity_weights.get(inputs.moving, 1.0))
                scalar = spec.drishti_scalar(inputs.moving)
                boost = 1.0 + (severity - 1.0) * scalar
                factor *= 1.0 + (boost - 1.0) * average
                components["drishti_average"] = average
                components["drishti_scalar"] = scalar
    bias = spec.resonance_bias()
    if bias:
        for key, value in bias.items():
            components[f"bias:{key}"] = float(value)
    return max(factor, 0.0), components


def _fractal_factor(
    policy: Mapping[str, object], inputs: ScoreInputs
) -> tuple[float, dict[str, float]]:
    if inputs.angle_deg is None:
        return 1.0, {}
    patterns = policy.get("fractal_patterns", {})
    if not isinstance(patterns, Mapping) or not patterns.get("enabled", True):
        return 1.0, {}
    harmonics = patterns.get("harmonics", (2, 3, 4, 6))
    try:
        harmonics_tuple = tuple(int(h) for h in harmonics)
    except Exception:  # pragma: no cover - defensive
        harmonics_tuple = (2, 3, 4, 6)
    include_cardinals = bool(patterns.get("include_cardinals", True))
    corridor = inputs.corridor_width_deg or inputs.orb_allow_deg
    if corridor <= 0.0:
        corridor = inputs.orb_allow_deg
    softness = float(patterns.get("softness", 0.5))
    baseline = float(patterns.get("baseline", 0.5))
    curve = policy.get("curve", {})
    default_spread = 0.5
    if isinstance(curve, Mapping):
        default_spread = float(curve.get("sigma_frac_of_orb", 0.5))
    spread = float(patterns.get("spread", default_spread))
    angles = branch_sensitive_angles(
        float(inputs.angle_deg),
        harmonics=harmonics_tuple,
        include_cardinals=include_cardinals,
    )
    contributions: dict[str, float] = {}
    total = 0.0
    for angle in angles:
        delta = abs(delta_angle(float(inputs.angle_deg), angle))
        membership = fuzzy_membership(
            delta,
            corridor,
            profile=inputs.corridor_profile,
            softness=softness,
        )
        contributions[f"{angle:.2f}"] = membership
        total += membership
    if not contributions:
        return 1.0, {}
    mean = total / len(contributions)
    factor = 1.0 + (mean - baseline) * spread
    contributions["mean"] = mean
    contributions["spread"] = spread
    return max(factor, 0.0), contributions


def compute_uncertainty_confidence(
    orb_allow_deg: float,
    corridor_width_deg: float | None,
    *,
    observers: int = 1,
    overlap_count: int = 1,
    orb_abs_deg: float | None = None,
    resonance_weights: Mapping[str, float] | None = None,
    uncertainty_bias: Mapping[str, str] | None = None,
) -> float:
    """Return a 0–1 confidence score mixing orb width and observer effects."""

    width = max(float(orb_allow_deg), 1e-9)
    corridor = float(corridor_width_deg) if corridor_width_deg else width
    corridor_ratio = width / (width + corridor)
    closeness = 1.0
    if orb_abs_deg is not None:
        closeness = max(0.0, 1.0 - float(orb_abs_deg) / (width + 1e-9))
    observer_penalty = 1.0 / (1.0 + math.log1p(max(0, observers - 1)))
    overlap_penalty = 1.0 / (1.0 + max(0, overlap_count - 1) * 0.5)
    base = (corridor_ratio + closeness) / 2.0
    bias_multiplier = 1.0
    if uncertainty_bias and resonance_weights:
        ratio = corridor / width
        focus_key = "mind"
        if ratio < 1.0:
            focus_key = str(uncertainty_bias.get("narrow", "spirit")) or "spirit"
        elif ratio > 1.5:
            focus_key = str(uncertainty_bias.get("broad", "body")) or "body"
        else:
            focus_key = str(uncertainty_bias.get("standard", "mind")) or "mind"
        focus_key = focus_key.lower()
        normalized = _normalize_weights(
            {
                "mind": float(resonance_weights.get("mind", 1.0)),
                "body": float(resonance_weights.get("body", 1.0)),
                "spirit": float(resonance_weights.get("spirit", 1.0)),
            }
        )
        bias_multiplier = normalized.get(focus_key, 1.0)
    confidence = base * observer_penalty * overlap_penalty * bias_multiplier
    return max(0.0, min(confidence, 1.0))


def compute_score(
    inputs: ScoreInputs,
    *,
    policy_path: str | None = None,
    policy: Mapping[str, object] | None = None,
) -> ScoreResult:
    policy_dict = _resolve_policy(policy, policy_path)
    tradition_overrides: Mapping[str, object] | None = None
    if inputs.tradition_profile:
        traditions = policy_dict.get("traditions", {})
        if isinstance(traditions, Mapping):
            candidate = traditions.get(inputs.tradition_profile.lower())
            if isinstance(candidate, Mapping):
                tradition_overrides = candidate
                policy_dict = deep_merge(policy_dict, candidate)
    base_weight = float(policy_dict.get("base_weights", {}).get(inputs.kind, 0.0))
    if base_weight <= 0.0 or inputs.orb_allow_deg <= 0:
        confidence = compute_uncertainty_confidence(
            inputs.orb_allow_deg,
            inputs.corridor_width_deg,
            observers=inputs.observers,
            overlap_count=inputs.overlap_count,
            orb_abs_deg=inputs.orb_abs_deg,
            resonance_weights=inputs.resonance_weights,
            uncertainty_bias=inputs.uncertainty_bias,
        )
        result = ScoreResult(0.0, {"base_weight": base_weight}, confidence)
        return apply_score_extensions(inputs, result)

    curve = policy_dict.get("curve", {})
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
    if inputs.orb_abs_deg >= inputs.orb_allow_deg:
        gaussian_value = 0.0
        corridor_factor = 0.0
    normalized = min_score + (max_score - min_score) * gaussian_value * corridor_factor

    cls_m = body_class(inputs.moving)
    cls_t = body_class(inputs.target)
    body_weights = policy_dict.get("body_class_weights", {})
    weight_m = float(body_weights.get(cls_m, 1.0))
    weight_t = float(body_weights.get(cls_t, 1.0))
    pair_key = "-".join(sorted((cls_m, cls_t)))
    pair_matrix = policy_dict.get("pair_matrix", {})
    pair_weight = float(pair_matrix.get(pair_key, 1.0))

    resonance_factor, resonance_components = _resonance_factor(inputs)
    dignity_factor, dignity_components = _dignity_factor(policy_dict, inputs)
    condition_factor, condition_components = _condition_factor(policy_dict, inputs)
    tradition_factor, tradition_components = _tradition_factor(policy_dict, inputs)
    fractal_factor, fractal_components = _fractal_factor(policy_dict, inputs)
    score = (
        base_weight
        * weight_m
        * weight_t
        * pair_weight
        * normalized
        * resonance_factor
        * dignity_factor
        * condition_factor
        * tradition_factor
        * fractal_factor
    )

    phase = (inputs.applying_or_separating or "").lower()
    applying_cfg = policy_dict.get("applying_bias", {})
    if applying_cfg.get("enabled") and phase == "applying":
        score *= float(applying_cfg.get("factor", 1.0))

    partile_cfg = policy_dict.get("partile", {})
    if partile_cfg.get("enabled") and inputs.orb_abs_deg <= float(
        partile_cfg.get("threshold_deg", 0.0)
    ):
        score *= float(partile_cfg.get("boost_factor", 1.0))

    confidence = compute_uncertainty_confidence(
        inputs.orb_allow_deg,
        inputs.corridor_width_deg,
        observers=inputs.observers,
        overlap_count=inputs.overlap_count,
        orb_abs_deg=inputs.orb_abs_deg,
        resonance_weights=inputs.resonance_weights,
        uncertainty_bias=inputs.uncertainty_bias,
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
        "dignity_factor": dignity_factor,
        "condition_factor": condition_factor,
        "confidence": confidence,
        "tradition_factor": tradition_factor,
        "fractal_factor": fractal_factor,
    }
    if resonance_components:
        components["resonance_components"] = resonance_components
    if dignity_components:
        components["dignity_components"] = dignity_components
    if condition_components:
        components["condition_components"] = condition_components
    if tradition_components:
        components["tradition_components"] = tradition_components
    if fractal_components:
        components["fractal_components"] = fractal_components
    if tradition_overrides:
        components["tradition_override"] = list(tradition_overrides.keys())

    result = ScoreResult(score=score, components=components, confidence=confidence)
    return apply_score_extensions(inputs, result)
