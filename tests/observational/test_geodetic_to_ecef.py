from __future__ import annotations

import math

from astroengine.engine.observational.earth import ecef_from_geodetic


def _approx(a: float, b: float, tol: float = 1e-6) -> bool:
    return math.isclose(a, b, rel_tol=tol, abs_tol=tol)


def test_equator_origin() -> None:
    vec = ecef_from_geodetic(0.0, 0.0, 0.0)
    assert _approx(vec.x, 6_378_137.0)
    assert _approx(vec.y, 0.0)
    assert _approx(vec.z, 0.0)


def test_pole_height() -> None:
    vec = ecef_from_geodetic(90.0, 0.0, 0.0)
    assert _approx(vec.x, 0.0, tol=1e-5)
    assert _approx(vec.y, 0.0, tol=1e-5)
    assert _approx(vec.z, 6_356_752.314245179)


def test_midlatitude_offset() -> None:
    vec = ecef_from_geodetic(45.0, 45.0, 1000.0)
    assert _approx(vec.x, 3_194_919.1450605746)
    assert _approx(vec.y, 3_194_919.145060574)
    assert _approx(vec.z, 4_488_055.515647106)
