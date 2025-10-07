from datetime import UTC, datetime

import pytest

from astroengine.engine.vedic import (
    KarmicProfile,
    build_context,
    compute_chara_karakas,
    eclipse_alignment_roles,
    ishta_kashta_phala,
    karakamsha_lagna,
    karma_attributions,
)
from astroengine.engine.vedic.karmic import build_karmic_profile


def _context():
    return build_context(
        datetime(1984, 10, 17, 4, 30, tzinfo=UTC),
        40.7128,
        -74.0060,
    )


def test_compute_chara_karakas_orders_atmakaraka():
    ctx = _context()
    karakas = compute_chara_karakas(ctx.chart)
    assert karakas[0].role == "atmakaraka"
    assert karakas[0].planet == "Saturn"
    assert karakas[0].degrees_in_sign > karakas[1].degrees_in_sign


def test_karakamsha_lagna_uses_atmakaraka_navamsa():
    ctx = _context()
    karakamsha = karakamsha_lagna(ctx.chart)
    assert karakamsha.sign == "Aries"
    assert karakamsha.pada == 7
    assert karakamsha.atmakaraka.planet == "Saturn"


def test_ishta_kashta_scores_boundaries():
    ctx = _context()
    scores = ishta_kashta_phala(ctx.chart)
    saturn = scores["Saturn"]
    sun = scores["Sun"]
    assert pytest.approx(saturn.ishta, rel=1e-3) == 0.986
    assert saturn.kashta < 0.05
    assert pytest.approx(sun.kashta, rel=1e-3) == 0.946
    assert 0.0 <= sun.ishta <= 1.0


def test_karma_attributions_segment_scores():
    ctx = _context()
    segments = karma_attributions(ctx.chart)
    assert segments["sanchita"].score > 0
    assert segments["prarabdha"].score < 0
    assert "Sun, Moon" in segments["prarabdha"].summary


def test_eclipse_alignment_roles_provide_scores():
    ctx = _context()
    alignments = eclipse_alignment_roles(ctx)
    sun_rahu = alignments["sun_rahu"]
    moon_ketu = alignments["moon_ketu"]
    assert 0.0 <= sun_rahu.alignment <= 1.0
    assert 0.0 <= moon_ketu.alignment <= 1.0
    assert sun_rahu.nodes_variant == "mean"


def test_build_karmic_profile_bundles_all_components():
    ctx = _context()
    profile = build_karmic_profile(ctx)
    assert isinstance(profile, KarmicProfile)
    assert profile.karakamsha.sign == "Aries"
    assert "moon_ketu" in profile.eclipse_alignments
