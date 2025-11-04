from __future__ import annotations

from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.swiss

try:
    from astroengine.engine.ephe_runtime import init_ephe
    from astroengine.ephemeris import SwissEphemerisAdapter
except ImportError as exc:  # pragma: no cover - optional dependency gating
    pytest.skip(
        f"Swiss Ephemeris adapter unavailable: {exc}", allow_module_level=True
    )


def test_julian_day_roundtrip_precision() -> None:
    adapter = SwissEphemerisAdapter()
    moment = datetime(2024, 3, 1, 12, 34, 56, 789123, tzinfo=UTC)
    jd = adapter.julian_day(moment)
    restored = adapter.from_julian_day(jd)
    delta = abs((restored - moment).total_seconds())
    assert delta < 5e-4


def test_rise_transit_alignment_with_swisseph(swiss_ephemeris) -> None:
    adapter = SwissEphemerisAdapter()
    init_ephe()
    jd = swiss_ephemeris.julday(2024, 6, 1, 0.0)
    latitude = 40.7128
    longitude = -74.0060
    ours = adapter.rise_transit(
        jd,
        swiss_ephemeris.SUN,
        latitude=latitude,
        longitude=longitude,
        event="rise",
        flags=adapter._calc_flags,  # noqa: SLF001 - intentional test access
        body_name="Sun",
    )
    expected_status, expected_tret = swiss_ephemeris.rise_trans(
        jd,
        swiss_ephemeris.SUN,
        swiss_ephemeris.CALC_RISE,
        (longitude, latitude, 0.0),
        0.0,
        0.0,
        adapter._calc_flags,  # noqa: SLF001 - intentional test access
    )
    assert ours.status == expected_status
    assert ours.julian_day is not None
    assert abs(ours.julian_day - expected_tret[0]) < 1e-6


def test_fixed_star_matches_native_computation(swiss_ephemeris) -> None:
    adapter = SwissEphemerisAdapter()
    init_ephe()
    jd = swiss_ephemeris.julday(2024, 1, 1, 0.0)
    star = adapter.fixed_star("Aldebaran", jd, flags=adapter._calc_flags)
    values, name, retflags = swiss_ephemeris.fixstar_ut("Aldebaran", jd, adapter._calc_flags)
    assert star.name.strip().lower() == name.strip().lower()
    assert abs(star.longitude - values[0]) < 1e-6
    assert abs(star.latitude - values[1]) < 1e-6
    assert star.flags == retflags


def test_compute_bodies_many_matches_single_calls(swiss_ephemeris) -> None:
    adapter = SwissEphemerisAdapter()
    init_ephe()
    jd = swiss_ephemeris.julday(2024, 2, 1, 0.0)
    bodies = {
        "Sun": int(swiss_ephemeris.SUN),
        "Moon": int(swiss_ephemeris.MOON),
        "Mars": int(swiss_ephemeris.MARS),
    }
    aggregated = adapter.compute_bodies_many(jd, bodies)
    assert set(aggregated) == set(bodies)
    for name, code in bodies.items():
        single = adapter.body_position(jd, int(code), body_name=name)
        combined = aggregated[name]
        assert combined.body == single.body
        assert combined.julian_day == pytest.approx(single.julian_day)
        assert combined.longitude == pytest.approx(single.longitude)
        assert combined.latitude == pytest.approx(single.latitude)
        assert combined.distance_au == pytest.approx(single.distance_au)
        assert combined.speed_longitude == pytest.approx(single.speed_longitude)
        assert combined.speed_latitude == pytest.approx(single.speed_latitude)
        assert combined.speed_distance == pytest.approx(single.speed_distance)
        assert combined.declination == pytest.approx(single.declination)
        assert combined.speed_declination == pytest.approx(
            single.speed_declination
        )


def test_ayanamsa_variants(swiss_ephemeris) -> None:
    adapter = SwissEphemerisAdapter(zodiac="sidereal", ayanamsa="lahiri")
    init_ephe()
    jd = swiss_ephemeris.julday(2024, 5, 10, 0.0)
    ut_value = adapter.ayanamsa(jd)
    expected_ut = swiss_ephemeris.get_ayanamsa_ut(jd)
    assert abs(ut_value - expected_ut) < 1e-8

    true_value = adapter.ayanamsa(jd, true_longitude=True)
    expected_true = swiss_ephemeris.get_ayanamsa(jd + swiss_ephemeris.deltat(jd))
    assert abs(true_value - expected_true) < 1e-8

    details = adapter.ayanamsa_details(jd)
    flags, expected = swiss_ephemeris.get_ayanamsa_ex_ut(
        jd, int(swiss_ephemeris.SIDM_LAHIRI)
    )
    assert details["mode"] == int(swiss_ephemeris.SIDM_LAHIRI)
    assert details["flags"] == flags
    assert abs(details["value"] - expected) < 1e-8


def test_planet_name_resolution(swiss_ephemeris) -> None:
    name = SwissEphemerisAdapter.planet_name(int(swiss_ephemeris.MARS))
    assert "mars" in name.lower()
