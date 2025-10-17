"""Tests for :mod:`astroengine.core.config`."""

from __future__ import annotations

import json

import pytest

from astroengine.core.config import load_profile_json, profile_into_ctx


def test_load_profile_json_rejects_malformed_json(tmp_path):
    """Malformed JSON documents should raise a ``JSONDecodeError``."""

    path = tmp_path / "broken.json"
    path.write_text("{not-valid", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        load_profile_json(path)


def test_profile_into_ctx_preserves_existing_identifiers_and_policies():
    """Existing context keys are not overwritten when merging profiles."""

    base_ctx = {
        "profile_id": "preset",
        "orb_policy": {"default": 5},
        "severity_policy": {"rule": "keep"},
        "visibility_policy": "custom",
        "severity_modifiers": {"retrograde": 0.8},
    }

    profile = {
        "id": "override-me",
        "policies": {
            "orb": {"default": 8},
            "severity": {"rule": "replace"},
            "visibility": "profile",
        },
        "severity_modifiers": {"retrograde": 0.5, "combust": 1.1},
    }

    merged = profile_into_ctx(base_ctx, profile)

    # Pre-existing values remain unchanged.
    assert merged["profile_id"] == "preset"
    assert merged["orb_policy"] == {"default": 5}
    assert merged["severity_policy"] == {"rule": "keep"}
    assert merged["visibility_policy"] == "custom"

    # New modifier keys are added without replacing existing ones.
    assert merged["severity_modifiers"] == {
        "retrograde": 0.8,
        "combust": 1.1,
    }


def test_profile_into_ctx_populates_missing_profile_fields():
    """Profile data populates gaps in the engine context."""

    ctx = {}
    profile = {
        "id": "vca",
        "policies": {
            "orb": {"default": 6.0},
            "severity": {"rule": "stack"},
        },
        "severity_modifiers": {"new": 1.05},
    }

    merged = profile_into_ctx(ctx, profile)

    assert merged["profile_id"] == "vca"
    assert merged["orb_policy"] == {"default": 6.0}
    assert merged["severity_policy"] == {"rule": "stack"}
    assert merged["severity_modifiers"] == {"new": 1.05}
