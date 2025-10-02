from datetime import UTC, datetime
import sys
from types import ModuleType, SimpleNamespace

import pytest

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
        moment=datetime(2024, 3, 20, tzinfo=UTC),
        periods=(
            TimelordPeriod(
                system="profections",
                level="annual",
                ruler="Mars",
                start=datetime(2023, 3, 21, tzinfo=UTC),
                end=datetime(2024, 3, 20, tzinfo=UTC),
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


def test_gpt_client_supports_openai_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_kwargs: dict[str, object] = {}
    captured_call: dict[str, object] = {}

    def create_completion(**kwargs: object) -> SimpleNamespace:
        captured_call.update(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="Paris"),
                )
            ]
        )

    class DummyOpenAI:
        def __init__(self, **kwargs: object) -> None:
            captured_kwargs.update(kwargs)
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=create_completion)
            )

    module = ModuleType("openai")
    module.OpenAI = DummyOpenAI  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "openai", module)

    client = GPTNarrativeClient(
        api_key="token",
        model="openai/gpt-5",
        base_url="https://models.github.ai/inference",
        allow_stub=False,
    )

    assert client.available
    result = client.summarize("What is the capital of France?")
    assert result == "Paris"
    assert captured_kwargs == {
        "api_key": "token",
        "base_url": "https://models.github.ai/inference",
    }
    assert captured_call["model"] == "openai/gpt-5"
