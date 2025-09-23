import pytest

from astroengine.chart.natal import ChartLocation
from astroengine.cycles import (
    compute_age_series,
    derive_age_boundaries,
    neptune_pluto_wave,
    outer_cycle_timeline,
)
from astroengine.fixedstars import parans


def test_outer_cycle_timeline_generates_samples():
    timeline = outer_cycle_timeline(1990, 1990, step_days=120.0)
    assert timeline.samples
    assert {sample.phase for sample in timeline.samples} <= {"waxing", "waning"}
    assert all(0.0 <= sample.separation <= 180.0 for sample in timeline.samples)


def test_neptune_pluto_wave_rates_have_values():
    wave = neptune_pluto_wave(1990, 1992, step_days=180.0)
    assert wave.samples
    rates = [point.rate_deg_per_year for point in wave.samples]
    assert rates[0] is None
    assert any(rate is not None for rate in rates[1:])


def test_age_series_boundaries():
    series = compute_age_series(2000, 2002)
    assert len(series.samples) == 3
    assert all(sample.zodiac_sign in {"Pisces", "Aquarius"} for sample in series.samples)
    boundaries = derive_age_boundaries(series)
    assert boundaries
    assert boundaries[0].zodiac_sign == series.samples[0].zodiac_sign


def test_fixed_star_parans_import_guard():
    if parans.HAS_SKYFIELD:
        pytest.skip("skyfield available; guard not triggered")
    location = ChartLocation(latitude=0.0, longitude=0.0)
    with pytest.raises(ImportError):
        parans.compute_star_parans("Regulus", "2020-03-20", location)


def test_heliacal_phases_import_guard():
    if parans.HAS_SKYFIELD:
        pytest.skip("skyfield available; guard not triggered")
    location = ChartLocation(latitude=0.0, longitude=0.0)
    with pytest.raises(ImportError):
        parans.compute_heliacal_phases("Regulus", "2020-03-20", location)

