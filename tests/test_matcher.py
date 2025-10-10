from astroengine.core.aspects_plus.matcher import angular_sep_deg, match_all, match_pair

POLICY = {
    "per_object": {},
    "per_aspect": {"sextile": 3.0, "square": 6.0, "trine": 6.0, "conjunction": 8.0},
    "adaptive_rules": {},
}


def test_angular_sep_wraps_correctly():
    assert angular_sep_deg(350.0, 10.0) == 20.0
    assert angular_sep_deg(10.0, 190.0) == 180.0
    assert angular_sep_deg(0.0, 0.0) == 0.0


def test_exact_sextile_match():
    m = match_pair("Mars", "Venus", 10.0, 70.0, ["sextile"], POLICY)
    assert m is not None and m["aspect"] == "sextile"
    assert abs(m["orb"]) < 1e-9 and abs(m["angle"] - 60.0) < 1e-9


def test_exact_harmonic_match():
    m = match_pair("Sun", "Moon", 5.0, 45.0, ["novile"], POLICY)
    assert m is not None and m["aspect"] == "novile"
    assert abs(m["orb"]) < 1e-9 and abs(m["angle"] - 40.0) < 1e-9


def test_out_of_orb_excluded():
    # delta = 90, but sextile allowed only 3 → should be None
    m = match_pair("Mars", "Venus", 0.0, 90.0, ["sextile"], POLICY)
    assert m is None


def test_match_all_with_pairs_filter():
    positions = {"Sun": 0.0, "Moon": 60.0, "Mars": 90.0}
    matches = match_all(positions, ["sextile", "square"], POLICY, pairs=[("Sun", "Moon")])
    assert len(matches) == 1 and matches[0]["a"] == "Sun" and matches[0]["b"] == "Moon"
