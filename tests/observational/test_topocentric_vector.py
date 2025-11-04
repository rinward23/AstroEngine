from __future__ import annotations

from datetime import UTC, datetime

import pytest

pytest.importorskip(
    "PIL",
    reason="Pillow not installed; install extras with `pip install -e .[ui,reports]`.",
)

try:
    from astroengine.engine.observational import topocentric_equatorial
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

MOON_CODE = resolve_body_code("Moon").code


def _adapter(topocentric: bool, observer: ObserverLocation | None) -> EphemerisAdapter:
    config = EphemerisConfig(topocentric=topocentric, observer=observer)
    return EphemerisAdapter(config)


def _angular_delta(a: float, b: float) -> float:
    delta = (a - b + 180.0) % 360.0 - 180.0
    return abs(delta)


def test_topocentric_matches_swiss_ephemeris() -> None:
    if EphemerisAdapter is None or ObserverLocation is None:
        pytest.skip(f"EphemerisAdapter unavailable: {_EPHEMERIS_IMPORT_ERROR}")
    observer = ObserverLocation(latitude_deg=51.4779, longitude_deg=-0.0015, elevation_m=46.0)
    moment = datetime(2024, 3, 20, 5, 30, tzinfo=UTC)
    body = MOON_CODE

    geo_adapter = _adapter(False, None)
    topo_equ = topocentric_equatorial(geo_adapter, body, moment, observer)

    swe_adapter = _adapter(True, observer)
    swe_sample = swe_adapter.sample(body, moment)

    assert _angular_delta(topo_equ.right_ascension_deg, swe_sample.right_ascension) < 0.005
    assert abs(topo_equ.declination_deg - swe_sample.declination) < 0.005
    assert abs(topo_equ.distance_au - swe_sample.distance) < 5e-6


