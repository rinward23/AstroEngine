from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from astroengine.core.aspects_plus.search import (
    AspectSearch,
    TimeRange,
    search_pair,
    search_time_range,
)


class LinearEphemeris:
    """Synthetic linear-motion ephemeris for testing search helpers."""

    def __init__(
        self,
        t0: datetime,
        base: dict[str, float],
        rates_deg_per_day: dict[str, float],
    ) -> None:
        self.t0 = t0
        self.base = base
        self.rates = rates_deg_per_day

    def __call__(self, ts: datetime) -> dict[str, float]:
        dt_days = (ts - self.t0).total_seconds() / 86400.0
        return {
            name: (lon0 + self.rates.get(name, 0.0) * dt_days) % 360.0
            for name, lon0 in self.base.items()
        }


POLICY = {"per_object": {}, "per_aspect": {"sextile": 3.0}}


def test_search_pair_detects_sextile_event() -> None:
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    eph = LinearEphemeris(
        t0,
        base={"Mars": 10.0, "Venus": 0.0},
        rates_deg_per_day={"Mars": 0.2, "Venus": 1.0},
    )
    timerange = TimeRange(start=t0, end=t0 + timedelta(days=120), step_minutes=720)

    hits = search_pair(
        position_provider=eph,
        body_a="Mars",
        body_b="Venus",
        timerange=timerange,
        aspects=("sextile",),
        orb_policy=POLICY,
    )

    assert hits, "expected sextile hit within window"
    hit = hits[0]
    expected = t0 + timedelta(days=87.5)
    assert abs((hit.exact_time - expected).total_seconds()) <= 30
    assert hit.orb <= 1e-3


def test_search_time_range_includes_harmonics() -> None:
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    eph = LinearEphemeris(
        t0,
        base={"Mars": 10.0, "Venus": 0.0},
        rates_deg_per_day={"Mars": 0.2, "Venus": 1.0},
    )
    timerange = TimeRange(start=t0, end=t0 + timedelta(days=150), step_minutes=720)
    config = AspectSearch(
        objects=("Mars", "Venus"),
        aspects=("conjunction",),
        harmonics=(5,),
        orb_policy=POLICY,
        pairs=(("Mars", "Venus"),),
    )

    hits = search_time_range(position_provider=eph, timerange=timerange, config=config)

    harmonic_hits = [
        h for h in hits if (getattr(h, "meta", {}) or {}).get("harmonic") == 5
    ]
    assert harmonic_hits, "expected harmonic-generated aspects in results"
    assert any(abs(hit.aspect_angle - 72.0) <= 1e-3 for hit in harmonic_hits)


def test_search_time_range_requires_objects() -> None:
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    eph = LinearEphemeris(t0, base={"Sun": 0.0}, rates_deg_per_day={"Sun": 1.0})
    timerange = TimeRange(start=t0, end=t0 + timedelta(days=10))
    config = AspectSearch(objects=(), aspects=("conjunction",))

    with pytest.raises(ValueError, match="config.objects"):
        search_time_range(position_provider=eph, timerange=timerange, config=config)

