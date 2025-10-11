from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable

import pytest

pytestmark = pytest.mark.swiss

pytest.importorskip("swisseph", reason="pyswisseph required for provider parity")
pytest.importorskip("skyfield", reason="skyfield required for provider parity")
pytest.importorskip("jplephem", reason="jplephem kernel support required")

_CHARTS_PATH = Path(__file__).resolve().parents[1] / "qa" / "artifacts" / "provider_parity" / "charts.json"
_CHART_FIXTURES = json.loads(_CHARTS_PATH.read_text())

_ARCSECONDS_PER_DEGREE = 3600.0
_LON_TOLERANCE_ARCSEC = _CHART_FIXTURES["tolerances"]["ecliptic_longitude_arcsec"]
_DECL_TOLERANCE_ARCSEC = _CHART_FIXTURES["tolerances"]["declination_arcsec"]
_SPEED_TOLERANCE_DEG_PER_DAY = _CHART_FIXTURES["tolerances"]["speed_deg_per_day"]


def _wrap_angle_diff(a: float, b: float) -> float:
    """Return the absolute wrapped difference in degrees."""

    diff = (a - b + 180.0) % 360.0 - 180.0
    return abs(diff)


@pytest.fixture(scope="session")
def swiss_provider():
    from astroengine.providers.swiss_provider import SwissProvider

    try:
        return SwissProvider()
    except ImportError as exc:  # pragma: no cover - dependency gating
        pytest.skip(f"Swiss provider unavailable: {exc}")


@pytest.fixture(scope="session")
def skyfield_provider():
    from astroengine.providers.skyfield_provider import SkyfieldProvider

    try:
        return SkyfieldProvider()
    except (FileNotFoundError, ImportError) as exc:  # pragma: no cover - kernel gating
        pytest.skip(f"Skyfield provider unavailable: {exc}")


def _chart_ids() -> Iterable[str]:
    return [chart["id"] for chart in _CHART_FIXTURES["charts"]]


@pytest.mark.parametrize("chart", _CHART_FIXTURES["charts"], ids=_chart_ids())
def test_positions_ecliptic_within_tolerance(chart, swiss_provider, skyfield_provider):
    """Batch ecliptic positions stay inside documented parity tolerances."""

    timestamp = chart["timestamp"]
    bodies = chart["bodies"]

    swiss_positions = swiss_provider.positions_ecliptic(timestamp, bodies)
    skyfield_positions = skyfield_provider.positions_ecliptic(timestamp, bodies)

    lon_tol = _LON_TOLERANCE_ARCSEC / _ARCSECONDS_PER_DEGREE
    decl_tol = _DECL_TOLERANCE_ARCSEC / _ARCSECONDS_PER_DEGREE

    for body in bodies:
        swiss_body = swiss_positions[body]
        skyfield_body = skyfield_positions[body]
        assert math.isfinite(swiss_body["lon"])
        assert math.isfinite(skyfield_body["lon"])
        assert _wrap_angle_diff(swiss_body["lon"], skyfield_body["lon"]) <= lon_tol
        assert math.isfinite(swiss_body["decl"])
        assert math.isfinite(skyfield_body["decl"])
        assert abs(swiss_body["decl"] - skyfield_body["decl"]) <= decl_tol


@pytest.mark.parametrize("chart", _CHART_FIXTURES["charts"], ids=_chart_ids())
@pytest.mark.parametrize("body", _CHART_FIXTURES["body_samples"])
def test_canonical_body_positions_align(chart, body, swiss_provider, skyfield_provider):
    """Canonical BodyPosition comparisons respect documented tolerances."""

    timestamp = chart["timestamp"]

    swiss_sample = swiss_provider.position(body, timestamp)
    skyfield_sample = skyfield_provider.position(body, timestamp)

    lon_tol = _LON_TOLERANCE_ARCSEC / _ARCSECONDS_PER_DEGREE
    lat_tol = _DECL_TOLERANCE_ARCSEC / _ARCSECONDS_PER_DEGREE
    decl_tol = _DECL_TOLERANCE_ARCSEC / _ARCSECONDS_PER_DEGREE

    assert _wrap_angle_diff(swiss_sample.lon, skyfield_sample.lon) <= lon_tol
    assert abs(swiss_sample.lat - skyfield_sample.lat) <= lat_tol
    assert abs(swiss_sample.dec - skyfield_sample.dec) <= decl_tol
    assert abs(swiss_sample.speed_lon - skyfield_sample.speed_lon) <= _SPEED_TOLERANCE_DEG_PER_DAY
