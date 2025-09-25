from math import sin, tau

from astroengine.ephemeris.refinement import RefineResult, refine_root


def test_refine_root_sine_zero():
    # Root at t=0.25 for sin(2*pi*t)
    f = lambda t: sin(tau * (t - 0.25))
    result: RefineResult = refine_root(f, 0.24, 0.26, tol_seconds=1.0)
    assert result.status in {"ok", "max_iter"}
    assert abs(result.t_exact_jd - 0.25) < 1e-6
    assert result.achieved_tol_sec <= 1.0 + 1e-6
