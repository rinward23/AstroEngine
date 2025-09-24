from datetime import UTC, datetime

import pytest

try:  # pragma: no cover - exercised via runtime availability
    import swisseph as swe
except Exception:  # pragma: no cover - fallback when pyswisseph missing
    swe = None  # type: ignore[assignment]

from astroengine.core.angles import DeltaLambdaTracker
from astroengine.core.time import to_tt
from astroengine.ephemeris import EphemerisAdapter, EphemerisConfig, ObserverLocation


def test_adapter_memoizes_samples() -> None:
    adapter = EphemerisAdapter()
    moment = datetime(2024, 1, 1, tzinfo=UTC)
    first = adapter.sample(0, moment)
    second = adapter.sample(0, moment)
    assert first is second


def test_adapter_classify_motion_applying() -> None:
    adapter = EphemerisAdapter()
    tracker = DeltaLambdaTracker()
    reference_longitude = 240.9623186447056
    sample = adapter.sample(4, datetime(2025, 11, 5, 12, tzinfo=UTC))
    motion = adapter.classify_motion(tracker, sample, reference_longitude, 0.0)
    assert motion.state in {"applying", "separating"}


def test_topocentric_longitude_delta_within_bounds() -> None:
    moment = datetime(2025, 3, 20, 12, tzinfo=UTC)
    geocentric = EphemerisAdapter().sample(1, moment)
    observer = ObserverLocation(latitude_deg=40.7128, longitude_deg=-74.0060, elevation_m=15.0)
    topo_adapter = EphemerisAdapter(EphemerisConfig(topocentric=True, observer=observer))
    topocentric = topo_adapter.sample(1, moment)
    lon_delta = abs(topocentric.longitude - geocentric.longitude)
    lat_delta = abs(topocentric.latitude - geocentric.latitude)
    assert 0.0 < lon_delta < 1.0
    assert lat_delta < 1.0
    assert abs(topocentric.declination - geocentric.declination) < 1.0


@pytest.mark.skipif(swe is None, reason="pyswisseph unavailable")
def test_sidereal_mode_configures_swiss_backend() -> None:
    moment = datetime(2000, 4, 13, 11, 52, 10, 808741, tzinfo=UTC)
    adapter = EphemerisAdapter(
        EphemerisConfig(sidereal=True, sidereal_mode="lahiri"),
    )
    sample = adapter.sample(swe.SUN, moment)
    conv = to_tt(moment)
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0.0, 0.0)
    values, _ = swe.calc_ut(conv.jd_utc, swe.SUN, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
    expected = float(values[0]) % 360.0
    assert abs(sample.longitude - expected) < 1e-6
