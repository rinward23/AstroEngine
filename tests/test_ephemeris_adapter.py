from datetime import UTC, datetime

from astroengine.core.angles import DeltaLambdaTracker
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
