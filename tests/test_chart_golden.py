"""Golden regression tests for natal and transit calculations."""

from __future__ import annotations

import datetime as dt

import pytest

from astroengine.chart import ChartLocation, TransitScanner, compute_natal_chart
from astroengine.chart.natal import DEFAULT_BODIES
from astroengine.profiles import load_base_profile, load_vca_outline
from astroengine.scoring import OrbCalculator, lookup_dignities

TOLERANCE_DEG = 0.05


def _circular_delta(a: float, b: float) -> float:
    diff = (b - a) % 360.0
    return diff if diff <= 180.0 else 360.0 - diff

GOLDEN_CHARTS = [
    (
        "NYC_1990",
        dt.datetime(1990, 2, 16, 13, 30, tzinfo=dt.timezone(dt.timedelta(hours=-5))),
        ChartLocation(latitude=40.7128, longitude=-74.0060),
        {
            "Sun": 327.824967,
            "Moon": 226.812266,
            "Mercury": 306.587384,
            "Venus": 292.269912,
            "Mars": 283.177018,
            "Jupiter": 90.915699,
            "Saturn": 290.924799,
            "Uranus": 278.287469,
            "Neptune": 283.6611,
            "Pluto": 227.785695,
        },
        {
            "asc": 100.51151492493307,
            "mc": 349.0997581549976,
        },
        [
            ("Moon", "Pluto", 0, 0.97),
            ("Venus", "Saturn", 0, 1.35),
            ("Mars", "Neptune", 0, 0.48),
        ],
    ),
    (
        "London_1985",
        dt.datetime(1985, 7, 13, 17, 45, tzinfo=dt.timezone(dt.timedelta(hours=1))),
        ChartLocation(latitude=51.5074, longitude=-0.1278),
        {
            "Sun": 111.215606,
            "Moon": 61.184662,
            "Mercury": 137.755721,
            "Venus": 67.975138,
            "Mars": 112.558487,
            "Jupiter": 314.704774,
            "Saturn": 231.586352,
            "Uranus": 254.609143,
            "Neptune": 271.716086,
            "Pluto": 211.924831,
        },
        {
            "asc": 245.35985699522826,
            "mc": 182.8648257792668,
        },
        [
            ("Sun", "Mars", 0, 1.34),
            ("Sun", "Saturn", 120, 0.37),
            ("Mars", "Saturn", 120, 0.97),
            ("Jupiter", "Uranus", 60, 0.10),
            ("Neptune", "Pluto", 60, 0.21),
        ],
    ),
    (
        "Tokyo_2000",
        dt.datetime(2000, 12, 25, 8, 15, tzinfo=dt.timezone(dt.timedelta(hours=9))),
        ChartLocation(latitude=35.6895, longitude=139.6917),
        {
            "Sun": 273.465699,
            "Moon": 265.156077,
            "Mercury": 272.986165,
            "Venus": 319.107477,
            "Mars": 210.803963,
            "Jupiter": 62.824828,
            "Saturn": 54.933695,
            "Uranus": 318.320888,
            "Neptune": 305.085719,
            "Pluto": 253.51329,
        },
        {
            "asc": 294.0731106601721,
            "mc": 224.6845321970098,
        },
        [
            ("Sun", "Mercury", 0, 0.48),
            ("Sun", "Mars", 60, 2.66),
            ("Mercury", "Mars", 60, 2.18),
            ("Venus", "Uranus", 0, 0.79),
            ("Jupiter", "Neptune", 120, 2.26),
        ],
    ),
]


@pytest.mark.parametrize(
    "label, moment, location, expected_positions, expected_angles, expected_aspects",
    GOLDEN_CHARTS,
)
def test_natal_chart_positions(
    label: str,
    moment: dt.datetime,
    location: ChartLocation,
    expected_positions: dict[str, float],
    expected_angles: dict[str, float],
    expected_aspects: list[tuple[str, str, int, float]],
) -> None:
    chart = compute_natal_chart(moment, location)

    for body, expected_lon in expected_positions.items():
        assert chart.positions[body].longitude == pytest.approx(
            expected_lon, abs=TOLERANCE_DEG
        )

    assert chart.houses.ascendant == pytest.approx(
        expected_angles["asc"], abs=TOLERANCE_DEG
    )
    assert chart.houses.midheaven == pytest.approx(
        expected_angles["mc"], abs=TOLERANCE_DEG
    )

    seen = {}
    for hit in chart.aspects:
        key = tuple(sorted((hit.body_a, hit.body_b))), hit.angle
        seen[key] = hit

    for body_a, body_b, angle, expected_orb in expected_aspects:
        key = (tuple(sorted((body_a, body_b))), angle)
        assert key in seen, f"missing {body_a}-{body_b} {angle}° for {label}"
        assert seen[key].orb == pytest.approx(expected_orb, abs=0.2)


