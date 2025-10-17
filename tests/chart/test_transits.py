from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from astroengine.chart.transits import TransitScanner
from astroengine.ephemeris import BodyPosition


BASE_JD = 2451545.0


def _body_position(name: str, longitude: float) -> BodyPosition:
    return BodyPosition(
        body=name,
        julian_day=BASE_JD,
        longitude=longitude % 360.0,
        latitude=0.0,
        distance_au=1.0,
        speed_longitude=0.0,
        speed_latitude=0.0,
        speed_distance=0.0,
        declination=0.0,
        speed_declination=0.0,
    )


@dataclass
class _LinearMotion:
    longitude: float
    speed: float  # degrees per day


class _AdapterStub:
    def __init__(self, base_moment: datetime, motions: dict[str, _LinearMotion]) -> None:
        self.base_moment = base_moment
        self.base_jd = BASE_JD
        self.motions = motions

    def julian_day(self, moment: datetime) -> float:
        delta_days = (moment - self.base_moment).total_seconds() / 86400.0
        return self.base_jd + delta_days

    def body_positions(self, jd_ut: float, body_map):
        positions: dict[str, BodyPosition] = {}
        for name in body_map.keys():
            motion = self.motions.get(name)
            if motion is None:
                continue
            positions[name] = self._position_for(name, jd_ut, motion)
        return positions

    def body_position(self, jd_ut: float, code: int | None, body_name: str | None = None) -> BodyPosition:
        if body_name is None:
            raise ValueError("body_name required for body_position")
        motion = self.motions.get(body_name)
        if motion is None:
            raise KeyError(body_name)
        return self._position_for(body_name, jd_ut, motion)

    def _position_for(self, name: str, jd_ut: float, motion: _LinearMotion) -> BodyPosition:
        delta_days = jd_ut - self.base_jd
        longitude = (motion.longitude + motion.speed * delta_days) % 360.0
        return BodyPosition(
            body=name,
            julian_day=jd_ut,
            longitude=longitude,
            latitude=0.0,
            distance_au=1.0,
            speed_longitude=motion.speed,
            speed_latitude=0.0,
            speed_distance=0.0,
            declination=0.0,
            speed_declination=0.0,
        )


class _OrbStub:
    def __init__(self, threshold: float) -> None:
        self.threshold = threshold

    def orb_for(self, transiting: str, natal: str, angle: int, *, profile: str) -> float:
        return self.threshold


def test_transit_scanner_segments_contact_windows() -> None:
    moment = datetime(2024, 1, 1, 12, tzinfo=UTC)
    natal_positions = {
        "Sun": _body_position("Sun", 100.0),
        "Moon": _body_position("Moon", 250.0),
    }
    natal_chart = SimpleNamespace(positions=natal_positions)

    adapter = _AdapterStub(moment, {"Mars": _LinearMotion(longitude=100.0, speed=1.2)})
    scanner = TransitScanner(
        adapter=adapter,
        orb_calculator=_OrbStub(1.5),
        aspect_angles=(0,),
    )

    contacts = scanner.scan(natal_chart, moment, bodies={"Mars": 4})

    assert len(contacts) == 1
    contact = contacts[0]
    assert contact.transiting_body == "Mars"
    assert contact.natal_body == "Sun"
    assert contact.angle == 0
    assert contact.orb == pytest.approx(0.0, abs=1e-6)
    assert contact.orb_allow == pytest.approx(1.5)
    assert contact.ingress is not None and contact.egress is not None
    assert contact.ingress < moment < contact.egress
    assert contact.ingress_jd is not None and contact.egress_jd is not None
    assert contact.ingress_jd < contact.julian_day < contact.egress_jd

    span_days = (contact.egress - contact.ingress).total_seconds() / 86400.0
    expected_span = 2.0 * (contact.orb_allow / adapter.motions["Mars"].speed)
    assert span_days == pytest.approx(expected_span, rel=1e-2)


def test_transit_scanner_filters_contacts_and_handles_edge_cases() -> None:
    moment = datetime(2024, 1, 1, 12, tzinfo=UTC)
    natal_positions = {
        "Sun": _body_position("Sun", 100.0),
        "Moon": _body_position("Moon", 250.0),
    }
    natal_chart = SimpleNamespace(positions=natal_positions)

    adapter = _AdapterStub(moment, {"Mars": _LinearMotion(longitude=105.0, speed=0.2)})
    scanner = TransitScanner(
        adapter=adapter,
        orb_calculator=_OrbStub(1.0),
        aspect_angles=(0,),
    )

    # Separation exceeds the configured orb → no contacts returned.
    empty_contacts = scanner.scan(natal_chart, moment, bodies={"Mars": 4})
    assert empty_contacts == ()

    # Requesting bodies not provided by the adapter should yield no contacts.
    missing_data = scanner.scan(natal_chart, moment, bodies={"Venus": 3})
    assert missing_data == ()

    # When a body code is unavailable the scanner should still yield contacts,
    # but ingress/egress refinement is skipped.
    matching_adapter = _AdapterStub(moment, {"Mars": _LinearMotion(longitude=100.0, speed=0.5)})
    scanner_with_missing_code = TransitScanner(
        adapter=matching_adapter,
        orb_calculator=_OrbStub(1.0),
        aspect_angles=(0,),
    )
    contacts = scanner_with_missing_code.scan(natal_chart, moment, bodies={"Mars": None})
    assert len(contacts) == 1
    contact = contacts[0]
    assert contact.ingress is None and contact.egress is None
    assert contact.ingress_jd is None and contact.egress_jd is None
    assert contact.orb_allow == pytest.approx(1.0)
