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
    se_pos = se.positions_ecliptic(t, ["sun"])["sun"]
    sf_pos = sf.positions_ecliptic(t, ["sun"])["sun"]

    lon_diff = abs((se_pos["lon"] - sf_pos["lon"] + 180) % 360 - 180)
    decl_diff = abs(se_pos["decl"] - sf_pos["decl"])

    assert lon_diff < 1.0  # coarse sanity; detailed QA lives elsewhere
    assert decl_diff < 1.0


# >>> AUTO-GEN END: AE Provider Tests v1.0
