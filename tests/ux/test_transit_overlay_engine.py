"""Unit tests for the transit overlay engine helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from astroengine.chart.natal import ChartLocation
from astroengine.ux.maps.transit_overlay import engine


class TestOverlayOptionsSerialization:
    """Verify :class:`OverlayOptions` mapping helpers."""

    def test_round_trip_through_mapping_and_dict(self) -> None:
        payload = {
            "eph_source": "SWISS",
            "zodiac": "SIDEREAL",
            "ayanamsha": "Lahiri",
            "house_system": "Whole_Sign",
            "nodes_variant": "TRUE",
            "lilith_variant": "TRUE",
            "orbs_deg": {"conj": "3.5"},
            "orb_opposition": 4,
            "orb_overrides": {" Sun ": 2, "TRUE NODE": 1.5},
        }

        options = engine.OverlayOptions.from_mapping(payload)

        assert options.eph_source == "swiss"
        assert options.zodiac == "sidereal"
        assert options.ayanamsha == "Lahiri"
        assert options.house_system == "whole_sign"
        assert options.nodes_variant == "true"
        assert options.lilith_variant == "true"
        assert options.orb_conjunction == pytest.approx(3.5)
        assert options.orb_opposition == pytest.approx(4.0)
        assert options.orb_overrides == {"sun": 2.0, "true_node": 1.5}

        serialized = options.to_dict()
        assert serialized == {
            "eph_source": "swiss",
            "zodiac": "sidereal",
            "house_system": "whole_sign",
            "nodes_variant": "true",
            "lilith_variant": "true",
            "ayanamsha": "Lahiri",
            "orbs_deg": {"conj": 3.5, "opp": 4.0},
            "orb_overrides": {"sun": 2.0, "true_node": 1.5},
        }


class TestOverlayStateSerialization:
    """Tests covering :class:`OverlayBodyState` and :class:`OverlayFrame`."""

    def test_body_state_to_dict_handles_metadata(self) -> None:
        state = engine.OverlayBodyState(
            id="sun",
            lon_deg=120.0,
            lat_deg=-0.1,
            radius_au=1.0,
            speed_lon_deg_per_day=0.95,
            speed_lat_deg_per_day=0.01,
            speed_radius_au_per_day=0.0,
            retrograde=False,
            frame="heliocentric",
            metadata={"source": "ephe"},
        )

        assert state.to_dict() == {
            "id": "sun",
            "lon_deg": 120.0,
            "lat_deg": -0.1,
            "radius_au": 1.0,
            "speed_lon_deg_per_day": 0.95,
            "speed_lat_deg_per_day": 0.01,
            "speed_radius_au_per_day": 0.0,
            "retrograde": False,
            "frame": "heliocentric",
            "metadata": {"source": "ephe"},
        }

        without_metadata = engine.OverlayBodyState(
            id="moon",
            lon_deg=40.0,
            lat_deg=5.0,
            radius_au=0.01,
            speed_lon_deg_per_day=-0.2,
            speed_lat_deg_per_day=0.0,
            speed_radius_au_per_day=0.0,
            retrograde=True,
            frame="geocentric",
        )

        serialized = without_metadata.to_dict()
        assert "metadata" not in serialized
        assert serialized["retrograde"] is True

    def test_frame_to_dict_serializes_nested_states(self) -> None:
        heliocentric = {
            "sun": engine.OverlayBodyState(
                id="sun",
                lon_deg=10.0,
                lat_deg=0.0,
                radius_au=1.0,
                speed_lon_deg_per_day=0.5,
                speed_lat_deg_per_day=0.0,
                speed_radius_au_per_day=0.0,
                retrograde=False,
                frame="heliocentric",
            )
        }
        geocentric = {
            "sun": engine.OverlayBodyState(
                id="sun",
                lon_deg=190.0,
                lat_deg=0.0,
                radius_au=1.0,
                speed_lon_deg_per_day=0.5,
                speed_lat_deg_per_day=0.0,
                speed_radius_au_per_day=0.0,
                retrograde=False,
                frame="geocentric",
            )
        }

        frame = engine.OverlayFrame(
            timestamp=datetime(2024, 5, 1, tzinfo=timezone.utc),
            heliocentric=heliocentric,
            geocentric=geocentric,
            metadata={"system": "whole_sign"},
        )

        serialized = frame.to_dict()
        assert serialized["timestamp"] == datetime(2024, 5, 1, tzinfo=timezone.utc)
        assert serialized["heliocentric"]["sun"]["frame"] == "heliocentric"
        assert serialized["geocentric"]["sun"]["frame"] == "geocentric"
        assert serialized["metadata"] == {"system": "whole_sign"}


@dataclass
class DummyHouses:
    system: str
    ascendant: float
    midheaven: float

    def to_dict(self) -> dict[str, object]:
        return {
            "system": self.system,
            "asc": self.ascendant,
            "mc": self.midheaven,
        }


class DummyAdapter:
    def __init__(self) -> None:
        self.julian_calls: list[datetime] = []
        self.house_calls: list[tuple[float, float, float, str]] = []

    def julian_day(self, moment: datetime) -> float:
        self.julian_calls.append(moment)
        return 2451545.0

    def houses(
        self,
        jd: float,
        latitude: float,
        longitude: float,
        *,
        system: str,
    ) -> DummyHouses:
        self.house_calls.append((jd, latitude, longitude, system))
        return DummyHouses(system=system, ascendant=103.0, midheaven=257.0)


def test_compute_overlay_frames_normalizes_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    engine._cached_planet_position.cache_clear()
    engine._cached_variant_position.cache_clear()
    engine._ADAPTER_CACHE.clear()

    monkeypatch.setattr(engine, "has_swe", lambda: True)

    class _DummySwe:
        FLG_SPEED = 0x02
        FLG_HELCTR = 0x04

    monkeypatch.setattr(engine, "swe", lambda: _DummySwe)
    monkeypatch.setattr(engine, "_PLANET_CODES", {"sun": 0})

    init_calls: list[int] = []

    def fake_init_ephe() -> int:
        init_calls.append(1)
        return 0x10

    monkeypatch.setattr(engine, "init_ephe", fake_init_ephe)

    vec_calls: list[dict[str, object]] = []

    def fake_position_vec(body_code: int, jd_ut: float, *, flags: int) -> tuple[float, ...]:
        vec_calls.append({"body": body_code, "jd": jd_ut, "flags": flags})
        base = 100.0 + body_code
        return (base, 0.0, 1.0, 0.05, 0.0, 0.0)

    monkeypatch.setattr(engine, "position_vec", fake_position_vec)

    variant_calls: list[dict[str, object]] = []

    def fake_position_with_variants(
        name: str,
        jd_ut: float,
        config: engine.ProviderVariantConfig,
        *,
        flags: int,
    ) -> tuple[float, ...]:
        variant_calls.append(
            {
                "name": name,
                "jd": jd_ut,
                "config": config,
                "flags": flags,
            }
        )
        return (275.0, -0.1, 0.9, -0.05, 0.0, 0.0)

    monkeypatch.setattr(engine, "position_with_variants", fake_position_with_variants)

    dummy_adapter = DummyAdapter()
    captured_configs: list[engine.ChartConfig] = []

    def fake_from_chart_config(cls, config: engine.ChartConfig) -> DummyAdapter:  # type: ignore[override]
        captured_configs.append(config)
        return dummy_adapter

    monkeypatch.setattr(
        engine.SwissEphemerisAdapter,
        "from_chart_config",
        classmethod(fake_from_chart_config),
    )

    request = engine.OverlayRequest(
        birth_dt=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        birth_location=ChartLocation(latitude=37.77, longitude=-122.42),
        transit_dt=datetime(2024, 6, 1, 9, 30),
        bodies=["Sun", "TRUE NODE", "ASC", "Sun"],
        options={
            "eph_source": "SWISS",
            "zodiac": "SIDEREAL",
            "ayanamsha": "Lahiri",
            "house_system": "Whole_Sign",
            "nodes_variant": "TRUE",
            "lilith_variant": "TRUE",
            "orb_overrides": {"Sun": 1.5},
        },
    )

    result = engine.compute_overlay_frames(request)

    assert captured_configs and captured_configs[0].zodiac == "sidereal"
    assert captured_configs[0].house_system == "whole_sign"
    assert captured_configs[0].nodes_variant == "true"
    assert captured_configs[0].lilith_variant == "true"

    assert result.options.zodiac == "sidereal"
    assert result.options.house_system == "whole_sign"
    assert result.options.nodes_variant == "true"
    assert result.options.orb_overrides == {"sun": 1.5}

    assert [*result.natal.heliocentric] == ["sun"]
    assert [*result.natal.geocentric] == ["sun", "true_node", "asc"]
    assert result.natal.metadata["houses"]["system"] == "whole_sign"
    assert result.transit.metadata["houses"]["system"] == "whole_sign"
    assert result.transit.geocentric["asc"].metadata == {"kind": "angle"}
    assert result.transit.geocentric["true_node"].retrograde is True

    assert dummy_adapter.julian_calls[0].tzinfo is timezone.utc
    assert dummy_adapter.julian_calls[1].tzinfo is timezone.utc
    assert dummy_adapter.house_calls[0][3] == "whole_sign"

    assert result.transit.timestamp.tzinfo is timezone.utc

    assert init_calls
    assert vec_calls[0]["flags"] == 0x10 | _DummySwe.FLG_SPEED | _DummySwe.FLG_HELCTR
    assert vec_calls[1]["flags"] == 0x10 | _DummySwe.FLG_SPEED

    assert variant_calls[0]["name"] == "true_node"
    assert variant_calls[0]["config"].nodes_variant == "true"
    assert variant_calls[0]["flags"] == 0x10 | _DummySwe.FLG_SPEED

