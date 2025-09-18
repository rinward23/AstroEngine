"""Domain scoring utilities."""

from __future__ import annotations

import math
from typing import Mapping


def compute_domain_factor(
    domains: Mapping[str, float] | None,
    multipliers: Mapping[str, float] | None,
    method: str = "weighted",
    temperature: float = 8.0,
) -> float:
    """Return a multiplicative factor ≥0 based on domain weights and profile multipliers."""

    if not domains:
        return 1.0
    multipliers = multipliers or {}
    total = sum(max(0.0, float(value)) for value in domains.values())
    if total <= 0.0:
        return 1.0
    probabilities = {key: float(value) / total for key, value in domains.items()}
    multipliers = {key: float(multipliers.get(key, 1.0)) for key in probabilities}
    method_normalized = (method or "weighted").lower()

    if method_normalized == "top":
        top_domain = max(probabilities.items(), key=lambda kv: kv[1])[0]
        return multipliers.get(top_domain, 1.0)

    if method_normalized == "softmax":
        logits = {key: math.log(max(1e-9, multipliers[key])) for key in probabilities}
        temp = max(1e-6, float(temperature))
        max_logit = max(logits.values())
        exps = {key: math.exp((logits[key] - max_logit) / temp) for key in probabilities}
        normalizer = sum(exps.values()) or 1.0
        distribution = {key: exps[key] / normalizer for key in probabilities}
        return sum(distribution[key] * multipliers[key] for key in probabilities)

    return sum(probabilities[key] * multipliers[key] for key in probabilities)


__all__ = ["compute_domain_factor"]
