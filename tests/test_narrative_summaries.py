from astroengine.narrative import summarize_top_events
from astroengine.narrative.gpt_api import GPTNarrativeClient


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
    assert summary.startswith("Top events:")
    assert "Sun" in summary
