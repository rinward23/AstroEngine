from __future__ import annotations

import pytest

from astroengine.config.settings import (
    _LENGTH_ORDER,
    _TONE_ORDER,
    NarrativeCfg,
    NarrativeEsotericCfg,
    NarrativeMixCfg,
    Settings,
    _vote_enum,
    compose_narrative_from_mix,
)


def test_vote_enum_prefers_order_on_ties() -> None:
    assert _vote_enum(["teaching", "brief"], [1.0, 1.0], _TONE_ORDER) == "brief"
    assert _vote_enum(["neutral", "teaching"], [0.3, 0.3], _TONE_ORDER) == "neutral"
    assert _vote_enum(["long", "short"], [0.5, 0.5], _LENGTH_ORDER) == "short"


def test_compose_narrative_mix_merges_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    base = Settings()
    base.narrative = NarrativeCfg(
        mode="base",
        library="western_basic",
        tone="neutral",
        length="medium",
        language="en",
        disclaimers=True,
        verbosity=0.5,
        sources={"astro_data": False, "psych": False},
        frameworks={"hellenistic": False, "modern": False},
        esoteric=NarrativeEsotericCfg(
            tarot_enabled=False,
            tarot_deck="rws",
            numerology_enabled=False,
            numerology_system="pythagorean",
        ),
    )

    overlays = {
        "profile_a": {
            "narrative": {
                "mode": "profile_a",
                "library": "western_basic",
                "tone": "teaching",
                "length": "long",
                "verbosity": 0.8,
                "sources": {"astro_data": True, "tradition": True, "psych": False},
                "frameworks": {"hellenistic": True},
                "esoteric": {
                    "tarot_enabled": True,
                    "tarot_deck": "thoth",
                    "numerology_enabled": False,
                    "numerology_system": "pythagorean",
                },
                "disclaimers": True,
            }
        },
        "profile_b": {
            "narrative": {
                "mode": "profile_b",
                "library": "vedic",
                "tone": "brief",
                "length": "short",
                "verbosity": 0.2,
                "sources": {"astro_data": False, "tradition": True, "psych": True},
                "frameworks": {"hellenistic": False, "modern": True},
                "esoteric": {
                    "tarot_enabled": False,
                    "tarot_deck": "rws",
                    "numerology_enabled": True,
                    "numerology_system": "chaldean",
                },
                "disclaimers": False,
            }
        },
    }

    calls: list[str] = []

    def fake_loader(name: str) -> dict:
        calls.append(name)
        return overlays[name]

    monkeypatch.setattr(
        "astroengine.config.narrative_profiles.load_narrative_profile_overlay",
        fake_loader,
    )

    mix = NarrativeMixCfg(enabled=True, normalize=True, profiles={"profile_a": 0.7, "profile_b": 0.3})
    result = compose_narrative_from_mix(base, mix)

    assert set(calls) == {"profile_a", "profile_b"}
    assert result.mode == "mixed"
    assert result.library == "western_basic"
    assert result.tone == "teaching"
    assert result.length == "long"
    assert result.verbosity == pytest.approx(0.62, abs=1e-9)
    assert result.sources == {
        "astro_data": True,
        "psych": False,
        "tradition": True,
    }
    assert result.frameworks == {"hellenistic": True, "modern": False}
    assert result.esoteric.tarot_enabled is True
    assert result.esoteric.tarot_deck == "thoth"
    assert result.esoteric.numerology_enabled is False
    assert result.esoteric.numerology_system == "chaldean"
    assert result.disclaimers is True
