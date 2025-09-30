from astroengine.engine.vedic import (
    NAKSHATRA_ARC_DEGREES,
    nakshatra_info,
    nakshatra_of,
    pada_of,
    position_for,
)


def test_first_nakshatra_alignment():
    idx = nakshatra_of(0.0)
    info = nakshatra_info(idx)
    assert info.name == "Ashwini"
    assert info.lord == "Ketu"
    assert pada_of(0.0) == 0


def test_degree_within_pada():
    pos = position_for(17.5)  # 17.5° Aries
    assert pos.nakshatra.name == "Bharani"
    assert pos.pada == 2
    assert round(pos.degree_in_pada, 4) == round(17.5 % (NAKSHATRA_ARC_DEGREES / 4.0), 4)


def test_wraparound_longitude():
    idx = nakshatra_of(360.0 + 5.0)
    assert nakshatra_info(idx).name == "Ashwini"
