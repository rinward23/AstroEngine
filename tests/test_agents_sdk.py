from __future__ import annotations

import json
from pathlib import Path

import pytest

from astroengine.agents import AgentSDK, AgentSDKError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TIMELINE_FIXTURE = PROJECT_ROOT / "docs-site" / "docs" / "fixtures" / "timeline_events.json"


def _load_fixture_events() -> list[dict[str, object]]:
    payload = json.loads(TIMELINE_FIXTURE.read_text(encoding="utf-8"))
    events: list[dict[str, object]] = []
    for event in payload:
        enriched = dict(event)
        enriched.setdefault("source", "docs-site/docs/fixtures/timeline_events.json")
        events.append(enriched)
    return events


_FIXTURE_EVENTS = _load_fixture_events()


def _stub_scan_runner(
    *,
    start_utc: str,
    end_utc: str,
    moving: list[str],
    targets: list[str],
    return_used_entrypoint: bool = False,
    **_: object,
):
    assert start_utc
    assert end_utc
    assert moving
    assert targets
    events = [dict(event) for event in _FIXTURE_EVENTS]
    entrypoint = ("stub.module", "scan_window")
    if return_used_entrypoint:
        return events, entrypoint
    return events


def _bad_scan_runner(**_: object):
    return [{"moving": "Mars", "target": "Saturn"}], ("stub.module", "scan_window")


def test_registry_includes_agents_channel() -> None:
    sdk = AgentSDK()
    node = sdk.describe_path(["developer_platform", "agents", "toolkits", "python"])
    assert node["kind"] == "subchannel"
    assert node["metadata"]["status"] == "available"
    payload = node.get("payload", {})
    assert payload["module"] == "astroengine.agents.AgentSDK"
    assert "docs-site/docs/fixtures/timeline_events.json" in payload["datasets"]


def test_scan_transits_normalises_fixture_events() -> None:
    sdk = AgentSDK(scan_runner=_stub_scan_runner)
    result = sdk.scan_transits(
        start_utc="2024-02-01T00:00:00Z",
        end_utc="2024-02-10T00:00:00Z",
        moving=["Mars"],
        targets=["Saturn"],
    )

    assert result.entrypoint == ("stub.module", "scan_window")
    assert len(result.events) == len(_FIXTURE_EVENTS)

    event = result.events[0]
    assert event.timestamp == _FIXTURE_EVENTS[0]["ts"]
    assert event.moving == _FIXTURE_EVENTS[0]["moving"]
    assert event.target == _FIXTURE_EVENTS[0]["target"]
    assert event.aspect == "conjunction"
    assert event.applying is None
    assert event.metadata["source"] == "docs-site/docs/fixtures/timeline_events.json"
    assert event.metadata["orb_is_absolute"] is True

    context = sdk.build_context(result)
    assert context["entrypoint"] == ("stub.module", "scan_window")
    assert context["summary"]["by_aspect"]["conjunction"] == len(_FIXTURE_EVENTS)
    assert "docs-site/docs/fixtures/timeline_events.json" in context["datasets"]


def test_resolved_files_list_agents_documentation() -> None:
    sdk = AgentSDK()
    paths = sdk.resolved_files(["developer_platform", "agents", "toolkits", "python"])
    assert any(path.endswith("docs/module/developer_platform/agents.md") for path in paths)


def test_scan_transits_rejects_incomplete_event() -> None:
    sdk = AgentSDK(scan_runner=_bad_scan_runner)
    with pytest.raises(AgentSDKError):
        sdk.scan_transits(
            start_utc="2024-02-01T00:00:00Z",
            end_utc="2024-02-10T00:00:00Z",
            moving=["Mars"],
            targets=["Saturn"],
        )

