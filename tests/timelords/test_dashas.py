import math
from datetime import datetime

import pytest

from astroengine.timelords import dashas


@pytest.fixture
def fake_ephemeris(monkeypatch: pytest.MonkeyPatch) -> tuple[str, str, str]:
    """Patch ephemeris hooks so tests can control daśā windows precisely."""

    natal_ts = "natal"
    start_ts = "start"
    end_ts = "end"

    natal_jd = 1000.0
    ketu_span = dashas._DASHA_YEARS["Ketu"] * dashas.SIDEREAL_YEAR_DAYS
    start_jd = natal_jd + ketu_span + 5.0
    end_jd = start_jd + 10.0

    mapping = {natal_ts: natal_jd, start_ts: start_jd, end_ts: end_jd}

    monkeypatch.setattr(dashas, "iso_to_jd", mapping.__getitem__)
    monkeypatch.setattr(dashas, "jd_to_iso", lambda jd: f"iso-{jd:.3f}")
    monkeypatch.setattr(dashas, "moon_lon", lambda _jd: 0.0)

    return natal_ts, start_ts, end_ts


def test_major_index_and_fraction_uses_moon_longitude(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[float] = []

    def fake_moon_lon(jd: float) -> float:
        calls.append(jd)
        return dashas.NAKSHATRA_SIZE * 2.5

    monkeypatch.setattr(dashas, "moon_lon", fake_moon_lon)

    index, fraction = dashas._major_index_and_fraction(2451544.5)

    assert calls == [2451544.5]
    assert index == 2  # 0:Ketu, 1:Venus, 2:Sun
    assert pytest.approx(0.5, rel=1e-12) == fraction


def test_sub_periods_respects_start_fraction_and_bounds() -> None:
    assert dashas._sub_periods(0, 10.0, 10.0, 0.0) == []

    major_start = 0.0
    major_end = 12.0
    start_fraction = 0.25
    results = dashas._sub_periods(0, major_start, major_end, start_fraction)
    assert results, "expected sub periods once the major window has length"

    major_length = major_end - major_start
    cumulative = 0.0
    expected_index = None
    expected_lord = None
    expected_start = None
    expected_end = None
    for offset in range(len(dashas._DASHA_SEQUENCE)):
        sub_index = (0 + offset) % len(dashas._DASHA_SEQUENCE)
        sub_lord = dashas._DASHA_SEQUENCE[sub_index]
        fraction = dashas._DASHA_YEARS[sub_lord] / dashas._TOTAL_SEQUENCE_YEARS
        sub_start_fraction = cumulative
        sub_end_fraction = cumulative + fraction
        cumulative = sub_end_fraction
        if sub_end_fraction <= start_fraction:
            continue
        expected_index = sub_index
        expected_lord = sub_lord
        expected_start = major_start + max(sub_start_fraction, start_fraction) * major_length
        expected_end = major_start + min(sub_end_fraction, 1.0) * major_length
        break

    assert expected_index is not None
    first_index, first_lord, first_start, first_end = results[0]
    assert first_index == expected_index
    assert first_lord == expected_lord
    assert math.isclose(first_start, expected_start, rel_tol=1e-12)
    assert math.isclose(first_end, expected_end, rel_tol=1e-12)
    assert math.isclose(results[-1][3], major_end, rel_tol=1e-12)


def test_vimsottari_dashas_include_partial_controls_major_iteration(
    fake_ephemeris: tuple[str, str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    natal_ts, start_ts, end_ts = fake_ephemeris

    original_sub_periods = dashas._sub_periods
    seen: list[int] = []

    def tracker(
        major_index: int,
        major_start: float,
        major_end: float,
        start_fraction: float,
    ) -> list[tuple[int, str, float, float]]:
        seen.append(major_index)
        return list(original_sub_periods(major_index, major_start, major_end, start_fraction))

    monkeypatch.setattr(dashas, "_sub_periods", tracker)

    periods_without_partials = dashas.vimsottari_dashas(
        natal_ts, start_ts, end_ts, include_partial=False
    )
    assert all(period.major_lord != "Ketu" for period in periods_without_partials)
    assert 0 not in seen

    dashas.vimsottari_dashas(natal_ts, start_ts, end_ts, include_partial=True)
    assert 0 in seen, "enabling partials should evaluate the skipped major period"


def test_vimsottari_dashas_returns_empty_for_non_positive_window(monkeypatch: pytest.MonkeyPatch) -> None:
    natal_ts, start_ts, end_ts = "natal", "start", "end"
    mapping = {natal_ts: 1000.0, start_ts: 1100.0, end_ts: 1100.0}

    monkeypatch.setattr(dashas, "iso_to_jd", mapping.__getitem__)
    monkeypatch.setattr(dashas, "jd_to_iso", lambda jd: f"iso-{jd}")
    monkeypatch.setattr(dashas, "moon_lon", lambda _jd: 0.0)

    assert dashas.vimsottari_dashas(natal_ts, start_ts, end_ts) == []
