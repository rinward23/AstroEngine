from __future__ import annotations

from dataclasses import dataclass

import pytest

from astroengine.engine.progressions.solar_arc import (
    AscMc,
    GeoLocation,
    LonLat,
    apply_solar_arc_longitude,
    compute_arc_secondary_sun,
    rotate_angles,
)


@dataclass
class DummySample:
    longitude: float


@dataclass
class DummyEphemeris:
    natal_longitude: float
    progressed_longitude: float

    def sample(self, body: int, moment: object) -> DummySample:  # pragma: no cover - body unused
        if moment == "natal":
            return DummySample(self.natal_longitude)
        return DummySample(self.progressed_longitude)


def test_compute_arc_secondary_sun_uses_progressed_minus_natal() -> None:
    ephem = DummyEphemeris(120.0, 150.0)
    arc = compute_arc_secondary_sun(ephem, "natal", "progressed")
    assert arc == pytest.approx(30.0)


def test_apply_solar_arc_longitude_shifts_points() -> None:
    points = [LonLat(10.0), LonLat(350.0)]
    shifted = apply_solar_arc_longitude(points, 20.0)
    assert shifted[0].longitude == pytest.approx(30.0)
    assert shifted[1].longitude == pytest.approx(10.0)


@pytest.mark.parametrize("mode", ["LongitudeShift", "MCRotation"])
def test_rotate_angles_requires_inputs(mode: str) -> None:
    asc_mc = AscMc(ascendant=100.0, midheaven=200.0)
    if mode == "LongitudeShift":
        rotated = rotate_angles(mode, asc_mc, 15.0)
        assert rotated.ascendant == pytest.approx(115.0)
        assert rotated.midheaven == pytest.approx(215.0)
    else:
        loc = GeoLocation(latitude_deg=51.5, longitude_deg=0.0)
        rotated = rotate_angles(mode, asc_mc, 15.0, loc=loc, obliquity_deg=23.44)
        assert rotated.midheaven == pytest.approx((200.0 + 15.0) % 360.0)


def test_mcroation_requires_location_and_obliquity() -> None:
    asc_mc = AscMc(ascendant=100.0, midheaven=200.0)
    with pytest.raises(ValueError):
        rotate_angles("MCRotation", asc_mc, 10.0)
    loc = GeoLocation(latitude_deg=51.5, longitude_deg=0.0)
    with pytest.raises(ValueError):
        rotate_angles("MCRotation", asc_mc, 10.0, loc=loc)
