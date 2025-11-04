from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

pytest.importorskip(
    "PIL",
    reason="Pillow not installed; install extras with `pip install -e .[ui,reports]`.",
)

try:
    from astroengine.engine.observational import render_altaz_diagram
    from astroengine.engine.returns._codes import resolve_body_code
    from astroengine.ephemeris import EphemerisConfig
    from astroengine.ephemeris import EphemerisAdapter, ObserverLocation
except ImportError as exc:  # pragma: no cover - optional dependency gating
    pytest.skip(
        f"Observational ephemeris support unavailable: {exc}", allow_module_level=True
    )
    EphemerisAdapter = None  # type: ignore[assignment]
    ObserverLocation = None  # type: ignore[assignment]
    resolve_body_code = lambda name: None  # type: ignore[assignment]
    _EPHEMERIS_IMPORT_ERROR = exc
else:
    _EPHEMERIS_IMPORT_ERROR = None

pytestmark = pytest.mark.swiss

MARS_CODE = resolve_body_code("Mars").code


def test_altaz_diagram_output() -> None:
    if EphemerisAdapter is None or ObserverLocation is None:
        pytest.skip(f"EphemerisAdapter unavailable: {_EPHEMERIS_IMPORT_ERROR}")
    adapter = EphemerisAdapter(EphemerisConfig())
    observer = ObserverLocation(latitude_deg=40.7128, longitude_deg=-74.0060, elevation_m=10.0)
    start = datetime(2024, 7, 1, 0, 0, tzinfo=UTC)
    end = start + timedelta(hours=12)

    diagram = render_altaz_diagram(
        adapter,
        MARS_CODE,
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
