from __future__ import annotations

from datetime import UTC, datetime

import pytest

from astroengine.engine.ephe_runtime import init_ephe
from core.rel_plus import (
    BirthEvent,
    DavisonResult,
    circular_midpoint,
    composite_houses,
    davison_houses,
    geodesic_midpoint,
    midpoint_time,
)

pytestmark = pytest.mark.swiss


def _julian_day(dt: datetime, swe_module) -> float:
    ts = dt.astimezone(UTC)
    frac = (
        ts.hour
        + ts.minute / 60.0
        + ts.second / 3600.0
        + ts.microsecond / 3_600_000_000.0
    )
    init_ephe()
    return swe_module.julday(ts.year, ts.month, ts.day, frac)


def _obliquity(jd_ut: float, swe_module) -> float:
    if hasattr(swe_module, "obl_ecl"):
        return swe_module.obl_ecl(jd_ut)[0]  # type: ignore[call-arg]
    base_flag = init_ephe()
    values, _ = swe_module.calc_ut(jd_ut, swe_module.ECL_NUT, base_flag)
    return values[0]


def test_davison_houses_matches_swe(swiss_ephemeris):
    dt = datetime(2024, 3, 21, 12, 30, tzinfo=UTC)
    result = DavisonResult(mid_when=dt, mid_lat=10.0, mid_lon=20.0, positions={})
    houses = davison_houses(result, "O")

    jd = _julian_day(dt, swiss_ephemeris)
    cusps_ref, ascmc_ref = swiss_ephemeris.houses_ex(
        jd, result.mid_lat, result.mid_lon, b"O"
    )

    assert pytest.approx(houses.ascendant, rel=0, abs=1e-6) == (ascmc_ref[0] % 360.0)
    assert pytest.approx(houses.midheaven, rel=0, abs=1e-6) == (ascmc_ref[1] % 360.0)
    for idx, cusp in enumerate(houses.cusps):
        assert pytest.approx(cusp, rel=0, abs=1e-6) == (cusps_ref[idx] % 360.0)


def test_composite_houses_armc_midpoint_matches_reference(swiss_ephemeris):
    event_a = BirthEvent(when=datetime(1990, 1, 1, 5, 15, tzinfo=UTC), lat=40.0, lon=-73.0)
    event_b = BirthEvent(when=datetime(1992, 6, 10, 18, 45, tzinfo=UTC), lat=34.0, lon=-118.0)
    houses = composite_houses(event_a, event_b, "O")

    jd_a = _julian_day(event_a.when, swiss_ephemeris)
    jd_b = _julian_day(event_b.when, swiss_ephemeris)
    lst_a = (swiss_ephemeris.sidtime(jd_a) * 15.0 + event_a.lon) % 360.0
    lst_b = (swiss_ephemeris.sidtime(jd_b) * 15.0 + event_b.lon) % 360.0
    armc = circular_midpoint(lst_a, lst_b)
    mid_lat, _ = geodesic_midpoint(event_a.lat, event_a.lon, event_b.lat, event_b.lon)
    jd_mid = _julian_day(midpoint_time(event_a.when, event_b.when), swiss_ephemeris)
    eps = _obliquity(jd_mid, swiss_ephemeris)
    cusps_ref, ascmc_ref = swiss_ephemeris.houses_armc(armc, mid_lat, eps, b"O")

    assert pytest.approx(houses.ascendant, rel=0, abs=1e-6) == (ascmc_ref[0] % 360.0)
    assert pytest.approx(houses.midheaven, rel=0, abs=1e-6) == (ascmc_ref[1] % 360.0)
    for idx, cusp in enumerate(houses.cusps):
        assert pytest.approx(cusp, rel=0, abs=1e-6) == (cusps_ref[idx] % 360.0)


def test_composite_houses_polar_fallback():
    event_a = BirthEvent(when=datetime(2000, 1, 1, 0, 0, tzinfo=UTC), lat=68.0, lon=0.0)
    event_b = BirthEvent(when=datetime(2000, 7, 1, 0, 0, tzinfo=UTC), lat=69.0, lon=30.0)
    houses = composite_houses(event_a, event_b, "P")
    assert houses.system_requested == "P"
    assert houses.system_used in {"K", "O", "R", "W"}
    assert houses.fallback_reason is not None
    payload = houses.to_payload()
    assert payload["house_system_used"] == houses.system_used
    assert len(payload["cusps"]) == 12
