from __future__ import annotations

import pytest

from astroengine.detectors.directed_aspects import solar_arc_natal_aspects
from astroengine.detectors.progressed_aspects import progressed_natal_aspects


@pytest.mark.parametrize(
    "func",
    [solar_arc_natal_aspects, progressed_natal_aspects],
)
def test_experimental_aspect_detectors_raise(func):
    with pytest.raises(NotImplementedError):
        func(
            "2000-01-01T00:00:00Z",
            "2001-01-01T00:00:00Z",
            "2001-12-31T00:00:00Z",
            aspects=(0,),
            orb_deg=1.0,
        )
