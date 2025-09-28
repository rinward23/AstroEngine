"""Scoring helpers for synastry aspect hits."""

from __future__ import annotations

from collections.abc import Iterable

from astroengine.core.bodies import body_class

from .models import Hit, Scores
from .policy import ASPECT_FAMILY_MAP, Weights

__all__ = ["compute_scores"]


_BODY_CLASS_TO_FAMILY = {
    "luminary": "luminary",
    "personal": "personal",
    "social": "social",
    "outer": "outer",
    "centaur": "outer",
    "asteroid": "outer",
    "tno": "outer",
    "point": "points",
}

_DEFAULT_ASPECT_FAMILIES = ("harmonious", "challenging", "neutral")
_DEFAULT_BODY_FAMILIES = ("luminary", "personal", "social", "outer", "points")


def _body_family(name: str) -> str:
    cls = body_class(name)
    return _BODY_CLASS_TO_FAMILY.get(cls, "outer")


def compute_scores(hits: Iterable[Hit], weights: Weights) -> Scores:
    """Aggregate weighted scores for ``hits`` using ``weights``."""

    aspect_scores = {family: 0.0 for family in _DEFAULT_ASPECT_FAMILIES}
    body_scores = {family: 0.0 for family in _DEFAULT_BODY_FAMILIES}
    raw_total = 0.0

    for hit in hits:
        severity = float(hit.severity)
        raw_total += severity
        aspect_family = ASPECT_FAMILY_MAP.get(hit.aspect, "neutral")
        aspect_weight = weights.aspect_weight(aspect_family)
        family_a = _body_family(hit.body_a)
        family_b = _body_family(hit.body_b)
        body_weight_a = weights.body_weight(family_a)
        body_weight_b = weights.body_weight(family_b)
        score = severity * aspect_weight * body_weight_a * body_weight_b
        if hit.aspect == 0:
            score *= float(weights.conjunction_sign)
        aspect_scores[aspect_family] += score
        body_scores[family_a] += score
        body_scores[family_b] += score

    overall = sum(aspect_scores.values())
    return Scores(
        by_aspect_family={k: float(v) for k, v in aspect_scores.items()},
        by_body_family={k: float(v) for k, v in body_scores.items()},
        overall=float(overall),
        rawTotal=float(raw_total),
    )

