
from datetime import datetime, timezone

from astroengine.narrative import summarize_top_events
from astroengine.narrative.gpt_api import GPTNarrativeClient
from astroengine.timelords.models import TimelordPeriod, TimelordStack



_EVENTS = [
    {
        "timestamp": "2024-03-20T00:00:00Z",
        "moving": "Sun",
        "target": "Moon",
        "kind": "conjunction",
        "score": 5.0,
        "orb_abs": 0.2,
    },
    {
        "timestamp": "2024-03-21T00:00:00Z",
        "moving": "Sun",
        "target": "Mercury",
        "kind": "sextile",
        "score": 3.0,
        "orb_abs": 0.5,
    },
]


def test_summarize_top_events_uses_transport() -> None:
    client = GPTNarrativeClient(transport=lambda prompt, **_: "ok")
    summary = summarize_top_events(_EVENTS, client=client, top_n=1)
    assert summary == "ok"


def test_summarize_top_events_template_fallback() -> None:
    summary = summarize_top_events(_EVENTS, client=GPTNarrativeClient())
    assert summary.startswith("Transit Highlights")
    assert "Sun" in summary

def test_summarize_top_events_with_timelords() -> None:
    stack = TimelordStack(
        moment=datetime(2024, 3, 20, tzinfo=timezone.utc),
        periods=(
            TimelordPeriod(
                system="profections",
                level="annual",
                ruler="Mars",
                start=datetime(2023, 3, 21, tzinfo=timezone.utc),
                end=datetime(2024, 3, 20, tzinfo=timezone.utc),
            ),
        ),
    )
    summary = summarize_top_events(
        _EVENTS,
        profile="sidereal",
        timelords=stack,
        profile_context={"ayanamsha": "lahiri"},
        prefer_template=True,
    )
    assert summary.startswith("Sidereal Emphasis")
    assert "Mars" in summary
    assert "ayanamsha" in summary.lower()
