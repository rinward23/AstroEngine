from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

FIXTURE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = FIXTURE_ROOT.parent

pytestmark = pytest.mark.no_repo_package


def _canonicalise(events: list[dict[str, object]]) -> list[str]:
    canonical: list[str] = []
    for event in events:
        payload = {
            "angle_deg": event.get("angle_deg"),
            "family": event.get("family"),
            "kind": event.get("kind"),
            "moving": event.get("moving"),
            "orb_abs": event.get("orb_abs"),
            "target": event.get("target"),
            "ts": event.get("ts"),
        }
        canonical.append(json.dumps(payload, sort_keys=True))
    canonical.sort()
    return canonical


def test_timeline_mars_saturn_fixture_matches_golden() -> None:
    fixture_path = PROJECT_ROOT / "docs-site" / "docs" / "fixtures" / "timeline_events.json"
    golden_path = FIXTURE_ROOT / "golden" / "detectors" / "timeline_mars_saturn.jsonl"
    hash_path = FIXTURE_ROOT / "golden" / "detectors" / "timeline_mars_saturn.sha256"

    fixture_events = json.loads(fixture_path.read_text(encoding="utf-8"))
    canonical_events = _canonicalise(fixture_events)

    actual_payload = "\n".join(canonical_events) + "\n"
    actual_hash = hashlib.sha256(actual_payload.encode("utf-8")).hexdigest()

    expected_lines = golden_path.read_text(encoding="utf-8").splitlines()
    expected_hash = hash_path.read_text(encoding="utf-8").strip()

    assert canonical_events == expected_lines, "Solar Fire detector payload drifted"
    assert actual_hash == expected_hash, "Solar Fire detector checksum mismatch"
