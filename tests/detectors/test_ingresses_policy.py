"""Tests for ingress policy helpers."""

from __future__ import annotations

import types
from collections.abc import Mapping

import pytest

import astroengine.detectors.ingresses as ingresses
from astroengine.detectors.ingresses import (
    _default_bodies,
    _ingress_policy,
    _policy_from_mapping,
    _resolve_policy,
)


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"inner_mode": "invalid"},
        {"enabled": False, "include_moon": True, "inner_mode": "angles_only"},
    ],
)
def test_policy_from_mapping_handles_payloads(payload: Mapping[str, object] | None) -> None:
    """_policy_from_mapping should coerce payload values safely."""

    policy = _policy_from_mapping(payload)

    if not isinstance(payload, Mapping):
        assert policy.enabled is True
        assert policy.include_moon is False
        assert policy.inner_mode == "angles_only"
    else:
        assert policy.enabled is bool(payload.get("enabled", True))
        assert policy.include_moon is bool(payload.get("include_moon", False))
        expected_mode = payload.get("inner_mode", "angles_only")
        expected_normalized = str(expected_mode or "angles_only").strip().lower()
        if expected_normalized not in {"always", "angles_only"}:
            expected_normalized = "angles_only"
        assert policy.inner_mode == expected_normalized


def test_ingress_policy_falls_back_when_flags_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing feature flag mappings should revert to defaults."""

    scenarios = [
        {},
        {"feature_flags": {}},
    ]

    for scenario in scenarios:
        monkeypatch.setattr(ingresses, "load_base_profile", lambda: scenario)
        policy = _ingress_policy()
        assert policy.enabled is True
        assert policy.include_moon is False
        assert policy.inner_mode == "angles_only"


def test_resolve_policy_rejects_invalid_inner_mode() -> None:
    """Invalid inner mode inputs must raise ValueError."""

    with pytest.raises(ValueError):
        _resolve_policy(include_moon=None, inner_mode="sometimes", profile={})


@pytest.mark.parametrize(
    "profile",
    [
        {"feature_flags": {"ingresses": {"enabled": True}}},
        types.MappingProxyType({"feature_flags": {"ingresses": {"enabled": True}}}),
    ],
)
def test_resolve_policy_overrides_enable_inner_bodies(profile: Mapping[str, object]) -> None:
    """Explicit overrides should inject inner bodies and the Moon."""

    policy = _resolve_policy(
        include_moon=True,
        inner_mode="always",
        profile=profile,
    )
    assert policy.enabled is True
    assert policy.include_moon is True
    assert policy.inner_mode == "always"

    bodies = _default_bodies(policy)
    assert bodies[0] == "sun"
    assert bodies[1:4] == ("mercury", "venus", "moon")
    # Remaining bodies preserve the configured base ordering without duplication.
    assert bodies[4:] == ("mars", "jupiter", "saturn", "uranus", "neptune", "pluto")


def test_disabled_policy_skips_bodies_and_deduplicates_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Profiles can disable the policy, leaving no bodies even with overrides."""

    profile_payload = {
        "feature_flags": {
            "ingresses": {
                "enabled": False,
                "include_moon": True,
                "inner_mode": "always",
            }
        }
    }
    monkeypatch.setattr(ingresses, "load_base_profile", lambda: profile_payload)

    policy = _ingress_policy()
    assert policy.enabled is False

    override_list = ["sun", "moon", "sun", "venus", "moon"]
    deduped = tuple(dict.fromkeys(override_list))
    assert deduped == ("sun", "moon", "venus")

    body_tuple = () if not policy.enabled else _default_bodies(policy)
    assert body_tuple == ()
