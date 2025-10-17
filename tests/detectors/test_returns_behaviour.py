"""Tests for solar and lunar return detectors with fake ephemeris data."""

from __future__ import annotations

from datetime import UTC
from types import SimpleNamespace

import pytest

import astroengine.detectors.returns as returns


def _fake_swe() -> SimpleNamespace:
    return SimpleNamespace(SUN=0, MOON=1)


def test_scan_returns_parses_iso_and_applies_step(
    detector_stubs, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(returns, "get_swisseph", _fake_swe)
    detector_stubs.set_linear("sun", slope=180.0)
    detector_stubs.adapter.body_position_calls.clear()
    detector_stubs.adapter.julian_calls.clear()

    events = returns.scan_returns(
        natal_ts="1970-01-01T00:00:00",
        start_ts="1970-01-01T00:00:00Z",
        end_ts="1970-01-05T00:00:00",
        kind="solar",
        step_days=2.0,
    )

    assert events  # deterministic stub still finds at least one event
    assert all(call.tzinfo is UTC for call in detector_stubs.adapter.julian_calls)

    sampled = sorted({round(jd, 6) for _, jd in detector_stubs.adapter.body_position_calls})
    assert sampled[1] == pytest.approx(sampled[0] + 2.0)


def test_solar_lunar_returns_rejects_unsupported_kind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(returns, "get_swisseph", _fake_swe)

    base = 2451545.0
    with pytest.raises(ValueError):
        returns.solar_lunar_returns(base, base, base + 1.0, kind="martian")


def test_solar_returns_deduplicate_repeated_roots(
    detector_stubs, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(returns, "get_swisseph", _fake_swe)
    detector_stubs.set_linear("sun", slope=180.0)

    base = detector_stubs.origin
    monkeypatch.setattr(returns, "solve_zero_crossing", lambda *args, **kwargs: base)

    events = returns.solar_lunar_returns(
        base,
        base,
        base + 2.0,
        kind="solar",
        step_days=1.0,
        adapter=detector_stubs.adapter,
    )

    base_events = [event for event in events if event.jd == base]
    assert len(base_events) == 1
    assert len(events) >= 1
    assert all(event.body == "Sun" for event in events)


def test_scan_returns_returns_empty_for_reversed_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(returns, "get_swisseph", _fake_swe)

    assert (
        returns.scan_returns(
            natal_ts="1970-01-02T00:00:00Z",
            start_ts="1970-01-05T00:00:00Z",
            end_ts="1970-01-04T00:00:00Z",
            kind="solar",
        )
        == []
    )
