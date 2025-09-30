from __future__ import annotations

from astroengine.engine.observational.topocentric import refraction_saemundsson


def test_refraction_standard_conditions() -> None:
    assert refraction_saemundsson(0.0, 10.0, 1010.0) == pytest.approx(28.98192738444997, rel=1e-6)
    assert refraction_saemundsson(5.0, 10.0, 1010.0) == pytest.approx(9.674126604114392, rel=1e-6)
    assert refraction_saemundsson(10.0, 10.0, 1010.0) == pytest.approx(5.4076808031353245, rel=1e-6)


import pytest
