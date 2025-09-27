from datetime import datetime, timezone, timedelta

from astroengine.core.scan_plus.ranking import (
    EventPoint,
    daily_composite,
    monthly_composite,
    severity,
    taper_by_orb,
)

PROFILE = {"weights": {"square": 1.2, "trine": 0.8, "conjunction": 1.0}}


def test_taper_monotonic_and_bounds():
    assert taper_by_orb(0.0, 6.0) == 1.0
    assert 0.0 < taper_by_orb(3.0, 6.0) < 1.0
    assert taper_by_orb(6.0, 6.0) == 0.0


def test_severity_uses_profile_weights():
    # Exact square should use weight 1.2 at orb 0, limit 6
    s = severity("square", 0.0, 6.0, PROFILE)
    assert 1.19 <= s <= 1.20


def test_severity_tapers_with_orb():
    s0 = severity("trine", 0.0, 6.0, PROFILE)
    s3 = severity("trine", 3.0, 6.0, PROFILE)
    s6 = severity("trine", 6.0, 6.0, PROFILE)
    assert s0 > s3 > s6 >= 0.0


def test_daily_and_monthly_composites():
    base = datetime(2024, 1, 30, 12, 0, tzinfo=timezone.utc)
    events = [
        EventPoint(base + timedelta(hours=1), 1.0),
        EventPoint(base + timedelta(hours=5), 0.5),
        EventPoint(base + timedelta(days=1, hours=3), 2.0),  # next day
        EventPoint(base + timedelta(days=2, hours=2), 1.5),  # next next day (Feb)
    ]
    daily = daily_composite(events)
    assert list(daily.keys()) == ["2024-01-30", "2024-01-31", "2024-02-01"]
    assert abs(daily["2024-01-30"] - 0.75) < 1e-6

    monthly = monthly_composite(daily)
    assert set(monthly.keys()) == {"2024-01", "2024-02"}
    # Jan average of two days: (0.75 + 2.0)/2 = 1.375
    assert abs(monthly["2024-01"] - 1.375) < 1e-6
