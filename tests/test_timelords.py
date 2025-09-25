from datetime import UTC, datetime

from astroengine.timelords.dashas import compute_vimshottari_dasha
from astroengine.timelords.zr import compute_zodiacal_releasing


def test_vimshottari_maha_sequence_order() -> None:
    start = datetime(2024, 3, 20, tzinfo=UTC)
    events = compute_vimshottari_dasha(5.0, start, cycles=1, levels=("maha",))
    rulers = [event.ruler for event in events]
    assert rulers == [
        "Ketu",
        "Venus",
        "Sun",
        "Moon",
        "Mars",
        "Rahu",
        "Jupiter",
        "Saturn",
        "Mercury",
    ]
    assert events[0].jd < events[0].end_jd


def test_vimshottari_includes_antar_periods() -> None:
    start = datetime(2024, 3, 20, tzinfo=UTC)
    events = compute_vimshottari_dasha(5.0, start, cycles=1, levels=("maha", "antar"))
    antar = [event for event in events if event.level == "antar"]
    assert antar, "expected antar periods to be generated"
    assert antar[0].parent == "Ketu"
    # Ensure antar periods cover the same span as their parent maha period
    first_maha = next(
        event for event in events if event.level == "maha" and event.ruler == "Ketu"
    )
    assert antar[0].jd == first_maha.jd
    ketu_antar = [event for event in antar if event.parent == "Ketu"]
    assert ketu_antar, "expected antar periods linked to Ketu"
    assert abs(ketu_antar[-1].end_jd - first_maha.end_jd) < 1e-4


def test_zodiacal_releasing_levels() -> None:
    start = datetime(2024, 3, 20, tzinfo=UTC)
    events = compute_zodiacal_releasing(5.0, start, periods=4, levels=("l1", "l2"))
    level_one = [event for event in events if event.level == "l1"]
    level_two = [event for event in events if event.level == "l2"]
    assert [event.sign for event in level_one] == [
        "Aries",
        "Taurus",
        "Gemini",
        "Cancer",
    ]
    assert level_two[0].sign == "Aries"
    assert level_two[0].lot == "fortune"
    assert level_one[0].jd < level_one[0].end_jd
