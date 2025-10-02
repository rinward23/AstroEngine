from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from astroengine.engine.vedic import (
    DashaPeriod,
    TransitSnapshot,
    analyse_gochar_transits,
)
from astroengine.engine.vedic.varga import compute_varga


def _natal_positions() -> dict[str, SimpleNamespace]:
    return {
        "Sun": SimpleNamespace(longitude=120.0),
        "Moon": SimpleNamespace(longitude=315.0),
        "Mars": SimpleNamespace(longitude=80.0),
        "Jupiter": SimpleNamespace(longitude=12.0),
        "Saturn": SimpleNamespace(longitude=150.0),
    }


def _dasha_periods() -> list[DashaPeriod]:
    maha_start = datetime(2023, 1, 1, tzinfo=UTC)
    maha_end = datetime(2032, 1, 1, tzinfo=UTC)
    antar_start = datetime(2024, 1, 1, tzinfo=UTC)
    antar_end = datetime(2025, 1, 1, tzinfo=UTC)
    return [
        DashaPeriod(
            system="vimshottari",
            level="maha",
            ruler="Saturn",
            start=maha_start,
            end=maha_end,
            metadata={"span_years": 9.0},
        ),
        DashaPeriod(
            system="vimshottari",
            level="antar",
            ruler="Mars",
            start=antar_start,
            end=antar_end,
            metadata={"span_years": 1.0, "parent": "Saturn"},
        ),
    ]


def test_gochar_transits_emit_retrograde_triggers_and_alerts() -> None:
    natal = _natal_positions()
    divisional = {
        "D9": compute_varga(natal, "D9"),
        "D10": compute_varga(natal, "D10"),
    }
    periods = _dasha_periods()

    snapshot_1 = TransitSnapshot(
        timestamp=datetime(2024, 3, 1, tzinfo=UTC),
        positions={
            "Saturn": {"longitude": 311.0, "speed": 0.02},
            "Mars": {"longitude": 74.0, "speed": 0.6},
            "Jupiter": {"longitude": 140.0, "speed": 0.09},
        },
    )
    snapshot_2 = TransitSnapshot(
        timestamp=datetime(2024, 3, 5, tzinfo=UTC),
        positions={
            "Saturn": {"longitude": 311.5, "speed": -0.01},
            "Mars": {"longitude": 80.2, "speed": 0.55},
            "Jupiter": {"longitude": 140.3, "speed": 0.09},
        },
    )

    report = analyse_gochar_transits(
        [snapshot_1, snapshot_2],
        natal_positions=natal,
        dasha_periods=periods,
        divisional_positions=divisional,
    )

    assert any(
        trigger.body.lower() == "saturn" and trigger.phase == "retrograde"
        for trigger in report.retrograde_triggers
    )

    mars_contacts = [
        interaction
        for interaction in report.interactions
        if interaction.moving == "Mars"
        and interaction.target == "Mars"
        and interaction.relation == "natal"
    ]
    assert mars_contacts, "expected Mars transit to contact natal Mars"

    mars_contact = mars_contacts[0]
    assert mars_contact.metadata.get("dasha_levels") == ("antar",)
    assert "divisional_charts" in mars_contact.metadata

    assert any(alert.interaction == mars_contact for alert in report.alerts)
    assert any(interaction.relation == "transit" for interaction in report.interactions)
