from astroengine.core.aspects_plus.orb_policy import orb_limit

POLICY = {
    "per_object": {"Moon": 10.0},
    "per_aspect": {"conjunction": 8.0, "square": 6.0, "quincunx": 3.0},
    "adaptive_rules": {"luminaries_factor": 0.8, "outers_factor": 1.2, "minor_aspect_factor": 0.9},
}

def test_luminary_tighter_on_conjunction():
    # Base conj 8.0, per-object Moon=10 increases start to 10, then lum factor 0.8 => 8.0
    val = orb_limit("Sun", "Moon", "conjunction", POLICY)
    assert 7.9 <= val <= 8.1


def test_outers_wider_on_square():
    # Base square 6.0, outer present => *1.2 = 7.2
    val = orb_limit("Mars", "Pluto", "square", POLICY)
    assert 7.1 <= val <= 7.3


def test_minor_aspect_factor_applies():
    # Base quincunx 3.0, no lum/outer => *0.9 = 2.7
    val = orb_limit("Mercury", "Venus", "quincunx", POLICY)
    assert 2.6 <= val <= 2.8


def test_per_object_override_wins():
    # Moon override 10 dominates over per-aspect 8, then lum factor 0.8 => 8.0
    val = orb_limit("Moon", "Venus", "conjunction", POLICY)
    assert 7.9 <= val <= 8.1
