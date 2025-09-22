from astroengine.narrative_overlay import (
    NarrativeOverlay,
    apply_resonance_overlay,
    select_resonance_focus,
)
from astroengine.profiles import ResonanceWeights


def test_select_resonance_focus_spirit_when_low_confidence():
    weights = {"mind": 1.0, "body": 1.0, "spirit": 2.0}
    focus = select_resonance_focus(weights, confidence=0.4, corridor_ratio=0.8)
    assert focus == "spirit"


def test_apply_resonance_overlay_returns_overlay():
    weights = ResonanceWeights(1.0, 1.0, 1.0)
    overlay = apply_resonance_overlay(weights, confidence=0.9, corridor_width_deg=3.0, orb_allow_deg=2.0)
    assert isinstance(overlay, NarrativeOverlay)
    assert overlay.focus in {"mind", "body", "spirit"}
    assert overlay.confidence == 0.9
    assert overlay.emphasis["mind"] > 0.0
