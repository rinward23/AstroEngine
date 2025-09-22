from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from astroengine.exporters import LegacyTransitEvent
from astroengine.exporters_ics import write_ics_calendar
from astroengine.narrative import compose_narrative


def _sample_events() -> list[LegacyTransitEvent]:
    return [
        LegacyTransitEvent(
            kind="aspect_trine",
            timestamp="2025-03-01T08:00:00Z",
            moving="venus",
            target="mars",
            orb_abs=0.85,
            orb_allow=2.0,
            applying_or_separating="applying",
            score=88.4,
            lon_moving=123.45,
            lon_target=134.56,
            metadata={
                "angle_deg": 120.0,
                "timelord": {
                    "name": "Annual Profection",
                    "description": "Year of Venus",
                    "weight": 2.0,
                },
            },
        ),
        LegacyTransitEvent(
            kind="decl_parallel",
            timestamp="2025-03-02T15:30:00Z",
            moving="sun",
            target="moon",
            orb_abs=0.12,
            orb_allow=0.5,
            applying_or_separating="separating",
            score=72.0,
            lon_moving=None,
            lon_target=None,
            metadata={"dec_moving": 10.23, "dec_target": 11.02},
        ),
        LegacyTransitEvent(
            kind="antiscia",
            timestamp="2025-03-03T09:45:00Z",
            moving="mercury",
            target="sun",
            orb_abs=1.5,
            orb_allow=2.0,
            applying_or_separating="applying",
            score=65.5,
            lon_moving=None,
            lon_target=None,
            metadata={},
        ),
        LegacyTransitEvent(
            kind="aspect_square",
            timestamp="2025-03-04T18:20:00Z",
            moving="mars",
            target="saturn",
            orb_abs=0.45,
            orb_allow=3.0,
            applying_or_separating="separating",
            score=55.0,
            lon_moving=None,
            lon_target=None,
            metadata={"angle_deg": 90.0},
        ),
    ]


def _fixtures_path(name: str) -> Path:
    return Path(__file__).parent / "fixtures" / "narrative" / name


def test_template_narrative_snapshot():
    events = _sample_events()
    bundle = compose_narrative(
        events,
        top_n=4,
        generated_at=datetime(2025, 3, 5, 12, 0, tzinfo=timezone.utc),
    )

    expected_markdown = _fixtures_path("template_summary.md").read_text(encoding="utf-8").strip()
    expected_html = _fixtures_path("template_summary.html").read_text(encoding="utf-8").strip()

    assert bundle.markdown.strip() == expected_markdown
    assert bundle.html.strip() == expected_html

    snapshot = bundle.to_dict()
    assert snapshot["mode"] == "template"
    assert snapshot["categories"]
    assert snapshot["domains"]
    assert snapshot["timelords"]


def test_ics_includes_narrative_block(tmp_path):
    events = _sample_events()
    bundle = compose_narrative(
        events,
        top_n=4,
        generated_at=datetime(2025, 3, 5, 12, 0, tzinfo=timezone.utc),
    )
    path = tmp_path / "events.ics"
    count = write_ics_calendar(path, events, title="Sample Calendar", narrative_text=bundle)
    assert count == len(events)

    actual = path.read_text(encoding="utf-8")
    expected = _fixtures_path("events_with_narrative.ics").read_text(encoding="utf-8")
    assert actual.replace("\r\n", "\n").strip() == expected.replace("\r\n", "\n").strip()
    assert "Narrative Summary" in actual
