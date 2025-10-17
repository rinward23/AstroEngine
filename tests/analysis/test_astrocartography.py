"""Tests for astrocartography helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import astroengine.analysis.astrocartography as astrocartography


class DummySweModule:
    """Minimal Swiss Ephemeris stand-in for astrocartography tests."""

    SUN = 42

    def sidtime(self, jd_ut: float) -> float:  # pragma: no cover - deterministic stub
        return 0.0


class DummyAdapter:
    """Adapter stub returning deterministic equatorial coordinates."""

    def julian_day(self, moment: datetime) -> float:
        return 2451545.0

    def body_equatorial(self, jd_ut: float, code: int):
        return SimpleNamespace(right_ascension=180.0, declination=0.0)


def test_compute_lines_reflects_swisseph_availability(monkeypatch: pytest.MonkeyPatch) -> None:
    """`compute_astrocartography_lines` should honour patched Swiss Ephemeris state."""

    moment = datetime(2024, 1, 1, tzinfo=timezone.utc)
    adapter = DummyAdapter()

    monkeypatch.setattr(astrocartography, "has_swe", lambda: False)

    with pytest.raises(RuntimeError):
        astrocartography.compute_astrocartography_lines(
            moment,
            bodies=("sun",),
            adapter=adapter,
            line_types=("MC",),
        )

    dummy_swe = DummySweModule()
    monkeypatch.setattr(astrocartography, "has_swe", lambda: True)
    monkeypatch.setattr(astrocartography, "swe", lambda: dummy_swe)

    result = astrocartography.compute_astrocartography_lines(
        moment,
        bodies=("sun",),
        adapter=adapter,
        line_types=("MC",),
    )

    assert len(result.lines) == 1
    line = result.lines[0]
    assert line.body == "sun"
    assert line.kind == "MC"
    assert line.coordinates
