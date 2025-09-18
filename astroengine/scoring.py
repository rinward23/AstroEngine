"""Domain-based scoring helpers."""

from __future__ import annotations

import math
from typing import Mapping


# >>> AUTO-GEN BEGIN: Domain Scoring Utils v1.1


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
    normalized = {key: float(value) / total for key, value in domains.items()}

    active = {key: float(multipliers.get(key, 1.0)) for key in normalized}
    method = (method or "weighted").lower()

    if method == "top":
        dominant = max(normalized.items(), key=lambda kv: kv[1])[0]
        return active.get(dominant, 1.0)

    if method == "softmax":
        logits = {key: math.log(max(1e-9, active[key])) for key in normalized}
        temperature = max(1e-6, float(temperature))
        anchor = max(logits.values())
        exps = {key: math.exp((logits[key] - anchor) / temperature) for key in normalized}
        partition = sum(exps.values()) or 1.0
        weights = {key: exps[key] / partition for key in normalized}
        return sum(weights[key] * active[key] for key in normalized)

    return sum(normalized[key] * active[key] for key in normalized)


# >>> AUTO-GEN END: Domain Scoring Utils v1.1


__all__ = ["compute_domain_factor"]