@pytest.mark.parametrize(
    "label, moment, location", [(item[0], item[1], item[2]) for item in GOLDEN_CHARTS]
)
def test_transit_scanner_detects_self_contacts(
    label: str, moment: dt.datetime, location: ChartLocation
) -> None:
    natal_chart = compute_natal_chart(moment, location)
    scanner = TransitScanner()
    contacts = scanner.scan(natal_chart, moment)
    sun_hits = [
        hit
        for hit in contacts
        if hit.transiting_body == "Sun" and hit.natal_body == "Sun"
    ]
    assert sun_hits, f"expected Sun conjunction for {label}"
    assert sun_hits[0].orb == pytest.approx(0.0, abs=1e-6)


def test_transit_contact_boundaries_match_orb() -> None:
    _, moment, location = GOLDEN_CHARTS[0][:3]
    natal_chart = compute_natal_chart(moment, location)
    scanner = TransitScanner()
    contacts = scanner.scan(natal_chart, moment)
    sun_contact = next(
        contact
        for contact in contacts
        if contact.transiting_body == "Sun"
        and contact.natal_body == "Sun"
        and contact.angle == 0
    )

    assert sun_contact.ingress is not None
    assert sun_contact.egress is not None
    assert sun_contact.ingress < sun_contact.moment < sun_contact.egress
    assert sun_contact.ingress_jd is not None
    assert sun_contact.egress_jd is not None

    adapter = scanner.adapter
    natal_lon = natal_chart.positions["Sun"].longitude
    sun_code = DEFAULT_BODIES["Sun"]

    ingress_sep = _circular_delta(
        adapter.body_position(sun_contact.ingress_jd, sun_code, body_name="Sun").longitude,
        natal_lon,
    )
    egress_sep = _circular_delta(
        adapter.body_position(sun_contact.egress_jd, sun_code, body_name="Sun").longitude,
        natal_lon,
    )

    assert abs(ingress_sep - sun_contact.angle) == pytest.approx(
        sun_contact.orb_allow, abs=5e-3
    )
    assert abs(egress_sep - sun_contact.angle) == pytest.approx(
        sun_contact.orb_allow, abs=5e-3
    )


def test_body_expansions_toggle_optional_points() -> None:
    pytest.importorskip(
        "swisseph",
        reason="swisseph is required for expansion toggles test",
    )
    _, moment, location, *_ = GOLDEN_CHARTS[0]
    expansions = {
        "asteroids": True,
        "chiron": True,
        "mean_lilith": True,
        "true_lilith": True,
        "mean_node": True,
        "true_node": True,
        "vertex": True,
    }
    chart = compute_natal_chart(
        moment,
        location,
        body_expansions=expansions,
    )

    expected = {
        "Ceres",
        "Pallas",
        "Juno",
        "Vesta",
        "Chiron",
        "Black Moon Lilith (Mean)",
        "Black Moon Lilith (True)",
        "Mean Node",
        "True Node",
        "Mean South Node",
        "True South Node",
        "Vertex",
        "Anti-Vertex",
    }
    assert expected.issubset(chart.positions.keys())
    for name in expected:
        pos = chart.positions[name]
        assert 0.0 <= pos.longitude < 360.0

    assert adapter.julian_day(sun_contact.ingress) == pytest.approx(
        sun_contact.ingress_jd, rel=0, abs=5e-7
    )
    assert adapter.julian_day(sun_contact.egress) == pytest.approx(
        sun_contact.egress_jd, rel=0, abs=5e-7
    )


def test_orb_calculator_uses_policy() -> None:
    calculator = OrbCalculator()
    # Sun-Saturn trine should tighten via outer multiplier
    orb = calculator.orb_for("Sun", "Saturn", 120)
    assert orb < calculator.orb_for("Sun", "Sun", 120)


def test_dignity_lookup_returns_rulership() -> None:
    records = lookup_dignities("sun", sign="leo")
    assert any(record.dignity_type == "rulership" for record in records)


def test_profile_loaders_surface_vca_outline() -> None:
    outline = load_vca_outline()
    base_profile = load_base_profile()
    assert outline["modules"]["FIRE"] is True
    assert base_profile["profile_id"] == "base"
