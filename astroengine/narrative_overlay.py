"""Narrative helpers incorporating uncertainty-aware resonance cues."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .profiles import ResonanceWeights
from .utils.i18n import translate

__all__ = [
    "NarrativeOverlay",
    "select_resonance_focus",
    "format_confidence_band",
    "apply_resonance_overlay",
]


@dataclass(frozen=True)
class NarrativeOverlay:
    """Lightweight container returned to narrative composers."""

    focus: str
    confidence: float
    emphasis: Mapping[str, float]
    phrases: Sequence[str]

    def as_dict(self) -> dict[str, object]:
        return {
            "focus": self.focus,
            "confidence": self.confidence,
            "emphasis": dict(self.emphasis),
            "phrases": list(self.phrases),
        }


def select_resonance_focus(
    weights: Mapping[str, float], confidence: float, corridor_ratio: float
) -> str:
    """Return the dominant narrative layer based on confidence and corridor ratio."""

    normalized = ResonanceWeights(
        mind=float(weights.get("mind", 1.0)),
        body=float(weights.get("body", 1.0)),
        spirit=float(weights.get("spirit", 1.0)),
    ).normalized()
    if corridor_ratio < 1.0 or confidence < 0.5:
        return "spirit" if normalized.spirit >= normalized.mind else "mind"
    if corridor_ratio > 1.5:
        return "body" if normalized.body >= normalized.mind else "mind"
    return "mind"


def format_confidence_band(confidence: float) -> str:
    """Return a human friendly label for the supplied confidence value."""

    c = max(0.0, min(confidence, 1.0))
    if c >= 0.75:
        return translate("narrative.overlay.confidence.high", value=c)
    if c >= 0.45:
        return translate("narrative.overlay.confidence.moderate", value=c)
    return translate("narrative.overlay.confidence.low", value=c)


def apply_resonance_overlay(
    weights: Mapping[str, float] | ResonanceWeights,
    confidence: float,
    corridor_width_deg: float | None,
    orb_allow_deg: float,
    *,
    base_phrases: Sequence[str] | None = None,
) -> NarrativeOverlay:
    """Return a :class:`NarrativeOverlay` describing how to slant interpretations."""

    if isinstance(weights, ResonanceWeights):
        resonance = weights
    else:
        resonance = ResonanceWeights(
            mind=float(weights.get("mind", 1.0)),
            body=float(weights.get("body", 1.0)),
            spirit=float(weights.get("spirit", 1.0)),
        )
    corridor = float(corridor_width_deg) if corridor_width_deg else float(orb_allow_deg)
    corridor_ratio = corridor / max(float(orb_allow_deg), 1e-9)
    focus = select_resonance_focus(resonance.as_mapping(), confidence, corridor_ratio)
    emphasis = resonance.as_mapping()
    phrases = list(base_phrases or [])
    phrases.append(format_confidence_band(confidence))
    if focus == "spirit":
        phrases.append(translate("narrative.overlay.focus.spirit"))
    elif focus == "body":
        phrases.append(translate("narrative.overlay.focus.body"))
    else:
        phrases.append(translate("narrative.overlay.focus.mind"))
    return NarrativeOverlay(
        focus=focus, confidence=confidence, emphasis=emphasis, phrases=phrases
    )
