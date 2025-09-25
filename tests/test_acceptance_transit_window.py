from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

pytestmark = pytest.mark.swiss

from astroengine.core.transit_engine import TransitEngine
from astroengine.detectors.common import iso_to_jd
from astroengine.detectors.eclipses import find_eclipses
from astroengine.detectors.ingresses import find_sign_ingresses
from astroengine.detectors.returns import solar_lunar_returns
from astroengine.timelords.dashas import vimsottari_dashas


def _iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(UTC)


def test_mars_venus_exact_within_window() -> None:
    engine = TransitEngine.with_default_adapter()
    natal_venus_longitude = 240.9623186447056
    window_start = datetime(2025, 10, 20, tzinfo=UTC)
    window_end = datetime(2025, 11, 19, tzinfo=UTC)

    events = list(
        engine.scan_longitude_crossing(
            4, natal_venus_longitude, 0.0, window_start, window_end
        )
    )
    assert events, "Expected Mars to contact the natal Venus longitude"

    conjunction = min(events, key=lambda evt: abs(evt.orb or 999.0))
    expected_timestamp = datetime(2025, 11, 5, 21, 14, 3, 750000, tzinfo=UTC)
    assert conjunction.orb is not None and conjunction.orb < 1.0 / 60.0
    assert abs(conjunction.timestamp - expected_timestamp) <= timedelta(minutes=20)


def test_eclipse_detected_in_window() -> None:
    start_jd = iso_to_jd("2025-03-15T00:00:00Z")
    end_jd = iso_to_jd("2025-04-14T00:00:00Z")

    eclipses = find_eclipses(start_jd, end_jd)
    solar = [event for event in eclipses if event.eclipse_type == "solar"]
    assert solar, "Solar eclipse expected in window"

    event = min(solar, key=lambda evt: abs(evt.jd - iso_to_jd("2025-03-29T10:57:51Z")))
    assert event.phase == "new_moon"
    assert abs(_iso(event.ts) - _iso("2025-03-29T10:57:51Z")) <= timedelta(minutes=15)


def test_sun_aries_ingress_recorded() -> None:
    start_jd = iso_to_jd("2025-03-15T00:00:00Z")
    end_jd = iso_to_jd("2025-04-14T00:00:00Z")
    ingresses = find_sign_ingresses(start_jd, end_jd, bodies=["sun"])
    assert ingresses, "Sun ingress expected in window"

    ingress = ingresses[0]
    assert ingress.sign_from == "Pisces"
    assert ingress.sign_to == "Aries"
    assert abs(_iso(ingress.ts) - _iso("2025-03-20T09:01:29Z")) <= timedelta(minutes=20)


def test_solar_return_within_window() -> None:
    natal_jd = iso_to_jd("1990-07-11T08:00:00Z")
    start_jd = iso_to_jd("2025-06-21T00:00:00Z")
    end_jd = iso_to_jd("2025-07-21T00:00:00Z")

    returns = solar_lunar_returns(natal_jd, start_jd, end_jd, kind="solar")
    assert returns, "Solar return should occur within the 30-day window"

    event = returns[0]
    expected = _iso("2025-07-10T19:04:10Z")
    assert abs(_iso(event.ts) - expected) <= timedelta(minutes=30)


def test_vimsottari_dasha_snapshot_alignment() -> None:
    periods = vimsottari_dashas(
        "1990-07-11T08:00:00Z",
        "2025-03-15T00:00:00Z",
        "2025-04-14T00:00:00Z",
    )
    assert periods, "Expected an active dasha period covering the window"

    active = periods[0]
    assert active.major_lord == "Mercury"
    assert active.sub_lord == "Moon"

    window_start_jd = iso_to_jd("2025-03-15T00:00:00Z")
    window_end_jd = iso_to_jd("2025-04-14T00:00:00Z")
    assert active.jd <= window_start_jd <= active.end_jd
    assert window_end_jd <= active.end_jd
