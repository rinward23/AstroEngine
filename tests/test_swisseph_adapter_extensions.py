from __future__ import annotations

from datetime import UTC, datetime

import pytest

from astroengine.ephemeris import SwissEphemerisAdapter

swe = pytest.importorskip("swisseph")


def test_julian_day_roundtrip_precision() -> None:
    adapter = SwissEphemerisAdapter()
    moment = datetime(2024, 3, 1, 12, 34, 56, 789123, tzinfo=UTC)
    jd = adapter.julian_day(moment)
    restored = adapter.from_julian_day(jd)
    delta = abs((restored - moment).total_seconds())
    assert delta < 5e-4


def test_rise_transit_alignment_with_swisseph() -> None:
    adapter = SwissEphemerisAdapter()
    jd = swe().julday(2024, 6, 1, 0.0)
    latitude = 40.7128
    longitude = -74.0060
    ours = adapter.rise_transit(
        jd,
        swe().SUN,
        latitude=latitude,
        longitude=longitude,
        event="rise",
        flags=adapter._calc_flags,  # noqa: SLF001 - intentional test access
        body_name="Sun",
    )
    expected_status, expected_tret = swe().rise_trans(
        jd,
        swe().SUN,
        swe().CALC_RISE,
        (longitude, latitude, 0.0),
        0.0,
        0.0,
        adapter._calc_flags,  # noqa: SLF001 - intentional test access
    )
    assert ours.status == expected_status
    assert ours.julian_day is not None
    assert abs(ours.julian_day - expected_tret[0]) < 1e-6


def test_fixed_star_matches_native_computation() -> None:
    adapter = SwissEphemerisAdapter()
    jd = swe().julday(2024, 1, 1, 0.0)
    star = adapter.fixed_star("Aldebaran", jd, flags=adapter._calc_flags)
    values, name, retflags = swe().fixstar_ut("Aldebaran", jd, adapter._calc_flags)
    assert star.name.strip().lower() == name.strip().lower()
    assert abs(star.longitude - values[0]) < 1e-6
    assert abs(star.latitude - values[1]) < 1e-6
    assert star.flags == retflags


def test_compute_bodies_many_matches_single_calls() -> None:
    adapter = SwissEphemerisAdapter()
    jd = swe().julday(2024, 2, 1, 0.0)
    bodies = {
        "Sun": int(swe().SUN),
        "Moon": int(swe().MOON),
        "Mars": int(swe().MARS),
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


def test_ayanamsa_variants() -> None:
    adapter = SwissEphemerisAdapter(zodiac="sidereal", ayanamsa="lahiri")
    jd = swe().julday(2024, 5, 10, 0.0)
    ut_value = adapter.ayanamsa(jd)
    expected_ut = swe().get_ayanamsa_ut(jd)
    assert abs(ut_value - expected_ut) < 1e-8

    true_value = adapter.ayanamsa(jd, true_longitude=True)
    expected_true = swe().get_ayanamsa(jd + swe().deltat(jd))
    assert abs(true_value - expected_true) < 1e-8

    details = adapter.ayanamsa_details(jd)
    flags, expected = swe().get_ayanamsa_ex_ut(jd, int(swe().SIDM_LAHIRI))
    assert details["mode"] == int(swe().SIDM_LAHIRI)
    assert details["flags"] == flags
    assert abs(details["value"] - expected) < 1e-8


def test_planet_name_resolution() -> None:
    name = SwissEphemerisAdapter.planet_name(int(swe().MARS))
    assert "mars" in name.lower()
