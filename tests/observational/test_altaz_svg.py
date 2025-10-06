from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

pytest.importorskip(
    "PIL",
    reason="Pillow not installed; install extras with `pip install -e .[ui,reports]`.",
)

from astroengine.engine.observational import render_altaz_diagram
from astroengine.ephemeris import EphemerisAdapter, EphemerisConfig, ObserverLocation

swe = pytest.importorskip("swisseph")


def test_altaz_diagram_output() -> None:
    adapter = EphemerisAdapter(EphemerisConfig())
    observer = ObserverLocation(latitude_deg=40.7128, longitude_deg=-74.0060, elevation_m=10.0)
    start = datetime(2024, 7, 1, 0, 0, tzinfo=UTC)
    end = start + timedelta(hours=12)

    diagram = render_altaz_diagram(
        adapter,
        swe().MARS,
        start,
        end,
        observer,
        refraction=True,
    )

    assert "Altitude vs Time" in diagram.svg
    assert "polyline" in diagram.svg
    assert diagram.metadata["count"] > 0
    rise_meta = diagram.metadata["rise"]
    if rise_meta is not None:
        assert rise_meta.endswith("Z") or rise_meta.endswith("+00:00")
    assert diagram.png is not None and len(diagram.png) > 1000
