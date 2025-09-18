from __future__ import annotations

import pytest

from astroengine.api import TransitEvent
from astroengine.engine import attach_domain_fields, build_transit_event


def test_build_transit_event_applies_domain_multiplier():
    ctx = {
        "sign_index": 11,  # Pisces
        "planet_key": "neptune",
        "house_index": 12,
        "severity": 2.0,
        "domain_profile": "vca_spirit_plus",
    }
    event = build_transit_event(ctx, emit_domains=True)
    assert event.elements == ["WATER"]
    assert event.domain_profile == "vca_spirit_plus"
    # Neptune (SPIRIT) in 12th (SPIRIT) should favour SPIRIT multiplier 1.25
    assert event.severity == pytest.approx(2.5)


def test_attach_domain_fields_noop_when_missing_keys():
    event = TransitEvent(severity=1.0)
    attach_domain_fields(event, {})
    assert event.elements == []
    assert event.domains == {}
    assert event.domain_profile is None


def test_build_transit_event_handles_invalid_severity():
    ctx = {
        "sign_index": 0,
        "planet_key": "sun",
        "severity": "not-a-number",
    }
    event = build_transit_event(ctx, emit_domains=False)
    assert event.severity is None
