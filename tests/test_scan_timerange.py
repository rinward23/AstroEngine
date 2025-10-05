from datetime import datetime, timedelta, timezone

import pytest

from astroengine.core.aspects_plus.scan import (
    AspectSpec,
    TimeWindow,
    scan_pair_time_range,
    scan_time_range,
)


class LinearEphemeris:
    """Synthetic linear-motion ephemeris for testing."""

    def __init__(
        self,
        t0: datetime,
        base: dict[str, float],
        rates_deg_per_day: dict[str, float],
    ) -> None:
        self.t0 = t0
        self.base = base
        self.rates = rates_deg_per_day

    def __call__(self, ts: datetime):
        dt_days = (ts - self.t0).total_seconds() / 86400.0
        out: dict[str, float] = {}
        for name, lon0 in self.base.items():
            out[name] = (lon0 + self.rates.get(name, 0.0) * dt_days) % 360.0
        return out


POLICY = {"per_object": {}, "per_aspect": {"sextile": 3.0}, "adaptive_rules": {}}


def test_find_single_sextile_with_bisection():
    t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    eph = LinearEphemeris(
        t0,
        base={"Mars": 10.0, "Venus": 0.0},
        rates_deg_per_day={"Mars": 0.2, "Venus": 1.0},
    )
    win = TimeWindow(start=t0, end=t0 + timedelta(days=100))

    hits = scan_pair_time_range(
        "Mars",
        "Venus",
        win,
        eph,
        [AspectSpec(name="sextile", angle=60.0)],
        POLICY,
        step_minutes=720,
    )
    assert hits

    h0 = hits[0]
    # Analytic solution: |10 - 0.8 t| = 60 -> t = 87.5 days (post-conjunction branch)
    expected = t0 + timedelta(days=87.5)
    assert abs((h0.exact_time - expected).total_seconds()) <= 30
    assert h0.orb <= 1e-3


def test_timewindow_requires_timezone():
    t0 = datetime(2025, 1, 1)
    with pytest.raises(ValueError, match="timezone-aware"):
        TimeWindow(start=t0, end=t0 + timedelta(days=1))


def test_multi_pair_scan_wrapper():
    t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    eph = LinearEphemeris(
        t0,
        base={"Mars": 10.0, "Venus": 0.0, "Sun": 0.0},
        rates_deg_per_day={"Mars": 0.2, "Venus": 1.0, "Sun": 0.9856},
    )
    win = TimeWindow(start=t0, end=t0 + timedelta(days=30))

    hits = scan_time_range(
        objects=["Sun", "Mars", "Venus"],
        window=win,
        position_provider=eph,
        aspects=["sextile"],
        harmonics=[],
        orb_policy=POLICY,
        step_minutes=360,
    )

    assert hits == sorted(hits, key=lambda h: h.exact_time)


def test_scan_time_range_includes_antiscia_hits():
    t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    eph = LinearEphemeris(
        t0,
        base={"Mars": 10.0, "Venus": 100.0},
        rates_deg_per_day={"Mars": 0.5, "Venus": 1.2},
    )
    win = TimeWindow(start=t0, end=t0 + timedelta(days=60))

    hits = scan_time_range(
        objects=["Mars", "Venus"],
        window=win,
        position_provider=eph,
        aspects=["conjunction"],
        harmonics=[],
        orb_policy=POLICY,
        step_minutes=720,
        include_antiscia=True,
        antiscia_orb=1.0,
    )

    mirror_hits = [
        h for h in hits if (getattr(h, "meta", {}) or {}).get("aspect") in {"antiscia", "contra_antiscia"}
    ]
    assert mirror_hits, "expected antiscia hits when feature enabled"
    assert all((hit.meta or {}).get("kind") == "mirror" for hit in mirror_hits)
