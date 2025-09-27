from core.lots_plus.engine import eval_formula, norm360
from core.lots_plus.catalog import compute_lot, compute_lots, LotDef, register_lot, Sect


def test_eval_formula_basic_and_wrap():
    pos = {"Asc": 350.0, "Sun": 10.0, "Moon": 20.0}
    # 350 + 20 - 10 = 360 → 0
    val = eval_formula("Asc + Moon - Sun", pos)
    assert abs(val - 0.0) < 1e-9


def test_fortune_and_spirit_day_night():
    pos = {"Asc": 100.0, "Sun": 10.0, "Moon": 70.0}
    # Day: Fortune = 100 + 70 - 10 = 160
    f_day = compute_lot("Fortune", pos, Sect.DAY)
    assert abs(f_day - 160.0) < 1e-9
    # Night: Fortune = 100 + 10 - 70 = 40
    f_night = compute_lot("Fortune", pos, Sect.NIGHT)
    assert abs(f_night - 40.0) < 1e-9

    # Spirit swaps Sun/Moon relative to Fortune
    s_day = compute_lot("Spirit", pos, Sect.DAY)   # 100 + 10 - 70 = 40
    s_night = compute_lot("Spirit", pos, Sect.NIGHT)  # 100 + 70 - 10 = 160
    assert abs(s_day - 40.0) < 1e-9 and abs(s_night - 160.0) < 1e-9


def test_dependent_lot_resolution():
    # Eros references Spirit; ensure dependency resolves once
    pos = {"Asc": 100.0, "Sun": 10.0, "Moon": 70.0, "Venus": 20.0}
    # Spirit(day) = 100 + 10 - 70 = 40 ; Eros(day) = 100 + 20 - Spirit = 80
    val = compute_lot("Eros", pos, Sect.DAY)
    assert abs(val - 80.0) < 1e-9


def test_compute_lots_batch():
    pos = {"Asc": 210.0, "Sun": 120.0, "Moon": 300.0}
    results = compute_lots(["Fortune", "Spirit"], pos, Sect.DAY)
    assert set(results.keys()) == {"Fortune", "Spirit"}
    assert abs(results["Fortune"] - 30.0) < 1e-9
    assert abs(results["Spirit"] - 30.0) < 1e-9


def test_custom_lot_registration():
    # Lot of Test := Asc + 15 - Sun
    from core.lots_plus.catalog import REGISTRY

    name = "LotOfTest"
    if name in REGISTRY:
        REGISTRY.pop(name)
    register_lot(LotDef(name=name, day="Asc + 15 - Sun", night="Asc + 15 - Sun", description="Test lot"))

    pos = {"Asc": 200.0, "Sun": 10.0}
    val = compute_lot(name, pos, Sect.DAY)
    assert abs(val - 205.0) < 1e-9


def test_invalid_sect_raises():
    pos = {"Asc": 100.0, "Sun": 10.0, "Moon": 70.0}
    try:
        compute_lot("Fortune", pos, "dawn")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for invalid sect")
