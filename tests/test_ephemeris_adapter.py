from datetime import UTC, datetime

from astroengine.core.angles import DeltaLambdaTracker
from astroengine.ephemeris import EphemerisAdapter


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
