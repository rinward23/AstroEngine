from __future__ import annotations

from datetime import datetime, timezone

import pytest

from astroengine.engine.vedic.chart import build_context
from astroengine.engine.vedic.panchang import (
    TITHI_ARC_DEGREES,
    karana_from_longitudes,
    nakshatra_from_longitude,
    panchang_from_chart,
    tithi_from_longitudes,
    vaar_from_datetime,
    yoga_from_longitudes,
)


@pytest.mark.swiss
def test_panchang_snapshot_components() -> None:
    moment = datetime(2023, 10, 24, 18, 0, tzinfo=timezone.utc)
    context = build_context(moment, latitude=28.6139, longitude=77.2090)

    snapshot = panchang_from_chart(context)

    assert snapshot.tithi.index == 11
    assert snapshot.tithi.name == "Shukla Ekadashi"
    assert snapshot.tithi.paksha == "Shukla"
    assert snapshot.tithi.progress == pytest.approx(0.3867402931, rel=1e-6)

    assert snapshot.nakshatra.position.nakshatra.name == "Shatabhisha"
    assert snapshot.nakshatra.progress == pytest.approx(0.3638164028, rel=1e-6)

    assert snapshot.yoga.index == 11
    assert snapshot.yoga.name == "Vriddhi"
    assert snapshot.yoga.progress == pytest.approx(0.3795665417, rel=1e-6)

    assert snapshot.karana.index == 21
    assert snapshot.karana.name == "Vanija"
    assert snapshot.karana.progress == pytest.approx(0.7734805863, rel=1e-6)

    assert snapshot.vaar.index == 3
    assert snapshot.vaar.name == "Mangalavara"
    assert snapshot.vaar.english == "Tuesday"


def test_tithi_boundaries() -> None:
    new_moon = tithi_from_longitudes(0.0, 0.0)
    assert new_moon.index == 1
    assert new_moon.progress == pytest.approx(0.0)

    near_full = tithi_from_longitudes(179.0, 0.0)
    assert near_full.index == 15
    assert near_full.progress == pytest.approx((179.0 % TITHI_ARC_DEGREES) / TITHI_ARC_DEGREES)


def test_karana_sequence_wrapping() -> None:
    first = karana_from_longitudes(0.0, 0.0)
    assert first.index == 1
    assert first.name == "Kimstughna"

    last = karana_from_longitudes(359.9, 0.0)
    assert last.name == "Nagava"


def test_yoga_progress_and_wrapping() -> None:
    base = yoga_from_longitudes(0.0, 0.0)
    assert base.index == 1
    assert base.progress == pytest.approx(0.0)

    wrapped = yoga_from_longitudes(400.0, 20.0)
    expected_total = (400.0 + 20.0) % 360.0
    assert wrapped.longitude_sum == pytest.approx(expected_total)
    assert 0.0 <= wrapped.progress < 1.0


def test_nakshatra_progress() -> None:
    status = nakshatra_from_longitude(45.0)
    assert status.position.nakshatra.index == 3
    assert 0.0 <= status.progress <= 1.0


def test_vaar_name_alignment() -> None:
    # Monday (weekday=0)
    monday = vaar_from_datetime(datetime(2024, 1, 1, tzinfo=timezone.utc))
    assert monday.weekday == 0
    assert monday.name == "Somavara"
    assert monday.english == "Monday"

    # Sunday (weekday=6)
    sunday = vaar_from_datetime(datetime(2023, 12, 31, tzinfo=timezone.utc))
    assert sunday.weekday == 6
    assert sunday.name == "Ravivara"
    assert sunday.english == "Sunday"
