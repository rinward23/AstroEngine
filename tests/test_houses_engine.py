from core.houses_plus.engine import HousePolicy, compute_houses, list_house_systems

ASC = 100.0
MC = 10.0
LAT = 40.0


def test_list_house_systems():
    systems = list_house_systems()
    assert set(["whole_sign", "equal", "porphyry", "placidus"]).issubset(set(systems))


def test_equal_houses_from_asc():
    r = compute_houses("equal", ASC, MC, LAT)
    cusps = r.cusps
    assert abs(cusps[0] - 100.0) < 1e-9  # 1st cusp at Asc
    assert abs(cusps[1] - 130.0) < 1e-9
    assert abs(cusps[11] - 70.0) < 1e-9  # wrap-around


def test_whole_sign_from_asc_sign():
    r = compute_houses("whole_sign", ASC, MC, LAT)
    cusps = r.cusps
    assert abs(cusps[0] - 90.0) < 1e-9   # 0° of the Asc sign (100° → sign starts at 90°)
    assert abs(cusps[3] - 180.0) < 1e-9


def test_porphyry_quadrant_divisions():
    r = compute_houses("porphyry", ASC, MC, LAT)
    cusps = r.cusps
    expected = [
        100.0,
        130.0,
        160.0,
        190.0,
        220.0,
        250.0,
        280.0,
        310.0,
        340.0,
        10.0,
        40.0,
        70.0,
    ]
    for got, exp in zip(cusps, expected, strict=False):
        assert abs(got - exp) < 1e-9


def test_placidus_fallback_policy():
    pol = HousePolicy(
        extreme_lat_deg=66.0,
        placidus_fallback="porphyry",
        always_fallback_placidus=True,
    )
    r = compute_houses("placidus", ASC, MC, lat_deg=70.0, policy=pol)
    assert r.meta.get("fallback") == "placidus→porphyry"
    # and numerically equals porphyry for the same inputs
    assert abs(r.cusps[0] - 100.0) < 1e-9 and abs(r.cusps[9] - 10.0) < 1e-9
