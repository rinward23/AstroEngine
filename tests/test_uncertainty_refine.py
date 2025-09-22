from astroengine.refine import (
    adaptive_corridor_width,
    branch_sensitive_angles,
    gaussian_membership,
)


def test_gaussian_membership_peaks_at_exact():
    assert gaussian_membership(0.0, 2.0) == 1.0
    assert gaussian_membership(1.0, 2.0) < 1.0


def test_adaptive_corridor_scales_with_velocity():
    slow = adaptive_corridor_width(4.0, 0.5, 0.4)
    fast = adaptive_corridor_width(4.0, 1.5, 0.1)
    retrograde = adaptive_corridor_width(4.0, -1.0, -0.8, retrograde=True)
    assert fast > slow
    assert retrograde < slow


def test_branch_sensitive_angles_includes_cardinals():
    angles = branch_sensitive_angles(20.0)
    assert any(abs(angle - 90.0) < 1e-6 for angle in angles)
    assert any(abs(angle - 180.0) < 1e-6 for angle in angles)
