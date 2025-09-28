from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.rel_plus import (
    BirthEvent,
    DavisonResult,
    composite_houses,
    davison_houses,
    geodesic_midpoint,
    midpoint_time,
    circular_midpoint,
)

swe = pytest.importorskip("swisseph")


def _julian_day(dt: datetime) -> float:
    ts = dt.astimezone(timezone.utc)
    frac = (
        ts.hour
        + ts.minute / 60.0
        + ts.second / 3600.0
        + ts.microsecond / 3_600_000_000.0
    )
    return swe.julday(ts.year, ts.month, ts.day, frac)


def _obliquity(jd_ut: float) -> float:
    if hasattr(swe, "obl_ecl"):
        return swe.obl_ecl(jd_ut)[0]  # type: ignore[call-arg]
    values, _ = swe.calc_ut(jd_ut, swe.ECL_NUT, swe.FLG_SWIEPH)
    return values[0]


def test_davison_houses_matches_swe():
    dt = datetime(2024, 3, 21, 12, 30, tzinfo=timezone.utc)
    result = DavisonResult(mid_when=dt, mid_lat=10.0, mid_lon=20.0, positions={})
    houses = davison_houses(result, "O")

    jd = _julian_day(dt)
    cusps_ref, ascmc_ref = swe.houses_ex(jd, result.mid_lat, result.mid_lon, b"O")

    assert pytest.approx(houses.ascendant, rel=0, abs=1e-6) == (ascmc_ref[0] % 360.0)
    assert pytest.approx(houses.midheaven, rel=0, abs=1e-6) == (ascmc_ref[1] % 360.0)
    for idx, cusp in enumerate(houses.cusps):
        assert pytest.approx(cusp, rel=0, abs=1e-6) == (cusps_ref[idx] % 360.0)


def test_composite_houses_armc_midpoint_matches_reference():
    event_a = BirthEvent(when=datetime(1990, 1, 1, 5, 15, tzinfo=timezone.utc), lat=40.0, lon=-73.0)
    event_b = BirthEvent(when=datetime(1992, 6, 10, 18, 45, tzinfo=timezone.utc), lat=34.0, lon=-118.0)
    houses = composite_houses(event_a, event_b, "O")

    jd_a = _julian_day(event_a.when)
    jd_b = _julian_day(event_b.when)
    lst_a = (swe.sidtime(jd_a) * 15.0 + event_a.lon) % 360.0
    lst_b = (swe.sidtime(jd_b) * 15.0 + event_b.lon) % 360.0
    armc = circular_midpoint(lst_a, lst_b)
    mid_lat, _ = geodesic_midpoint(event_a.lat, event_a.lon, event_b.lat, event_b.lon)
    jd_mid = _julian_day(midpoint_time(event_a.when, event_b.when))
    eps = _obliquity(jd_mid)
    cusps_ref, ascmc_ref = swe.houses_armc(armc, mid_lat, eps, b"O")

    assert pytest.approx(houses.ascendant, rel=0, abs=1e-6) == (ascmc_ref[0] % 360.0)
    assert pytest.approx(houses.midheaven, rel=0, abs=1e-6) == (ascmc_ref[1] % 360.0)
    for idx, cusp in enumerate(houses.cusps):
        assert pytest.approx(cusp, rel=0, abs=1e-6) == (cusps_ref[idx] % 360.0)


def test_composite_houses_polar_fallback():
    event_a = BirthEvent(when=datetime(2000, 1, 1, 0, 0, tzinfo=timezone.utc), lat=68.0, lon=0.0)
    event_b = BirthEvent(when=datetime(2000, 7, 1, 0, 0, tzinfo=timezone.utc), lat=69.0, lon=30.0)
    houses = composite_houses(event_a, event_b, "P")
    assert houses.system_requested == "P"
    assert houses.system_used in {"K", "O", "R", "W"}
    assert houses.fallback_reason is not None
    payload = houses.to_payload()
    assert payload["house_system_used"] == houses.system_used
    assert len(payload["cusps"]) == 12
