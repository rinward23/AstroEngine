"""Tests for built-in use-case settings profiles."""

from astroengine.config import (
    USE_CASE_PRESETS,
    apply_profile_overlay,
    built_in_profiles,
    default_settings,
    profile_description,
    profile_label,
)


def test_use_case_presets_are_registered() -> None:
    """Every declared use-case preset should be available in the registry."""

    built_ins = built_in_profiles()
    for name in USE_CASE_PRESETS:
        assert name in built_ins, f"missing preset: {name}"
        label = profile_label(name)
        assert isinstance(label, str) and label
        if name != "minimalist":
            # Minimalist predates the new descriptions but remains a use-case.
            assert profile_description(name)


def test_horary_strict_overlay_limits_bodies_and_orbs() -> None:
    """Horary strict keeps modern bodies disabled and tightens orbs."""

    base = default_settings()
    overlay = built_in_profiles()["horary_strict"]
    merged = apply_profile_overlay(base, overlay)

    assert not merged.bodies.groups.get("modern", True)
    assert merged.aspects.orbs_global == 3.5
    assert merged.timeline_ui.show_exact_only is True
    assert merged.dignities.weights.retrograde == -6


def test_electional_strict_overlay_enables_rigorous_search() -> None:
    """Electional strict should emphasise tight timing controls."""

    base = default_settings()
    overlay = built_in_profiles()["electional_strict"]
    merged = apply_profile_overlay(base, overlay)

    assert merged.electional.enabled is True
    assert merged.electional.step_minutes == 2
    assert merged.forecast_stack.consolidate_hours == 6
    assert merged.forecast_stack.exactness_deg == 0.2


def test_counseling_modern_overlay_emphasises_psychological_mode() -> None:
    """Counseling modern should include minor aspects and modern tone."""

    base = default_settings()
    overlay = built_in_profiles()["counseling_modern"]
    merged = apply_profile_overlay(base, overlay)

    assert merged.narrative.mode == "modern_psychological"
    assert merged.aspects.sets.get("minor") is True
    assert merged.bodies.groups.get("asteroids_major") is True
    assert merged.narrative.verbosity == 0.7


def test_minimalist_overlay_reduces_modern_bodies() -> None:
    """The minimalist preset should keep the focus on classical planets."""

    base = default_settings()
    overlay = built_in_profiles()["minimalist"]
    merged = apply_profile_overlay(base, overlay)

    assert merged.bodies.groups.get("modern") is False
    assert merged.aspects.detect_patterns is False
