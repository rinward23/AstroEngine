import os
from datetime import UTC, datetime

import pytest

try:

    HAVE_SWISS = True
except Exception:  # pragma: no cover
    HAVE_SWISS = False

SE_OK = bool(os.environ.get("SE_EPHE_PATH") or os.environ.get("SWE_EPH_PATH"))
pytestmark = pytest.mark.skipif(
    not (HAVE_SWISS and SE_OK), reason="Swiss ephemeris not available"
)

from astroengine.chart import ChartLocation, compute_natal_chart
from astroengine.chart.composite import compute_composite_chart
from astroengine.detectors.common import iso_to_jd
from astroengine.detectors.returns import solar_lunar_returns
from astroengine.engine import TargetFrameResolver, scan_contacts


def _primary_chart() -> tuple[datetime, ChartLocation, object]:
    moment = datetime(1990, 1, 1, 12, tzinfo=UTC)
    location = ChartLocation(latitude=40.7128, longitude=-74.0060)
    chart = compute_natal_chart(moment, location)
    return moment, location, chart


def _partner_chart() -> object:
    partner_moment = datetime(1985, 7, 13, 16, 45, tzinfo=UTC)
    partner_location = ChartLocation(latitude=34.0522, longitude=-118.2437)
    return compute_natal_chart(partner_moment, partner_location)


def test_solar_and_lunar_returns_match_reference() -> None:
    moment, _, natal_chart = _primary_chart()
    natal_jd = iso_to_jd(moment.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z"))
    start = iso_to_jd("2020-01-01T00:00:00Z")
    end = iso_to_jd("2021-01-01T00:00:00Z")

    solar_events = solar_lunar_returns(natal_jd, start, end, "solar")
    assert solar_events
    assert solar_events[0].ts == "2020-01-01T18:56:43Z"

    lunar_end = iso_to_jd("2020-02-01T00:00:00Z")
    lunar_events = solar_lunar_returns(natal_jd, start, lunar_end, "lunar")
    assert lunar_events
    assert lunar_events[0].ts == "2020-01-13T19:29:43Z"


def test_progressed_resolver_matches_expected_longitude() -> None:
    _, _, natal_chart = _primary_chart()
    resolver = TargetFrameResolver("progressed", natal_chart=natal_chart)

    pos = resolver.position_dict("2020-01-01T12:00:00Z", "Sun")
    assert pos["lon"] == pytest.approx(311.353371730214, rel=1e-6)

    moon_pos = resolver.position_dict("2020-01-01T12:00:00Z", "Moon")
    assert moon_pos["lon"] == pytest.approx(11.414140977903433, rel=1e-6)


def test_directed_resolver_matches_expected_longitude() -> None:
    _, _, natal_chart = _primary_chart()
    resolver = TargetFrameResolver("directed", natal_chart=natal_chart)

    mars_pos = resolver.position_dict("2020-01-01T12:00:00Z", "Mars")
    assert mars_pos["lon"] == pytest.approx(280.53920288277413, rel=1e-6)


def test_composite_resolver_matches_expected_longitude() -> None:
    _, _, natal_chart = _primary_chart()
    partner_chart = _partner_chart()
    composite = compute_composite_chart(natal_chart, partner_chart)
    resolver = TargetFrameResolver(
        "composite", natal_chart=natal_chart, composite_chart=composite
    )

    sun_pos = resolver.position_dict("2020-07-20T00:00:00Z", "Sun")
    assert sun_pos["lon"] == pytest.approx(196.01493088166742, rel=1e-6)


def test_scan_contacts_for_static_natal_longitude() -> None:
    resolver = TargetFrameResolver("natal", static_positions={"sun": 280.009517900689})
    events = scan_contacts(
        start_iso="2020-01-01T00:00:00Z",
        end_iso="2020-01-02T00:00:00Z",
        moving="sun",
        target="sun",
        provider_name="swiss",
        step_minutes=60,
        target_frame="natal",
        target_resolver=resolver,
    )
    assert events
    best = min(events, key=lambda ev: ev.orb_abs)
    assert best.lon_target == pytest.approx(280.009517900689, abs=0.1)


def test_scan_contacts_progressed_frame_hits_expected_longitude() -> None:
    _, _, natal_chart = _primary_chart()
    resolver = TargetFrameResolver("progressed", natal_chart=natal_chart)
    events = scan_contacts(
        start_iso="2020-11-04T00:00:00Z",
        end_iso="2020-11-08T00:00:00Z",
        moving="sun",
        target="sun",
        provider_name="swiss",
        step_minutes=120,
        target_frame="progressed",
        target_resolver=resolver,
    )
    assert events
    best = min(events, key=lambda ev: ev.orb_abs)
    assert best.lon_target == pytest.approx(312.20808265875746, abs=0.1)


def test_scan_contacts_directed_frame_emits_events() -> None:
    _, _, natal_chart = _primary_chart()
    resolver = TargetFrameResolver("directed", natal_chart=natal_chart)
    events = scan_contacts(
        start_iso="2020-11-04T00:00:00Z",
        end_iso="2020-11-08T00:00:00Z",
        moving="sun",
        target="sun",
        provider_name="swiss",
        step_minutes=120,
        target_frame="directed",
        target_resolver=resolver,
    )
    assert events
    best = min(events, key=lambda ev: ev.orb_abs)
    assert best.lon_target == pytest.approx(312.20808265875746, abs=0.1)


def test_scan_contacts_composite_frame_detects_hits() -> None:
    _, _, natal_chart = _primary_chart()
    partner_chart = _partner_chart()
    composite = compute_composite_chart(natal_chart, partner_chart)
    resolver = TargetFrameResolver(
        "composite", natal_chart=natal_chart, composite_chart=composite
    )
    events = scan_contacts(
        start_iso="2020-07-16T00:00:00Z",
        end_iso="2020-07-20T00:00:00Z",
        moving="sun",
        target="sun",
        provider_name="swiss",
        step_minutes=120,
        target_frame="composite",
        target_resolver=resolver,
    )
    assert events
    best = min(events, key=lambda ev: ev.orb_abs)
    assert best.lon_target == pytest.approx(196.01493088166742, abs=0.2)
