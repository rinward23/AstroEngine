# >>> AUTO-GEN BEGIN: AE Provider Tests v1.0
import datetime as dt
import importlib

import pytest


@pytest.mark.skipif(
    importlib.util.find_spec("swisseph") is None, reason="pyswisseph missing"
)
def test_swiss_provider_roundtrip():
    from astroengine.providers.swiss_provider import SwissProvider

    p = SwissProvider()
    now = dt.datetime(2024, 3, 20, 12, 0, 0).isoformat() + "Z"
    res = p.positions_ecliptic(now, ["sun", "moon", "mars"])
    assert set(res) >= {"sun", "moon"}
    assert 0 <= res["sun"]["lon"] < 360


@pytest.mark.skipif(
    importlib.util.find_spec("skyfield") is None
    or importlib.util.find_spec("jplephem") is None,
    reason="skyfield/jplephem missing",
)
def test_skyfield_available_or_skipped():
    from astroengine.providers.skyfield_provider import SkyfieldProvider

    try:
        SkyfieldProvider()
    except FileNotFoundError:
        pytest.skip("no local JPL kernel found")


@pytest.mark.skipif(
    importlib.util.find_spec("skyfield") is None
    or importlib.util.find_spec("jplephem") is None
    or importlib.util.find_spec("swisseph") is None,
    reason="providers missing",
)
def test_swiss_vs_skyfield_sun_diff_under_one_degree():
    from astroengine.providers.skyfield_provider import SkyfieldProvider
    from astroengine.providers.swiss_provider import SwissProvider

    try:
        sf = SkyfieldProvider()
    except FileNotFoundError:
        pytest.skip("no local JPL kernel found")
    se = SwissProvider()

    t = dt.datetime(2024, 6, 1, 0, 0, 0).isoformat() + "Z"
    a = se.positions_ecliptic(t, ["sun"])["sun"]["lon"]
    b = sf.positions_ecliptic(t, ["sun"])["sun"]["lon"]
    diff = abs((a - b + 180) % 360 - 180)
    assert diff < 1.0  # coarse sanity; detailed QA lives elsewhere


@pytest.mark.skipif(
    importlib.util.find_spec("skyfield") is None
    or importlib.util.find_spec("jplephem") is None
    or importlib.util.find_spec("swisseph") is None,
    reason="providers missing",
)
def test_swiss_vs_skyfield_single_body_position_close():
    import astroengine.providers.skyfield_provider  # ensure registration

    from astroengine.providers import get_provider
    from astroengine.providers.swiss_provider import SwissProvider

    try:
        sf = get_provider("skyfield")
    except KeyError:
        pytest.skip("skyfield provider unavailable")

    se = SwissProvider()
    ts = dt.datetime(2024, 6, 1, 0, 0, 0).isoformat() + "Z"

    swiss_pos = se.position("Sun", ts)
    skyfield_pos = sf.position("Sun", ts)

    lon_diff = abs(((swiss_pos.lon - skyfield_pos.lon) + 180) % 360 - 180)
    assert lon_diff < 1.0
    assert abs(swiss_pos.lat - skyfield_pos.lat) < 1.0
    assert abs(swiss_pos.dec - skyfield_pos.dec) < 1.0
    assert abs(swiss_pos.speed_lon - skyfield_pos.speed_lon) < 0.5


# >>> AUTO-GEN END: AE Provider Tests v1.0
