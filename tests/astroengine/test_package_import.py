"""Regression tests for importing :mod:`astroengine`."""

from __future__ import annotations


def test_import_exposes_expected_symbols() -> None:
    import astroengine as ae

    assert ae.ChartConfig is not None
    assert ae.compute_natal_chart is not None
    assert ae.SwissEphemerisAdapter is not None
    assert ae.TransitEngine is not None
    assert ae.NarrativeOverlay is not None
    assert ae.AgentSDK is not None
    # Optional legacy surface should still resolve without raising
    assert hasattr(ae, "LunationEvent")
