"""Ingress detector behavioural tests using deterministic stubs."""

from __future__ import annotations
from types import MappingProxyType

import pytest

import astroengine.detectors.ingresses as ingresses
from astroengine.detectors.ingresses import (
    _IngressPolicy,
    _default_bodies,
    _policy_from_mapping,
    _resolve_policy,
    find_house_ingresses,
    find_sign_ingresses,
)


def test_policy_from_mapping_normalizes_inputs() -> None:
    payload = {"enabled": 0, "include_moon": 1, "inner_mode": " unknown "}

    policy = _policy_from_mapping(payload)

    assert policy.enabled is False
    assert policy.include_moon is True
    assert policy.inner_mode == "angles_only"


def test_resolve_policy_merges_profile_and_overrides() -> None:
    profile = MappingProxyType(
        {"feature_flags": {"ingresses": {"enabled": True, "inner_mode": "always"}}}
    )

    derived = _resolve_policy(include_moon=None, inner_mode=None, profile=profile)
    assert derived.enabled is True
    assert derived.include_moon is False
    assert derived.inner_mode == "always"

    overridden = _resolve_policy(include_moon=True, inner_mode="angles_only", profile=profile)
    assert overridden.include_moon is True
    assert overridden.inner_mode == "angles_only"


def test_default_bodies_include_inners_and_moon() -> None:
    policy = _IngressPolicy(enabled=True, include_moon=True, inner_mode="always")

    bodies = _default_bodies(policy)

    assert bodies[:4] == ("sun", "mercury", "venus", "moon")
    assert "saturn" in bodies and len(bodies) == len(set(bodies))


def test_find_sign_ingresses_obeys_profile_flags(detector_stubs) -> None:
    detector_stubs.set_linear("sun", slope=40.0)
    detector_stubs.set_linear("moon", slope=90.0)
    detector_stubs.set_linear("mercury", slope=60.0)
    detector_stubs.set_linear("venus", slope=45.0)

    profile = {
        "feature_flags": {
            "ingresses": {"enabled": True, "include_moon": True, "inner_mode": "always"}
        }
    }

    start = detector_stubs.origin
    end = start + 2.0

    events = find_sign_ingresses(start, end, profile=profile, step_hours=6.0)
    bodies = {event.body.lower() for event in events}

    assert {"sun", "moon", "mercury", "venus"}.issubset(bodies)

    disabled_profile = {"feature_flags": {"ingresses": {"enabled": False}}}
    assert find_sign_ingresses(start, end, profile=disabled_profile) == []

    with pytest.raises(ValueError):
        find_sign_ingresses(start, start + 1.0, step_hours=0.0)


def test_find_house_ingresses_validates_inputs(detector_stubs, monkeypatch: pytest.MonkeyPatch) -> None:
    detector_stubs.set_linear("sun", slope=30.0)
    detector_stubs.set_linear("moon", slope=75.0)

    cusps = [index * 30.0 for index in range(12)]

    with pytest.raises(ValueError):
        start = detector_stubs.origin
        find_house_ingresses(start, start + 1.0, house_cusps=cusps[:10])

    profile = {"feature_flags": {"ingresses": {"include_moon": True}}}
    start = detector_stubs.origin
    events = find_house_ingresses(
        start,
        start + 1.0,
        house_cusps=cusps,
        profile=profile,
        step_minutes=90.0,
    )
    assert any(event.body.lower() == "moon" for event in events)

    monkeypatch.setattr(ingresses, "_HAS_SWE", False)
    with pytest.raises(RuntimeError):
        find_house_ingresses(start, start + 1.0, house_cusps=cusps)
