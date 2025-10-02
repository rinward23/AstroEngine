import json
from datetime import date

import pytest

from astroengine import cli
from astroengine import engine as engine_module
from astroengine.engine import scan_contacts
from astroengine.engine import scanning as scanning_module
from astroengine.engine.scanning import _attach_timelords
from astroengine.exporters import LegacyTransitEvent
from astroengine.timelords import (
    TimelordCalculator,
    active_timelords,
    generate_profection_periods,
    generate_vimshottari_periods,
    generate_zodiacal_releasing,
)
from astroengine.timelords.context import build_context
from astroengine.timelords.utils import parse_iso

NATAL_TS = "1984-10-17T04:30:00Z"
LAT = 40.7128
LON = -74.0060


@pytest.fixture
def natal_context():
    return build_context(parse_iso(NATAL_TS), LAT, LON)


def test_vimshottari_known_dates(natal_context):
    periods = generate_vimshottari_periods(
        natal_context, parse_iso("1990-01-01T00:00:00Z")
    )
    maha = next(period for period in periods if period.level == "maha")
    assert maha.start.date() == date(1984, 10, 17)
    assert maha.end.date() == date(1999, 10, 2)
    antar = [period for period in periods if period.level == "antar"]
    assert antar[0].ruler == "jupiter"
    assert antar[0].end.date() == date(1986, 10, 15)
    assert antar[1].ruler == "saturn"
    assert antar[1].end.date() == date(1989, 2, 26)
    praty = [period for period in periods if period.level == "pratyantar"]
    assert praty[0].end.date() == date(1985, 1, 22)
    assert praty[1].end.date() == date(1985, 5, 17)
    sookshma = [period for period in periods if period.level == "sookshma"]
    assert sookshma, "expected sookshma periods to be generated"
    assert sookshma[0].metadata["parent"] == praty[0].ruler
    praan = [period for period in periods if period.level == "praan"]
    assert praan, "expected praan periods to be generated"
    assert praan[0].metadata["parent"] == sookshma[0].ruler


def test_zodiacal_releasing_spirit_first_periods(natal_context):
    periods = generate_zodiacal_releasing(
        natal_context, parse_iso("1986-01-01T00:00:00Z"), lot="spirit"
    )
    l1 = next(period for period in periods if period.level == "l1")
    assert l1.ruler == "scorpio"
    assert l1.start.date() == date(1984, 10, 17)
    assert l1.end.date() == date(1999, 10, 17)
    l2 = next(period for period in periods if period.level == "l2")
    assert l2.ruler == "scorpio"
    assert l2.end.date() == date(1985, 11, 10)
    l3 = next(period for period in periods if period.level == "l3")
    assert l3.ruler == "scorpio"
    assert l3.end.date() == date(1984, 11, 13)


def test_profections_multilevel_midpoints(natal_context):
    periods = generate_profection_periods(
        natal_context, parse_iso("1985-12-17T04:30:00Z")
    )
    annual = next(period for period in periods if period.level == "annual")
    assert annual.metadata == {"house": 1, "sign": "leo"}
    monthly = [period for period in periods if period.level == "monthly"]
    assert monthly[0].metadata["sign"] == "leo"
    assert monthly[1].metadata["sign"] == "virgo"
    daily = [period for period in periods if period.level == "daily"]
    assert daily[0].midpoint().date() == date(1984, 10, 17)
    assert daily[1].midpoint().date() == date(1984, 10, 18)


def test_active_timelord_stack(natal_context):
    stack = active_timelords(NATAL_TS, LAT, LON, "1985-05-01T12:00:00Z")
    assert stack.rulers() == [
        "sun",
        "saturn",
        "mars",
        "jupiter",
        "jupiter",
        "saturn",
        "rahu",
        "mars",
        "scorpio",
        "scorpio",
        "aries",
        "capricorn",
    ]


def test_cli_timelords_active_output(capsys):
    args = [
        "timelords",
        "active",
        "--natal-utc",
        NATAL_TS,
        "--lat",
        str(LAT),
        "--lon",
        str(LON),
        "--datetime",
        "1985-05-01T12:00:00Z",
    ]
    assert cli.main(args) == 0
    captured = capsys.readouterr()
    assert "Active timelords" in captured.out
    assert "profections/annual" in captured.out
    assert "vimshottari/maha" in captured.out
    assert "zodiacal_releasing/l1" in captured.out


def test_scan_contacts_injects_timelord_metadata(natal_context):
    until = parse_iso("1984-11-17T04:30:00Z")
    calculator = TimelordCalculator(context=natal_context, until=until)
    try:
        engine_module.FEATURE_TIMELORDS = True
        events = scan_contacts(
            start_iso="1984-10-17T00:00:00Z",
            end_iso="1984-10-25T00:00:00Z",
            moving="moon",
            target="sun",
            provider_name="swiss",
            timelord_calculator=calculator,
        )
    finally:
        engine_module.FEATURE_TIMELORDS = False
    assert events
    payload = events[0].metadata
    assert "timelord_rulers" in payload
    assert "timelords" in payload
    # ensure metadata round-trips through JSON serialization
    json.dumps(payload)


def test_timelord_calculator_system_filter(natal_context):
    until = parse_iso("1984-12-31T00:00:00Z")
    calculator = TimelordCalculator(
        context=natal_context,
        until=until,
        systems=("vimshottari",),
    )
    assert calculator.profections == []
    assert calculator.zr_spirit == []
    assert calculator.vimshottari
    systems = {period.system for period in calculator.iter_periods()}
    assert systems == {"vimshottari"}


def test_attach_timelords_marks_dasha_transits(natal_context):
    until = parse_iso("1985-01-15T00:00:00Z")
    calculator = TimelordCalculator(context=natal_context, until=until)
    event = LegacyTransitEvent(
        kind="aspect",
        timestamp="1984-11-01T00:00:00Z",
        moving="Jupiter",
        target="Moon",
        orb_abs=0.0,
        orb_allow=1.0,
        applying_or_separating="applying",
        score=0.0,
    )
    try:
        scanning_module.FEATURE_TIMELORDS = True
        _attach_timelords(event, calculator)
    finally:
        scanning_module.FEATURE_TIMELORDS = False
    assert "transit_over_dasha_lords" in event.metadata
    roles = {entry["role"] for entry in event.metadata["transit_over_dasha_lords"]}
    assert "moving" in roles
