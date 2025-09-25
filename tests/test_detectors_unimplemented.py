import pytest


from astroengine.detectors.directed_aspects import solar_arc_natal_aspects
from astroengine.detectors.progressed_aspects import progressed_natal_aspects


def test_solar_arc_directed_aspects_not_implemented():
    with pytest.raises(NotImplementedError):
        solar_arc_natal_aspects(
            natal_ts="2000-01-01T00:00:00Z",
            start_ts="2000-01-01T00:00:00Z",
            end_ts="2000-01-02T00:00:00Z",
            aspects=(0,),
            orb_deg=1.0,
        )


def test_progressed_aspects_not_implemented():
    with pytest.raises(NotImplementedError):
        progressed_natal_aspects(
            natal_ts="2000-01-01T00:00:00Z",
            start_ts="2000-01-01T00:00:00Z",
            end_ts="2000-01-02T00:00:00Z",
            aspects=(0,),
            orb_deg=1.0,
        )
