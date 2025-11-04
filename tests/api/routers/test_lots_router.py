"""Validation smoke tests for the lots router models."""

from __future__ import annotations

from datetime import datetime, timezone

from astroengine.api.routers.lots import (
    AspectScanRequest,
    ChartInput,
    EventScanRequest,
    LotCompileRequest,
    LotComputeRequest,
    LotPresetPayload,
)


def test_lots_router_models_validate() -> None:
    """Ensure the router's Pydantic models accept representative payloads."""

    chart_input = ChartInput(
        positions={"Sun": 120.0, "Moon": 250.5},
        angles={"Asc": 15.0},
        is_day=True,
        sun_altitude=5.5,
        moment=datetime(2024, 1, 1, 12, 30, tzinfo=timezone.utc),
        latitude=40.7128,
        longitude=-74.006,
        zodiac="tropical",
        ayanamsha=None,
        house_system="Placidus",
    )

    compute_request = LotComputeRequest(
        source="lot Fortune = Asc + Moon - Sun",
        chart=chart_input,
    )

    compile_request = LotCompileRequest(source="lot Spirit = Sun + Mercury - Asc")

    aspect_request = AspectScanRequest(
        lots={"Fortune": 123.4},
        bodies={"Sun": 95.0, "Moon": 205.2},
        harmonics=[1, 3],
        policy={"orb": 2.0},
    )

    event_request = EventScanRequest(
        lot_name="Fortune",
        lot_longitude=123.4,
        bodies=["Sun", "Moon"],
        start=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        end=datetime(2024, 1, 2, 0, 0, tzinfo=timezone.utc),
        harmonics=[1, 2],
        policy={"orb": 1.5},
        step_hours=6.0,
    )

    preset_payload = LotPresetPayload(
        profile_id="fortune",
        name="Fortune",
        description="Fortune lot profile",
        source="lot Fortune = Asc + Moon - Sun",
        zodiac="tropical",
        house_system="Placidus",
        policy_id="standard",
        ayanamsha=None,
        tradition="hellenistic",
        source_refs={"Valens": "Anthologies"},
    )

    # The test focuses on construction; ensure key fields round-trip through model_dump.
    compute_dump = compute_request.model_dump()
    assert compute_dump["chart"]["positions"] == chart_input.positions
    assert compile_request.source.startswith("lot Spirit")
    assert aspect_request.lots["Fortune"] == 123.4
    assert event_request.start.tzinfo is timezone.utc
    assert preset_payload.profile_id == "fortune"
