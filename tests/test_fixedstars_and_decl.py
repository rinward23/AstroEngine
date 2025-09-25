# >>> AUTO-GEN BEGIN: AE Fixed Stars & Decl Tests v1.0
import datetime as dt
import importlib
import math

import pytest


@pytest.mark.skipif(
    importlib.util.find_spec("skyfield") is None
    or importlib.util.find_spec("jplephem") is None,
    reason="skyfield/jplephem missing",
)
def test_skyfield_star_regulus_lon_lat_range():
    from astroengine.fixedstars.skyfield_stars import star_lonlat

    iso = dt.datetime(2024, 6, 1, 0, 0, 0).isoformat() + "Z"
    try:
        lon, lat = star_lonlat("Regulus", iso)
    except FileNotFoundError:
        pytest.skip("no local JPL kernel found")
    assert 0.0 <= lon < 360.0
    assert -90.0 <= lat <= 90.0


def test_declination_utils():
    from astroengine.astro.declination import (
        antiscia_lon,
        available_antiscia_axes,
        contra_antiscia_lon,
        ecl_to_dec,
        is_contraparallel,
        is_parallel,
    )

    # Equinox/solstice sanity
    assert abs(ecl_to_dec(0.0)) < 1e-6  # Aries 0 dec ~ 0
    assert abs(ecl_to_dec(180.0)) < 1e-6
    dec_cancer = ecl_to_dec(90.0)
    dec_cap = ecl_to_dec(270.0)
    assert dec_cancer > 0 and dec_cap < 0
    # Mirrors
    assert math.isclose(antiscia_lon(10.0), 170.0)
    assert math.isclose(contra_antiscia_lon(10.0), 350.0)
    assert math.isclose(antiscia_lon(10.0, axis="aries_libra"), 350.0)
    assert math.isclose(contra_antiscia_lon(10.0, axis="aries_libra"), 170.0)
    assert "cancer_capricorn" in available_antiscia_axes()
    with pytest.raises(ValueError):
        antiscia_lon(10.0, axis="bogus_axis")
    # Parallels
    assert is_parallel(10.0, 10.3, tol_deg=0.5)
    assert is_contraparallel(10.0, -10.3, tol_deg=0.5)


# >>> AUTO-GEN END: AE Fixed Stars & Decl Tests v1.0
